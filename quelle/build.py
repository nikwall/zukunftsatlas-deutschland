"""Zukunftsatlas Deutschland 2035 bauen: atlas.toml + vorlage.html -> out/index.html (mit assets/).

    python build.py

Prüft Pflichtfelder, Wahrscheinlichkeiten, Daten und Achsen; bricht ab, wenn ein gesperrter Name im Text steht.
"""
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

HIER = Path(__file__).resolve().parent
FRUEH_BIS = dt.date(2027, 6, 30)   # Standardfilter der Signalspalte
GESPERRT = {"d1a69b55256558f6aacca286ef45b90dfd7bb3335169588333ba5363e3b8a829"}   # SHA-256 von Namen, die auf öffentlichen Seiten nicht stehen dürfen


def gesperrt(text):
    return any(hashlib.sha256(w.encode()).hexdigest() in GESPERRT for w in re.findall(r"[a-z]+", text.lower()))
OUT = HIER / "out"
GRUPPEN = {"A": "Umfeld", "B": "Basis", "L": "Ergebnis · Lücke", "I": "Ergebnis · Industrie"}
CROWD = {"ja": ("crowd-ja", "Für Prognosegruppen"), "bedingt": ("", "Bedingt für Gruppen"), "nein": ("", "Fachfrage")}
GRUENDE_S = ["Warum dieses Signal", "Was dafür spricht", "Was dagegen spricht"]
GRUENDE_U = ["Warum sie zählt", "Was dafür spricht", "Was dagegen spricht"]
MM = {"PM": [1, 0, 0, 0], "PP": [0, 1, 0, 0], "MM": [0, 0, 1, 0], "MP": [0, 0, 0, 1]}
T = {
    "lesart_heute": "Heute führt der wahrscheinlichste Pfad ins Feld",
    "lesart_wasw1": "Mit Ihrer Was-wäre-wenn-Antwort führt der wahrscheinlichste Pfad ins Feld",
    "lesart_wasw": "Mit Ihren {n} Was-wäre-wenn-Antworten führt der wahrscheinlichste Pfad ins Feld",
    "notiz_heute": "Ein Feld ist so wahrscheinlich wie das Produkt seiner beiden Achsen.",
    "notiz_wasw": "Zurücksetzen unter der Karte.",
    "hinweis_karte": "Zeigen Sie auf ein Signal oder wählen Sie Ja oder Nein, um zu sehen, wohin sich die Markierung bewegt.",
    "vorschau_bleibt": "Ein Ja bei <b>{s}</b>: {f} bleibt vorn ({p}).",
    "vorschau_wechsel": "Ein Ja bei <b>{s}</b>: {f} rückt nach vorn ({p}).",
    "vorschau_erg": "Ein Ja bei <b>{s}</b>: {o}.",
    "kaum": "kaum Veränderung",
}


class Fehler(Exception):
    pass


def nbsp(s):
    """Geschütztes Leerzeichen vor %, €, $ und zwischen Zahl und Einheit."""
    return re.sub(r" (%|€|\$)", " \\1", s)


def prob(v, wo):
    if not isinstance(v, (int, float)) or not 0 < v < 1:
        raise Fehler(f"{wo}: Wahrscheinlichkeit {v!r} liegt nicht zwischen 0 und 1")
    return float(v)


def pct(v):
    return f"{round(v * 100)} %"


def mm(cells):
    pos = [(0, 0), (14, 0), (0, 14), (14, 14)]
    rects = "".join(f'<rect{" class=\"on\"" if c else ""} x="{x}" y="{y}" width="12" height="12" rx="2"/>' for c, (x, y) in zip(cells, pos))
    return f'<svg class="mm" viewBox="0 0 26 26" aria-hidden="true">{rects}</svg>'


def dir_cells(ax, richtung):
    if ax == "A":
        return [1, 1, 0, 0] if richtung == "plus" else [0, 0, 1, 1]
    return [0, 1, 0, 1] if richtung == "plus" else [1, 0, 1, 0]


def lesen():
    roh = (HIER / "atlas.toml").read_text(encoding="utf-8")
    if gesperrt(roh):
        raise Fehler("Ein gesperrter Name steht im Text; auf öffentlichen Seiten nie nennen.")
    return tomllib.loads(roh)


