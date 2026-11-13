"""Compute base rates from the Eurostat downloads. Usage: python -I basisraten.py <datadir>"""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
L = lambda n: {g: {int(y): v for y, v in s.items() if v is not None} for g, s in json.loads((d / f"{n}.json").read_text()).items()}

WEST = ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "FI", "SE", "DK", "PT", "EL", "NO", "CH"]  # ohne IE, LU

def avg_growth(s, a, b):
    if a in s and b in s and s[a] > 0:
        return ((s[b] / s[a]) ** (1 / (b - a)) - 1) * 100
    return None

print("=== U1 Defizit ===")
deficit = L("deficit")
de = deficit["DE"]
print("DE:", {y: round(v, 1) for y, v in sorted(de.items())})
ok = [y for y, v in de.items() if v >= -3.0]
print(f"DE Jahre <=3 %: {len(ok)} von {len(de)}")
# international: Jahre mit Defizit > 4 %, Lage 9 Jahre später
hits = tot = 0
for g, s in deficit.items():
    for y, v in s.items():
        if v < -4.0 and (y + 9) in s:
            tot += 1
            hits += s[y + 9] >= -3.0
print(f"Länderjahre mit Defizit >4 %: nach 9 Jahren <=3 %: {hits}/{tot}")
# episodenbasiert: erstes Jahr einer >3 %-Phase, Jahre bis <=3 %
for g in ["DE"] + [x for x in deficit if x != "DE"]:
    s = deficit[g]; yrs = sorted(s); ep = []
    i = 0
    while i < len(yrs):
        if s[yrs[i]] < -3.0:
            start = yrs[i]
            j = i
            while j < len(yrs) and s[yrs[j]] < -3.0:
                j += 1
            ep.append((start, yrs[j] if j < len(yrs) else None))
            i = j
        else:
            i += 1
    if g == "DE":
        print("DE Episoden >3 % (Start, erstes Jahr wieder <=3 %):", ep)

print("\n=== U2 Produktivität je Stunde ===")
prod = L("prod_hour")
p = prod["DE"]
for a, b in [(1995, 2005), (2005, 2015), (2015, 2025), (2010, 2020), (2016, 2025)]:
    print(f"DE {a}-{b}: {avg_growth(p, a, b):.2f} % p.a.")
w = [avg_growth(p, y - 10, y) for y in range(2001, 2026)]
print("DE 10J-Fenster (Ende 2001..2025):", [round(x, 2) for x in w])
print("DE Fenster >=1,2 %:", sum(x >= 1.2 for x in w), "von", len(w))
for start_end in [(2005, 2025), (2015, 2025)]:
    n = k = 0
    for g in WEST:
        s = prod.get(g, {})
        for y in range(start_end[0], start_end[1] + 1):
            x = avg_growth(s, y - 10, y)
            if x is not None:
                n += 1; k += x >= 1.2
    print(f"Westeuropa, 10J-Fenster mit Ende {start_end}: >=1,2 % in {k}/{n}")
# Beschleunigung: Fenster, in denen ein Land nach einem Jahrzehnt <0,9 % im nächsten >=1,2 % schaffte
n = k = 0
for g in WEST:
    s = prod.get(g, {})
    for y in range(2001, 2016):
        a = avg_growth(s, y - 10, y); b = avg_growth(s, y, y + 10)
        if a is not None and b is not None and a < 0.9:
            n += 1; k += b >= 1.2
print(f"Westeuropa: nach Jahrzehnt <0,9 % folgte >=1,2 %: {k}/{n}")
print("DE 2024, 2025 Wachstum:", round((p[2024]/p[2023]-1)*100, 2), round((p[2025]/p[2024]-1)*100, 2))

print("\n=== U3 Nettozuwanderung DE ===")
m = L("netmig")["DE"]
print({y: round(v / 1000) for y, v in sorted(m.items()) if y >= 1990})
def win(start_from):
    res = []
    for y in range(start_from, 2026 - 8):
        vals = [m[t] for t in range(y, y + 9) if t in m]
        if len(vals) == 9:
            res.append(sum(vals) / 9)
    return res
for sf in (1960, 1991):
    r = win(sf)
    print(f"9J-Fenster ab {sf}: Schnitt >=200k in {sum(x >= 200000 for x in r)}/{len(r)}")
yrs = [y for y in m if y >= 1991]
print("Jahre >=200k seit 1991:", sum(m[y] >= 200000 for y in yrs), "von", len(yrs))
print("Jahre <100k seit 1991:", sum(m[y] < 100000 for y in yrs), "von", len(yrs))

print("\n=== U5 Zins vs. Wachstum DE ===")
bond = L("bond10y")["DE"]; gdp = L("gdp_nominal")["DE"]; intr = L("interest")["DE"]
print("Rendite 10J:", {y: round(v, 2) for y, v in sorted(bond.items()) if y >= 2015})
print("Zinsausgaben % BIP:", {y: round(v, 1) for y, v in sorted(intr.items())})
n = k = 0
rows = []
for y in range(1996, 2022):
    r_ = [bond[t] for t in range(y, y + 5) if t in bond]
    g_ = [(gdp[t] / gdp[t - 1] - 1) * 100 for t in range(y, y + 5) if t in gdp and t - 1 in gdp]
    if len(r_) == 5 and len(g_) == 5:
        n += 1; diff = sum(r_) / 5 - sum(g_) / 5; k += diff > 0; rows.append((y, round(diff, 2)))
print("5J-Fenster r>g:", k, "/", n, rows)
print("Jahre Zinsausgaben >=2 % BIP:", sum(v >= 2 for v in intr.values()), "von", len(intr))
# international r>g windows 2000-2025
n = k = 0
bondall = L("bond10y"); gdpall = L("gdp_nominal")
for g in WEST:
    b_, y_ = bondall.get(g, {}), gdpall.get(g, {})
    for y in range(1996, 2022):
        r_ = [b_[t] for t in range(y, y + 5) if t in b_]
        g_ = [(y_[t] / y_[t - 1] - 1) * 100 for t in range(y, y + 5) if t in y_ and t - 1 in y_]
        if len(r_) == 5 and len(g_) == 5:
            n += 1; k += (sum(r_) - sum(g_)) / 5 > 0
print("Westeuropa 5J-Fenster r>g:", k, "/", n)

print("\n=== U8 Industrieanteil ===")
mg, tg = L("manuf_gva"), L("total_gva")
share = {g: {y: mg[g][y] / tg[g][y] * 100 for y in mg.get(g, {}) if y in tg.get(g, {})} for g in mg}
print("DE:", {y: round(v, 1) for y, v in sorted(share["DE"].items())})
n = k = 0
for g in WEST + ["PL", "CZ", "HU", "SK", "SI"]:
    s = share.get(g, {})
    for y in range(1995, 2016):
        if y in s and y + 10 in s and s[y] >= 15:
            n += 1; k += (s[y] - s[y + 10]) > 2.0
print(f"Länder-Fenster (Anteil >=15 %): Rückgang >2 Pp in 10 J: {k}/{n}")
s = share["DE"]
print("DE 10J-Änderungen:", {y: round(s[y + 10] - s[y], 1) for y in range(1991, 2016) if y + 10 in s})
