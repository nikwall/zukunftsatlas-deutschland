"""Data check for the correlation judgments: country-decade panel, Western Europe.

Usage: python -I panel.py <datadir>   (reads existing JSON, fetches four more series into the same dir)
"""
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
nan=float("nan")

d = Path(sys.argv[1])
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
WEST = ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "FI", "SE", "DK", "PT", "EL", "NO", "CH"]

EXTRA = {
    "netmig_rate": ("demo_gind", {"indic_de": "CNMIGRATRT"}),
    "soc_contrib": ("gov_10a_main", {"na_item": "D61REC", "sector": "S13", "unit": "PC_GDP"}),
    "defence": ("gov_10a_exp", {"cofog99": "GF02", "na_item": "TE", "sector": "S13", "unit": "PC_GDP"}),
    "hicp_energy": ("prc_hicp_aind", {"coicop": "NRG", "unit": "RCH_A_AVG"}),
}


def fetch(dataset, params):
    q = "&".join([f"{k}={v}" for k, v in params.items()] + [f"geo={g}" for g in WEST])
    with urllib.request.urlopen(f"{BASE}{dataset}?format=JSON&lang=EN&{q}", timeout=120) as r:
        js = json.load(r)
    ids, sizes, dims = js["id"], js["size"], js["dimension"]
    cats = {k: {v: c for c, v in dims[k]["category"]["index"].items()} for k in ids}
    out = {}
    for flat, val in js["value"].items():
        flat = int(flat); co = {}
        for k, s in zip(reversed(ids), reversed(sizes)):
            co[k] = cats[k][flat % s]; flat //= s
        out.setdefault(co["geo"], {})[co["time"]] = val
    return out


for name, (ds, p) in EXTRA.items():
    f = d / f"{name}.json"
    if not f.exists():
        f.write_text(json.dumps(fetch(ds, p)))

L = lambda n: {g: {int(y): v for y, v in s.items() if v is not None} for g, s in json.loads((d / f"{n}.json").read_text()).items()}
prod, mig, dfc, bond, gdp = L("prod_hour"), L("netmig_rate"), L("deficit"), L("bond10y"), L("gdp_nominal")
mg, tg, soc, dfn, nrg = L("manuf_gva"), L("total_gva"), L("soc_contrib"), L("defence"), L("hicp_energy")

WINDOWS = [(1995, 2005), (2005, 2015), (2015, 2025)]
rows = []
for g in WEST:
    for a, b in WINDOWS:
        yrs = range(a + 1, b + 1)
        def sf(fn):
            try:
                return fn()
            except (KeyError, ZeroDivisionError):
                return nan
        r = {
            "U2 Produktivitaet": sf(lambda: ((prod[g][b] / prod[g][a]) ** (1 / (b - a)) - 1) * 100),
            "U3 Zuwanderung": sf(lambda: np.mean([mig[g][y] for y in yrs])),
            "U1 Defizit (Saldo)": sf(lambda: np.mean([dfc[g][y] for y in yrs])),
            "U5 r minus g": sf(lambda: np.mean([bond[g][y] - (gdp[g][y] / gdp[g][y - 1] - 1) * 100 for y in yrs])),
            "U8 Industrieanteil D": sf(lambda: (mg[g][b] / tg[g][b] - mg[g][a] / tg[g][a]) * 100),
            "U4 Sozialbeitraege D": sf(lambda: soc[g][b] - soc[g][a]),
            "U6 Verteidigung D": sf(lambda: dfn[g][b] - dfn[g][a]),
            "U7 Energiepreise": sf(lambda: np.mean([nrg[g][y] for y in yrs])),
        }
        rows.append((g, a, r))

names = list(rows[0][2])
X = np.array([[r[n] for n in names] for _, _, r in rows])
win = np.array([a for _, a, _ in rows])
print("Zeilen:", len(rows), "je Variable vorhanden:", dict(zip([n[:3] for n in names], (~np.isnan(X)).sum(0))))
Xd = X.copy()
for a, _ in WINDOWS:
    m = win == a
    Xd[m] -= np.nanmean(Xd[m], axis=0)
def pc(M):
    k = M.shape[1]; C = np.full((k, k), nan); N = np.zeros((k, k), int)
    for i in range(k):
        for j in range(k):
            ok = ~np.isnan(M[:, i]) & ~np.isnan(M[:, j]); N[i, j] = ok.sum()
            if ok.sum() > 5:
                C[i, j] = np.corrcoef(M[ok, i], M[ok, j])[0, 1]
    return C, N
for label, M in [("gepoolt", X), ("innerhalb der Jahrzehnte", Xd)]:
    C, N = pc(M)
    print(f"\nKorrelationen ({label}):")
    print(" " * 22 + "".join(f"{n[:3]:>7}" for n in names))
    for i, n in enumerate(names):
        print(f"{n:22}" + "".join(f"{C[i, j]:7.2f}" for j in range(len(names))))
print("\nn je Paar (min):", N[N > 0].min(), "max:", N.max())