def pruefen(d):
    for k in ("A", "B"):
        prob(d["achse"][k]["p"], f"achse.{k}.p")
    for k in ("L", "I"):
        for f in MM:
            prob(d["ergebnis"][k]["je_feld"][f], f"ergebnis.{k}.{f}")
    for f in MM:
        for key in ("name", "kurz", "szene", "zeichen"):
            if key not in d["feld"][f]:
                raise Fehler(f"feld.{f}: {key} fehlt")
    ids = set()
    for s in d["signal"]:
        wo = f"signal {s.get('id')}"
        for key in ("id", "datum", "wann", "achse", "richtung", "gewicht", "p", "kurz", "frage", "aufloesung", "referenz", "basisrate", "crowd", "gruende"):
            if key not in s:
                raise Fehler(f"{wo}: {key} fehlt")
        if s["id"] in ids:
            raise Fehler(f"{wo}: doppelte id")
        ids.add(s["id"])
        prob(s["p"], wo)
        if s["achse"] not in GRUPPEN or s["richtung"] not in ("plus", "minus") or s["gewicht"] not in (1, 2, 3):
            raise Fehler(f"{wo}: achse, richtung oder gewicht ungültig")
        if s["crowd"] not in CROWD or len(s["gruende"]) != 3 or not isinstance(s["datum"], dt.date):
            raise Fehler(f"{wo}: crowd, gruende (genau drei) oder datum ungültig")
        if s.get("aufgeloest") not in (None, "ja", "nein"):
            raise Fehler(f"{wo}: aufgeloest muss ja oder nein sein")
    for u in d["unsicherheit"]:
        prob(u["p"], f"unsicherheit {u['id']}")
        if len(u["gruende"]) != 3:
            raise Fehler(f"unsicherheit {u['id']}: genau drei Gründe")


def then_text(s, d):
    ax, r = s["achse"], s["richtung"]
    if ax == "A":
        return f'Ein Ja macht das Umfeld <b>{d["achse"]["A"]["pol_plus" if r == "plus" else "pol_minus"]}</b>.'
    if ax == "B":
        return f'Ein Ja macht die Basis <b>{d["achse"]["B"]["pol_plus" if r == "plus" else "pol_minus"]}</b>.'
    if ax == "L":
        return "Ein Ja spricht dafür, dass die <b>Lücke geschlossen</b> wird." if r == "plus" else "Ein Ja spricht dafür, dass die <b>Lücke offen</b> bleibt."
    return "Ein Ja spricht dafür, dass die <b>Industrie hält</b>." if r == "plus" else "Ein Ja spricht dafür, dass die <b>Industrie schrumpft</b>."


def karte_signal(s, d):
    ax, done = s["achse"], s.get("aufgeloest")
    cls, crowd_txt = CROWD[s["crowd"]]
    tags = (f'<div class="tags"><span class="tag when">{s["wann"]}</span><span class="tag g c-{ax}">{GRUPPEN[ax]}</span>'
            f'<span class="tag {cls}">{crowd_txt}</span></div>')
    pv = ("Ja" if done == "ja" else "Nein") if done else f'{round(s["p"] * 100)}<small> %</small>'
    facts = f'<div class="facts"><span><b>Basisrate:</b> {s["basisrate"]}</span></div>'
    icon = mm(dir_cells(ax, s["richtung"])) if ax in ("A", "B") else ""
    then = f'<p class="then">{icon}<span>{then_text(s, d)}</span></p>'
    if done:
        ctrl = f'<span class="resolved">Aufgelöst: {"Ja" if done == "ja" else "Nein"}</span>'
    else:
        ctrl = (f'<div class="seg3" role="group" aria-label="Was-wäre-wenn für: {s["kurz"]}">'
                '<button type="button" data-v="open" aria-pressed="true">Offen</button>'
                '<button type="button" data-v="yes" aria-pressed="false">Ja</button>'
                '<button type="button" data-v="no" aria-pressed="false">Nein</button></div>')
    gr = "".join(f"<li><em>{lab}:</em> {txt}</li>" for lab, txt in zip(GRUENDE_S, s["gruende"]))
    quelle = (f'<p class="src"><b>Auflösung:</b> {s["aufloesung"]}</p><p class="src"><b>Referenz:</b> {s["referenz"]}</p>')
    why = f'<details class="why"><summary>Drei Gründe, Auflösung und Referenz</summary><ul class="reasons">{gr}</ul>{quelle}</details>'
    frueh = "1" if s["datum"] <= FRUEH_BIS else "0"
    return (f'<article class="sig c-{ax}{" done" if done else ""}" id="c{s["id"]}" data-id="{s["id"]}" data-ax="{ax}" data-crowd="{s["crowd"]}" data-frueh="{frueh}" tabindex="-1">'
            f'{tags}<p class="qt">{s["frage"]}</p><p class="pv">{pv}</p><div class="bar"><i style="width:{s["p"] * 100:.0f}%"></i></div>'
            f'{facts}{then}{ctrl}{why}</article>')


