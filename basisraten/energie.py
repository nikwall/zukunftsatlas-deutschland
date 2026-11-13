"""Energy price shocks: real price two years after the peak vs. pre-shock year. Usage: python -I energie.py <fred_dir>"""
import csv
import sys
from pathlib import Path

d = Path(sys.argv[1])

def load(name):
    out = {}
    with open(d / f"{name}.csv", newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            try:
                out[row[0][:7]] = float(row[1])
            except ValueError:
                pass
    return out

wti, cpi, gas = load("WTISPLC"), load("CPIAUCSL"), load("PNGASEUUSDM")
last = cpi[max(cpi)]
real = lambda s: {m: v / cpi[m] * last for m, v in s.items() if m in cpi}
rw, rg = real(wti), real(gas)

def months(a, b):
    y, m = map(int, a.split("-")); out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}"); m += 1
        if m == 13: y, m = y + 1, 1
    return out

def shift(mon, k):
    y, m = map(int, mon.split("-")); t = y * 12 + (m - 1) + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"

def episode(s, name, pre_year, win):
    pk = max(months(*win), key=lambda x: s.get(x, -1))
    pre = sum(s[m] for m in months(f"{pre_year}-01", f"{pre_year}-12")) / 12
    post_m = [shift(pk, k) for k in range(13, 25)]
    post = sum(s[m] for m in post_m) / 12
    print(f"{name}: Gipfel {pk} ({s[pk]/pre:.1f}x Vorjahr {pre_year}); 2 Jahre später {post/pre:.2f}x")
    return post / pre

res = [
    episode(rw, "Öl 1973/74", 1972, ("1973-10", "1974-12")),
    episode(rw, "Öl 1979/80", 1978, ("1979-01", "1981-12")),
    episode(rw, "Öl 1990", 1989, ("1990-08", "1991-02")),
    episode(rw, "Öl 2008", 2007, ("2008-01", "2008-12")),
    episode(rw, "Öl 2022", 2021, ("2022-01", "2022-12")),
    episode(rg, "Gas EU 2022 (Vorjahr 2019)", 2019, ("2021-06", "2022-12")),
]
print("Normalisiert (<1,25x):", sum(r < 1.25 for r in res), "von", len(res))
print("Gas EU real, Jahresmittel USD/MMBtu:", {y: round(sum(gas[m] for m in months(f'{y}-01', f'{y}-12') if m in gas) / 12, 1) for y in range(2019, 2026)})
print("Gas EU zuletzt:", {m: gas[m] for m in months("2026-01", "2026-09") if m in gas})
