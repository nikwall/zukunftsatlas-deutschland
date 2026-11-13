"""Fetch Eurostat JSON-stat series and save them as {geo: {year: value}} JSON.

Usage: python -I eurostat.py <outdir>
"""
import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
GEOS = ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "FI", "SE", "DK", "IE", "PT", "EL", "LU",
        "NO", "CH", "PL", "CZ", "HU", "SK", "SI", "EE", "LV", "LT"]

QUERIES = {
    "deficit": ("gov_10dd_edpt1", {"na_item": "B9", "sector": "S13", "unit": "PC_GDP"}),
    "interest": ("gov_10a_main", {"na_item": "D41PAY", "sector": "S13", "unit": "PC_GDP"}),
    "prod_hour": ("nama_10_lp_ulc", {"na_item": "RLPR_HW", "unit": "I15"}),
    "netmig": ("demo_gind", {"indic_de": "CNMIGRAT"}),
    "gdp_nominal": ("nama_10_gdp", {"na_item": "B1GQ", "unit": "CP_MEUR"}),
    "manuf_gva": ("nama_10_a10", {"na_item": "B1G", "unit": "CP_MEUR", "nace_r2": "C"}),
    "total_gva": ("nama_10_a10", {"na_item": "B1G", "unit": "CP_MEUR", "nace_r2": "TOTAL"}),
    "bond10y": ("irt_lt_mcby_a", {"int_rt": "MCBY"}),
}


def fetch(dataset, params):
    q = "&".join([f"{k}={v}" for k, v in params.items()] + [f"geo={g}" for g in GEOS])
    url = f"{BASE}{dataset}?format=JSON&lang=EN&{q}"
    with urllib.request.urlopen(url, timeout=120) as r:
        js = json.load(r)
    ids, sizes = js["id"], js["size"]
    dims = js["dimension"]
    # index -> label for each dimension
    cats = {d: {v: k for k, v in dims[d]["category"]["index"].items()} for d in ids}
    out = {}
    for flat, val in js["value"].items():
        flat = int(flat)
        coords = {}
        for d, s in zip(reversed(ids), reversed(sizes)):
            coords[d] = cats[d][flat % s]
            flat //= s
        out.setdefault(coords["geo"], {})[coords["time"]] = val
    return out


def main():
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    for name, (ds, params) in QUERIES.items():
        try:
            data = fetch(ds, params)
            (outdir / f"{name}.json").write_text(json.dumps(data, indent=0))
            de = data.get("DE", {})
            yrs = sorted(de)
            print(name, "geos:", len(data), "DE years:", yrs[:1], "...", yrs[-1:] if yrs else None)
        except Exception as e:  # noqa: BLE001
            print(name, "FAILED", e)


if __name__ == "__main__":
    main()