def bauen():
    d = lesen()
    pruefen(d)
    S, A, B = d["seite"], d["achse"]["A"], d["achse"]["B"]
    stand = S["stand"].strftime("%d.%m.%Y")
    signale = sorted(d["signal"], key=lambda s: (s["datum"], s["id"]))

    # Signale nach Gruppen
    blocks = []
    for key, titel, nr in (("A", A["frage"], "1"), ("B", B["frage"], "2"), ("E", "Was die Karte je Feld zeigt: Lücke und Industrie", "")):
        grp = [s for s in signale if (s["achse"] in ("L", "I")) == (key == "E") and (key == "E" or s["achse"] == key)]
        name = {"A": "Umfeld", "B": "Basis", "E": "Ergebnis"}[key]
        nummer = f'<span class="n">{nr}</span>' if nr else ""
        blocks.append(f'<div class="grp">{nummer}{titel} <small>{name} · {len(grp)} Signale</small></div>')
        blocks += [karte_signal(s, d) for s in grp]

    # Felder
    L, I = d["ergebnis"]["L"], d["ergebnis"]["I"]
    felder = []
    for k in ("PM", "PP", "MM", "MP"):
        f = d["feld"][k]
        z = "".join(f"<li>{x}</li>" for x in f["zeichen"])
        felder.append(f'<div class="field" id="f{k}"><div class="h">{mm(MM[k])}<h3>{f["name"]}</h3><span class="fp"></span></div>'
                      f'<p class="scene">{f["szene"]}</p><ul>{z}</ul>'
                      f'<div class="res"><span>{L["name"]}: <b>{pct(L["je_feld"][k])}</b></span><span>{I["name"]}: <b>{pct(I["je_feld"][k])}</b></span></div></div>')

    # Unsicherheiten
    U = {u["id"]: u for u in d["unsicherheit"]}
    def ukarte(u):
        gr = "".join(f"<li><em>{lab}:</em> {txt}</li>" for lab, txt in zip(GRUENDE_U, u["gruende"]))
        return (f'<article class="ucard"><div class="h"><h4><small>{u["id"]} · {u["zaehlt"]}</small>{u["titel"]}</h4>'
                f'<span class="up">{round(u["p"] * 100)}<small> %</small></span></div>'
                f'<p class="crit"><b>Ja, wenn:</b> {u["kriterium"]}</p><p class="base"><b>Basisrate:</b> {u["basisrate"]}</p>'
                f'<ul class="reasons">{gr}</ul></article>')
    uns = []
    for cls, titel, regel, ids in (
        ("c-A", f"Achse 1 · Umfeld: {A['frage']}", A["regel"], A["bestandteile"]),
        ("c-B", f"Achse 2 · Basis: {B['frage']}", B["regel"], B["bestandteile"]),
        ("c-L", "Ergebnis: was die Karte je Feld zeigt",
         "Lücke und Industrie gehen in keine Achse ein, weil sie an beiden hängen. Ihre Wahrscheinlichkeit hängt am Feld; die Karte zeigt sie unter dem Raster.",
         ["U1", "U8"]),
    ):
        karten = "".join(ukarte(U[i]) for i in ids)
        uns.append(f'<div class="ugrp {cls}"><h3>{titel}</h3><p class="rule">{regel}</p><div class="ucards">{karten}</div></div>')

    # Zeitstrahl
    tl, rest, start = [], list(signale), None
    for zr in d["zeitraum"]:
        teil = [s for s in rest if s["datum"] <= zr["bis"]]
        rest = [s for s in rest if s["datum"] > zr["bis"]]
        if not teil:
            continue
        li = "".join(f'<li class="{"done" if s.get("aufgeloest") else ""}"><a class="c-{s["achse"]}" href="#c{s["id"]}"><span>{s["kurz"]}'
                     f'<span class="w">{s["wann"]}</span></span><span class="tp">{pct(s["p"]) if not s.get("aufgeloest") else ("Ja" if s["aufgeloest"] == "ja" else "Nein")}</span></a></li>'
                     for s in teil)
        tl.append(f'<div class="tlp"><h3>{zr["name"]}<small>{len(teil)} Signale</small></h3><ol>{li}</ol></div>')
    if rest:
        raise Fehler(f"Signale nach dem letzten Zeitraum: {[s['id'] for s in rest]}")
    bis_juni = sum(1 for s in signale if s["datum"] <= FRUEH_BIS)

    kz = "".join(f'<div><b>{k["wert"]}</b><span>{k["text"]}</span></div>' for k in d["kennzahl"])
    methode = "".join(f'<div class="mcard"><h4>{h}</h4><p>{t}</p></div>' for h, t in (
        ("Neun Unsicherheiten",
         "Aus dem Jahresgutachten 2026/27 des Sachverständigenrates haben wir neun Unsicherheiten abgeleitet. Jede hat ein Kriterium, das sich später prüfen lässt, eine Basisrate aus öffentlichen Daten (Eurostat, FRED, EZB, Destatis) und unsere Einschätzung mit drei Gründen."),
        ("Zwei Achsen aus neun",
         "Wir haben geschätzt und an 42 Länder-Jahrzehnten aus Westeuropa geprüft, wie die neun zusammenhängen. Daraus entstehen zwei Bündel, die kaum korrelieren (−0,04): das Umfeld und die Basis. Lücke und Industrie hängen an beiden und werden je Feld gezeigt."),
        ("Felder und Was-wäre-wenn",
         "Ein Feld ist so wahrscheinlich wie das Produkt seiner Achsen; mit dem schwachen Zusammenhang gerechnet weicht es um höchstens einen Punkt ab. Lücke und Industrie je Feld stammen aus 400.000 Simulationen. Wie stark ein Signal wirkt, ist unsere Einschätzung; im Mittel bleibt die heutige Prognose gleich."),
    ))
    ueber = (f'<p>Dieser Zukunftsatlas ist ein öffentliches Beispiel der Methode Perspektiv von arq decisions. Er bleibt stehen und wird aktualisiert, sobald Signale auflösen; '
             f'{bis_juni} der {len(signale)} Signale lösen bis Ende Juni 2027 auf.</p>'
             f'<p>Rechenwege der Basisraten und Quellen der Seite: <a href="{S["repo"]}">{S["repo"].removeprefix("https://")}</a>. '
             f'Hinweise, Einwände und Fragen an <a href="mailto:{S["kontakt"]}">{S["kontakt"]}</a>.</p>')
    fuss = (f'{S["titel"]} · Stand {stand} · Methode: Perspektiv von <a href="https://www.arqdecisions.com/perspektiv">arq decisions</a> · '
            'arq decisions GmbH · Eifflerstraße 43 · 22769 Hamburg · '
            '<a href="https://www.arqdecisions.com/impressum">Impressum</a> · <a href="https://www.arqdecisions.com/privacy">Datenschutz</a>')

    ph = {
        "ROBOTS": "index, follow" if S.get("indexieren") else "noindex, nofollow", "URL": S["url"],
        "TITEL": S["titel"], "BESCHREIBUNG": S["beschreibung"], "OVERLINE": S["overline"],
        "CHIPS": f'<span class="chip real">Basisraten und Prognosen · Stand {stand}</span><span class="chip judg">Einschätzungen, Felder und Was-wäre-wenn: unsere</span>',
        "LEITFRAGE": S["leitfrage"], "EINLEITUNG": S["einleitung"], "KENNZAHLEN": kz,
        "KZ_NOTE": f'Zahlen aus dem <a href="{S["gutachten_link"]}">Jahresgutachten 2026/27</a> des Sachverständigenrates, veröffentlicht am 11.11.2026. '
                   'Der Rat spricht von einer „Konsolidierungsaufgabe von historischem Ausmaß“.',
        "A_FRAGE": A["frage"], "B_FRAGE": B["frage"], "A_PLUS": A["pol_plus"], "A_MINUS": A["pol_minus"],
        "B_PLUS": B["pol_plus"], "B_MINUS": B["pol_minus"],
        "L_NAME": L["name"], "I_NAME": I["name"], "N_FRUEH": bis_juni, "N_ALLE": len(signale),
        "SIGNALE": "".join(blocks), "FELDER": "".join(felder),
        "UNS_INTRO": "Jede Achse bündelt mehrere Unsicherheiten. Wir haben sie so gewählt, dass die beiden Achsen kaum zusammenhängen. "
                     "Lücke und Industrie hängen an beiden; sie sind das, was die Karte je Feld zeigt.",
        "UNSICHERHEITEN": "".join(uns), "ZEITSTRAHL": "".join(tl), "METHODE": methode, "UEBER": ueber, "FUSS": fuss,
    }
    for k in ("PP", "PM", "MP", "MM"):
        ph[f"{k}_NAME"], ph[f"{k}_KURZ"] = d["feld"][k]["name"], d["feld"][k]["kurz"]

    html = (HIER / "vorlage.html").read_text(encoding="utf-8")
    def ersetze(m):
        if m.group(1) not in ph:
            raise Fehler(f"Platzhalter {{{{{m.group(1)}}}}} ohne Wert")
        return nbsp(str(ph[m.group(1)]))
    html = re.sub(r"\{\{(\w+)\}\}", ersetze, html)

    daten = {
        "t": T,
        "achsen": {k: {x: d["achse"][k][x] for x in ("frage", "pol_plus", "pol_minus", "kurz_plus", "kurz_minus", "aussage", "p")} for k in ("A", "B")},
        "ergebnisse": {k: {"name": d["ergebnis"][k]["name"], "je_feld": d["ergebnis"][k]["je_feld"]} for k in ("L", "I")},
        "felder": {k: {"name": d["feld"][k]["name"]} for k in MM},
        "signale": [{x: s[x] for x in ("id", "achse", "richtung", "gewicht", "p", "kurz")} | {"aufgeloest": {"ja": "yes", "nein": "no"}.get(s.get("aufgeloest"))}
                    for s in signale],
    }
    html = html.replace("/*__DATA__*/null", json.dumps(daten, ensure_ascii=False))
    if "{{" in html or gesperrt(html):
        raise Fehler("Ungefüllter Platzhalter oder verbotener Name in der Ausgabe")

    # out/ ist die Arbeitskopie des öffentlichen Repos: nur die erzeugten Teile ersetzen, .git bleibt.
    OUT.mkdir(exist_ok=True)
    for name in ("assets", "quelle", "basisraten"):
        if (OUT / name).exists():
            shutil.rmtree(OUT / name)
    shutil.copytree(HIER / "assets", OUT / "assets")
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "quelle").mkdir()
    for f in ("atlas.toml", "vorlage.html", "build.py", "vorschaubild.py"):
        shutil.copy2(HIER / f, OUT / "quelle" / f)
    (OUT / "basisraten").mkdir()
    for f in sorted((HIER.parent / "basisraten").glob("*.py")) + [HIER.parent / "basisraten" / "README.md"]:
        shutil.copy2(f, OUT / "basisraten" / f.name)
    (OUT / "README.md").write_text(
        f"# {S['titel']}\n\n{S['beschreibung']}\n\nSeite: {S['url']}\n\n"
        "- `index.html`, `assets/`: die veröffentlichte Seite (GitHub Pages).\n"
        "- `quelle/`: Inhalt (`atlas.toml`), Vorlage und Build der Seite.\n"
        "- `basisraten/`: Skripte, mit denen die Basisraten aus öffentlichen Daten nachgerechnet werden.\n\n"
        "arq decisions GmbH · Eifflerstraße 43 · 22769 Hamburg · kontakt@arqdecisions.com\n", encoding="utf-8")
    for f in OUT.rglob("*"):
        if f.is_file() and f.suffix in (".html", ".md", ".py", ".toml") and gesperrt(f.read_text(encoding="utf-8", errors="ignore")):
            raise Fehler(f"Gesperrter Name in {f.relative_to(OUT)}")
    print(f"gebaut: {OUT / 'index.html'} ({len(html) // 1024} KB), {len(signale)} Signale, {bis_juni} bis Ende Juni 2027")


if __name__ == "__main__":
    try:
        bauen()
    except Fehler as e:
        sys.exit(f"Abbruch: {e}")
