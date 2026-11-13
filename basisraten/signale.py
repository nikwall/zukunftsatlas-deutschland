"""Base rates for the signal timeline. Usage: python -I signale.py <datadir>

Reads the Eurostat/FRED snapshots in <datadir>; fetches three more Eurostat series if missing
(population on 1 January, monthly 10-year yields, industrial production).
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
d = Path(sys.argv[1])
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EXTRA = {
    "pop_jan": ("demo_gind", {"indic_de": "JAN", "geo": "DE"}),
    "bond_m_long": ("irt_lt_mcby_m", {"geo": "DE"}),
    "indprod_m": ("sts_inpr_m", {"geo": "DE", "nace_r2": "B-D", "s_adj": "SCA", "unit": "I21", "indic_bt": "PRD"}),
}


def fetch(ds, params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    with urllib.request.urlopen(f"{BASE}{ds}?format=JSON&lang=EN&{q}", timeout=120) as r:
        js = json.load(r)
    t = {v: k for k, v in js["dimension"]["time"]["category"]["index"].items()}
    size_t = js["size"][js["id"].index("time")]
    return {t[int(i) % size_t]: v for i, v in js["value"].items()}


for name, (ds, p) in EXTRA.items():
    f = d / f"{name}.json"
    if not f.exists():
        f.write_text(json.dumps(fetch(ds, p)))
E = lambda n: json.loads((d / f"{n}.json").read_text())

# Produktivität je Stunde
p = {int(y): v for y, v in E("prod_hour")["DE"].items()}
g = {y: (p[y] / p[y - 1] - 1) * 100 for y in p if y - 1 in p}
print("Produktivität: Jahre >= 1,5 %:", sum(v >= 1.5 for v in g.values()), "von", len(g),
      "| seit 2010:", sum(v >= 1.5 for y, v in g.items() if y >= 2010), "von", sum(1 for y in g if y >= 2010))
w4 = {y: ((p[y + 4] / p[y]) ** 0.25 - 1) * 100 for y in p if y + 4 in p}
print("Produktivität: 4-Jahres-Fenster >= 1,0 %:", sum(v >= 1.0 for v in w4.values()), "von", len(w4),
      "| Start ab 2006:", sum(v >= 1.0 for y, v in w4.items() if y >= 2006), "von", sum(1 for y in w4 if y >= 2006))

# Bevölkerung
pop = {int(y): v for y, v in E("pop_jan").items()}
dec = [y for y in pop if y + 1 in pop and pop[y + 1] < pop[y] and y >= 1991]
print("Bevölkerung geschrumpft (Jahr y: 1.1.y+1 < 1.1.y) seit 1991:", sorted(dec), "->", len(dec), "von", sum(1 for y in pop if y >= 1991 and y + 1 in pop))

# Nettozuwanderung
m = {int(y): v for y, v in E("netmig")["DE"].items()}
for thr in (100_000, 150_000):
    yrs = [y for y in m if y >= 1991]
    print(f"Nettozuwanderung >= {thr:,} seit 1991: {sum(m[y] >= thr for y in yrs)} von {len(yrs)}")

# Ölpreis: Monatsmittel zwei Monate später über 92,6 % des Ausgangswerts (100 $ bei 108 $ Terminkurs)
oil = {}
with open(d / "WTISPLC.csv") as f:
    r = csv.reader(f); next(r)
    for row in r:
        try: oil[row[0][:7]] = float(row[1])
        except ValueError: pass
ks = sorted(k for k in oil if k >= "1987-01")
ratios = [oil[ks[i + 2]] / oil[ks[i]] for i in range(len(ks) - 2)]
print(f"Öl: Monatsmittel 2 Monate später > 92,6 % des Ausgangswerts: {np.mean(np.array(ratios) > 100 / 108):.0%} von {len(ratios)} Fällen")

# Bundrendite: Juni 2027 über 3,5 % bei 3,42 % im Oktober 2026 (8 Monate)
b = E("bond_m_long")
bk = sorted(b)
ch = [b[bk[i + 8]] - b[bk[i]] for i in range(len(bk) - 8)]
print(f"Bundrendite: Anstieg um mehr als 0,08 Pp. in 8 Monaten: {np.mean(np.array(ch) > 0.08):.0%} von {len(ch)} (seit {bk[0]})")

# Industrieproduktion: 1. Quartal über Vorjahresquartal
ip = E("indprod_m")
q1 = {}
for k, v in ip.items():
    y, mo = k.split("-")
    if mo in ("01", "02", "03"):
        q1.setdefault(int(y), []).append(v)
q1 = {y: np.mean(v) for y, v in q1.items() if len(v) == 3}
up = [y for y in q1 if y - 1 in q1 and q1[y] > q1[y - 1]]
tot = [y for y in q1 if y - 1 in q1]
print("Industrieproduktion Q1 über Vorjahr:", len(up), "von", len(tot), "| seit 2018:", sum(y >= 2018 for y in up), "von", sum(y >= 2018 for y in tot))
print("Letzte Monate Industrieproduktion:", {k: ip[k] for k in sorted(ip)[-6:]})

# Industrieproduktion: 4. Quartal über Vorjahresquartal
q4 = {}
for k, v in ip.items():
    y, mo = k.split("-")
    if mo in ("10", "11", "12"):
        q4.setdefault(int(y), []).append(v)
q4 = {y: np.mean(v) for y, v in q4.items() if len(v) == 3}
up4 = [y for y in q4 if y - 1 in q4 and q4[y] > q4[y - 1]]
tot4 = [y for y in q4 if y - 1 in q4]
print("Industrieproduktion Q4 über Vorjahr:", len(up4), "von", len(tot4), "| seit 2018:", sum(y >= 2018 for y in up4), "von", sum(y >= 2018 for y in tot4))

# Gas Europa: Monatsmittel vier Monate später mindestens 16 % höher (Sept. 2026 rund 78 €/MWh -> Jan. 2027 über 90 €)
gas = {}
with open(d / "PNGASEUUSDM.csv") as f:
    r = csv.reader(f); next(r)
    for row in r:
        try: gas[row[0][:7]] = float(row[1])
        except ValueError: pass
gk = sorted(gas)
gr = [gas[gk[i + 4]] / gas[gk[i]] for i in range(len(gk) - 4)]
print(f"Gas Europa: vier Monate später mindestens +16 %: {np.mean(np.array(gr) > 1.16):.0%} von {len(gr)} (seit {gk[0]})")
print("Gas Europa Sept. 2026 in €/MWh (Kurs 1,12):", round(gas['2026-09'] / 0.29307 / 1.12, 1))

# EZB: Folgte auf eine Erhöhung des Einlagesatzes binnen sechs Monaten eine weitere?
import datetime as dt
rows = list(csv.DictReader(open(d / "ecb_dfr.csv", encoding="utf-8")))
ser = [(dt.date.fromisoformat(r["TIME_PERIOD"]), float(r["OBS_VALUE"])) for r in rows if r.get("OBS_VALUE")]
hikes = [ser[i][0] for i in range(1, len(ser)) if ser[i][1] > ser[i - 1][1] + 1e-9]
foll = [h for h in hikes if any(0 < (h2 - h).days <= 183 for h2 in hikes)]
print(f"EZB: Erhöhungen seit 1999: {len(hikes)}, davon mit weiterer binnen 6 Monaten: {len(foll)}; letzte: {hikes[-3:]}, aktueller Satz {ser[-1]}")

# Industrieanteil DE: Rückgang um mehr als 0,9 Pp. in fünf Jahren
mg_, tg_ = E("manuf_gva")["DE"], E("total_gva")["DE"]
sh = {int(y): mg_[y] / tg_[y] * 100 for y in mg_ if y in tg_}
w5 = {y: sh[y + 5] - sh[y] for y in sh if y + 5 in sh}
print("Industrieanteil: 5-Jahres-Rückgang > 0,9 Pp.:", sum(v < -0.9 for v in w5.values()), "von", len(w5))
