# Basisraten des Zukunftsatlas Deutschland 2035

Mit diesen Skripten lassen sich die Basisraten und die Achsen des Atlas aus öffentlichen Daten nachrechnen. Die Rohdaten liegen nicht im Repo; die Schritte unten laden sie neu (Stand der Seite: Abruf am 13.11.2026, spätere Abrufe können durch Revisionen leicht abweichen).

## Daten holen

```bash
mkdir daten
python eurostat.py daten
curl -o daten/WTISPLC.csv "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WTISPLC"
curl -o daten/CPIAUCSL.csv "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
curl -o daten/PNGASEUUSDM.csv "https://fred.stlouisfed.org/graph/fredgraph.csv?id=PNGASEUUSDM"
curl -o daten/ecb_dfr.csv "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?format=csvdata"
```

`panel.py` und `signale.py` laden fehlende Eurostat-Reihen selbst nach.

## Rechnen

| Skript | Was es rechnet |
|---|---|
| `basisraten.py daten` | Defizite (U1), Produktivität (U2), Nettozuwanderung (U3), Zins gegen Wachstum (U5), Industrieanteil (U8) |
| `energie.py daten` | Energiepreisschocks seit 1973: Preis zwei Jahre nach dem Gipfel (U7) |
| `panel.py daten` | Zusammenhänge zwischen den Unsicherheiten in 42 Länder-Jahrzehnten aus Westeuropa |
| `achsen.py` | geschätzte Zusammenhänge, Faktoranalyse, alle Aufteilungen der neun auf zwei Achsen, Simulation der Felder |
| `signale.py daten` | Basisraten der Signale (Produktivität, Bevölkerung, Zuwanderung, Öl, Gas, Renditen, Industrieproduktion, EZB) |

## Weitere Quellen

- Beitragssätze zur Sozialversicherung 1995–2026: sozialpolitik-aktuell.de, Abbildung II.8 (U4).
- KI-Nutzung 2023 und 2024: Destatis; 2025: Jahresgutachten 2026/27.
- NATO-Ziele und Verteidigungsquoten: NATO; Schätzung für Deutschland 2026 laut Berichten zum Gipfel in Ankara (Juli 2026).
- Referenzwerte und Prognosen: Jahresgutachten 2026/27 des Sachverständigenrates.

Die Zusammenhänge in `achsen.py` sind Schätzungen, mit Daten geprüft, wo es welche gibt. Die Einschätzungen auf der Seite sind die von arq decisions.
