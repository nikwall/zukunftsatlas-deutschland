"""Vorschaubild für Linkvorschauen (1200 x 630) aus atlas.toml rendern: assets/og.png.

    python vorschaubild.py

Braucht Microsoft Edge (lokal installiert). Neu ausführen, wenn sich Achsen oder Felder ändern.
"""
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path

HIER = Path(__file__).resolve().parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

d = tomllib.loads((HIER / "atlas.toml").read_text(encoding="utf-8"))
a, b = d["achse"]["A"]["p"], d["achse"]["B"]["p"]
fp = {"PP": a * b, "PM": a * (1 - b), "MP": (1 - a) * b, "MM": (1 - a) * (1 - b)}
top = max(fp, key=fp.get)
pct = lambda v: f"{round(v * 100)}&nbsp;%"
assets = (HIER / "assets").as_uri()


def zelle(k, pos):
    f = d["feld"][k]
    cls = "c top" if k == top else "c"
    return f'<div class="{cls} {pos}"><b>{f["name"]}</b><span>{pct(fp[k])}</span></div>'


html = f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><style>
@font-face {{ font-family: Roboto; font-weight: 300 500; src: url({assets}/fonts/roboto-latin.woff2) format("woff2"); }}
@font-face {{ font-family: "Roboto Condensed"; font-weight: 700; src: url({assets}/fonts/RobotoCondensed-Bold.ttf) format("truetype"); }}
html, body {{ margin: 0; width: 1200px; height: 630px; background: #fbfcfa; font-family: Roboto, Arial, sans-serif; color: #2f3639; overflow: hidden; }}
.bar {{ height: 10px; width: 520px; margin: 0 auto; background: #bb2649; }}
.wrap {{ display: grid; grid-template-columns: 1fr 470px; gap: 48px; padding: 44px 64px 0; }}
.ov {{ font-size: 18px; font-weight: 500; letter-spacing: .14em; text-transform: uppercase; color: #5c7062; }}
.ov b {{ background: #135b49; color: #fff; border-radius: 30px; padding: 5px 14px; margin-right: 12px; letter-spacing: .12em; }}
h1 {{ margin: 34px 0 0; font-family: "Roboto Condensed"; font-weight: 700; font-size: 74px; line-height: 1.03; color: #bb2649; }}
p {{ margin: 24px 0 0; font-size: 23px; font-weight: 300; line-height: 1.4; max-width: 30ch; }}
.grid {{ margin-top: 30px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; height: 400px; }}
.c {{ background: #f1f5f0; padding: 18px 18px; display: flex; flex-direction: column; gap: 6px; border-top: 5px solid transparent; }}
.c.tl {{ border-radius: 14px 0 0 0; }} .c.tr {{ border-radius: 0 14px 0 0; }} .c.bl {{ border-radius: 0 0 0 14px; justify-content: flex-end; }} .c.br {{ border-radius: 0 0 14px 0; justify-content: flex-end; }}
.c b {{ font-family: "Roboto Condensed"; font-weight: 700; font-size: 27px; line-height: 1.08; color: #135b49; }}
.c span {{ font-family: "Roboto Condensed"; font-weight: 700; font-size: 38px; color: #135b49; }}
.c.top {{ background: #fff; border-top-color: #bb2649; box-shadow: inset 0 0 0 1px #d7e1d2; }}
.c.top b, .c.top span {{ color: #bb2649; }}
.ax {{ display: flex; justify-content: space-between; margin-top: 8px; font-size: 15px; font-weight: 500; letter-spacing: .1em; text-transform: uppercase; color: #5c7062; }}
.foot {{ position: absolute; left: 64px; right: 64px; bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; border-top: 2px solid #135b49; padding-top: 14px; font-size: 18px; color: #5c7062; }}
.foot img {{ height: 46px; }}
</style></head><body><div class="bar"></div><div class="wrap"><div>
<div class="ov"><b>Zukunftsatlas</b>Deutschland 2035</div>
<h1>{d["seite"]["leitfrage"]}</h1>
<p>Neun Unsicherheiten, zwei Achsen, vier Felder und {len(d["signal"])} Signale ab Dezember&nbsp;2026.</p>
</div><div>
<div class="grid">{zelle("PM", "tl")}{zelle("PP", "tr")}{zelle("MM", "bl")}{zelle("MP", "br")}</div>
<div class="ax"><span>← {d["achse"]["B"]["pol_minus"]}</span><span>↑ {d["achse"]["A"]["pol_plus"]} · ↓ {d["achse"]["A"]["pol_minus"]}</span><span>{d["achse"]["B"]["pol_plus"]} →</span></div>
</div></div>
<div class="foot"><span>Ausgangspunkt: Jahresgutachten 2026/27 des Sachverständigenrates · Stand {d["seite"]["stand"].strftime("%d.%m.%Y")}</span><img src="{assets}/arq_logo.png" alt=""></div>
</body></html>"""

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    src = Path(tmp) / "og.html"
    src.write_text(html, encoding="utf-8")
    ziel = HIER / "assets" / "og.png"
    if ziel.exists():
        ziel.unlink()
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={Path(tmp) / 'profil'}",
                    "--window-size=1200,630", "--virtual-time-budget=3000", f"--screenshot={ziel}", src.as_uri()], check=False)
    for _ in range(60):                      # Edge schreibt die Datei manchmal erst nach dem Beenden
        if ziel.exists() and ziel.stat().st_size > 0:
            break
        time.sleep(0.5)
    print("Vorschaubild:", ziel, ziel.stat().st_size if ziel.exists() else "fehlt")
