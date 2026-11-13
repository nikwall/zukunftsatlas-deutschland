"""Two composite axes from nine uncertainties, as uncorrelated as possible.

Correlations are for the latent drivers behind each yes/no criterion (orientation: "yes" as defined).
Judgment, checked against a Western-European country-decade panel where data exist (panel.py).
"""
import itertools
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
U = ["U1 Lücke geschlossen", "U2 Produktivität", "U3 Zuwanderung", "U4 Beiträge ≥46 %", "U5 Zins > Wachstum",
     "U6 Verteidigung 3,5 %", "U7 Energie günstig", "U8 Industrie hält", "U9 neue Krisenkasse"]
P = np.array([0.45, 0.20, 0.35, 0.55, 0.60, 0.60, 0.30, 0.40, 0.70])
pairs = {
    (1, 2): .25, (1, 3): .15, (1, 4): -.15, (1, 5): -.35, (1, 6): -.35, (1, 7): .25, (1, 8): .10, (1, 9): -.30,
    (2, 3): .00, (2, 4): -.15, (2, 5): -.25, (2, 6): .00, (2, 7): .20, (2, 8): .10, (2, 9): -.10,
    (3, 4): -.20, (3, 5): -.30, (3, 6): .15, (3, 7): .05, (3, 8): .05, (3, 9): .15,
    (4, 5): .05, (4, 6): .20, (4, 7): .00, (4, 8): -.15, (4, 9): .05,
    (5, 6): .10, (5, 7): -.10, (5, 8): .00, (5, 9): .00,
    (6, 7): -.25, (6, 8): .10, (6, 9): .20,
    (7, 8): .30, (7, 9): -.30,
    (8, 9): -.10,
}
n = 9
R = np.eye(n)
for (i, j), v in pairs.items():
    R[i - 1, j - 1] = R[j - 1, i - 1] = v
ev = np.linalg.eigvalsh(R)
print("kleinster Eigenwert (muss > 0 sein):", round(ev.min(), 3))

# --- Faktoranalyse light: zwei Hauptkomponenten, Varimax ---
w, V = np.linalg.eigh(R)
idx = np.argsort(w)[::-1]
w, V = w[idx], V[:, idx]
print("Eigenwerte:", np.round(w, 2), "Anteil der ersten zwei:", round(w[:2].sum() / n, 2))
Lmat = V[:, :2] * np.sqrt(w[:2])

def varimax(L, it=100):
    p, k = L.shape; Rm = np.eye(k); d = 0
    for _ in range(it):
        Lr = L @ Rm
        u, s, vt = np.linalg.svd(L.T @ (Lr ** 3 - Lr @ np.diag((Lr ** 2).sum(0)) / p))
        Rm = u @ vt
        if s.sum() < d * (1 + 1e-6): break
        d = s.sum()
    return L @ Rm

Lv = varimax(Lmat)
print("\nLadungen nach Varimax (F1, F2):")
for u, (a, b) in zip(U, Lv):
    print(f"  {u:24} {a:6.2f} {b:6.2f}")

# --- alle Aufteilungen: jede Unsicherheit in A, B oder keiner; Vorzeichen frei ---
def best_signs(items):
    best = None
    for signs in itertools.product([1, -1], repeat=len(items) - 1):
        s = np.zeros(n); s[items[0]] = 1
        for it, sg in zip(items[1:], signs): s[it] = sg
        inner = (s @ R @ s - len(items)) / 2  # Summe der Paar-Korrelationen mit Vorzeichen
        if best is None or inner > best[0]: best = (inner, s)
    return best

res = []
for assign in itertools.product([0, 1, 2], repeat=n):
    A = [i for i in range(n) if assign[i] == 1]; B = [i for i in range(n) if assign[i] == 2]
    if len(A) < 3 or len(B) < 3 or A[0] > B[0]: continue
    ia, a = best_signs(A); ib, b = best_signs(B)
    c = (a @ R @ b) / np.sqrt((a @ R @ a) * (b @ R @ b))
    mean_a, mean_b = ia / (len(A) * (len(A) - 1) / 2), ib / (len(B) * (len(B) - 1) / 2)
    res.append((abs(c), c, mean_a, mean_b, len(A) + len(B), A, B, a, b))

def show(r):
    _, c, ma, mb, k, A, B, a, b = r
    fa = ", ".join(("+" if a[i] > 0 else "−") + U[i][:3] for i in A)
    fb = ", ".join(("+" if b[i] > 0 else "−") + U[i][:3] for i in B)
    print(f"  r(A,B)={c:+.2f} | innen A {ma:.2f}, B {mb:.2f} | {k} von 9 | A: {fa} | B: {fb}")

for need in (9, 8, 7):
    sel = [r for r in res if r[4] == need and r[0] < 0.05 and min(r[2], r[3]) > 0.05]
    sel.sort(key=lambda r: -(r[2] + r[3]))
    print(f"\nBeste Aufteilungen mit {need} von 9, |r(A,B)| < 0,05, sortiert nach innerem Zusammenhang:")
    for r in sel[:6]: show(r)

# Vergleich: alter Vorschlag U2 × U1
print("\nKorrelation alter Vorschlag U2 × U1:", R[0, 1])

# --- Vorschlag: Umfeld (U6, U9, -U7) x Basis (U2, U3, -U4, -U5); U1 und U8 als Ergebnis je Feld ---
from scipy.stats import norm
def corr_of(A, B):
    a = np.zeros(n); b = np.zeros(n)
    for i, s in A: a[i] = s
    for i, s in B: b[i] = s
    inner = lambda v, k: (v @ R @ v - k) / (k * (k - 1))
    return (a @ R @ b) / np.sqrt((a @ R @ a) * (b @ R @ b)), inner(a, len(A)), inner(b, len(B))
UMF = [(5, 1), (8, 1), (6, -1)]
BAS = [(1, 1), (2, 1), (3, -1), (4, -1)]
c, ia, ib = corr_of(UMF, BAS)
print(f"\nVorschlag Umfeld x Basis: r latent {c:+.2f}, innen Umfeld {ia:.2f}, Basis {ib:.2f}")
c2, _, _ = corr_of(UMF + [(7, -1)], BAS)
print(f"  mit Industrie im Umfeld: r {c2:+.2f}")
c3, _, _ = corr_of(UMF, BAS + [(7, 1)])
print(f"  mit Industrie in der Basis: r {c3:+.2f}")

rng = np.random.default_rng(7)
Z = rng.multivariate_normal(np.zeros(n), R, size=400_000)
Y = Z < norm.ppf(P)          # True = "Ja" wie definiert
print("Kontrolle Randwahrscheinlichkeiten:", np.round(Y.mean(0), 2))
def pos(i, s): return Y[:, i] if s > 0 else ~Y[:, i]
umf_cnt = sum(pos(i, s).astype(int) for i, s in UMF)
bas_cnt = sum(pos(i, s).astype(int) for i, s in BAS)
for ru in (2,):
    for rb in (2, 3):
        rau = umf_cnt >= ru; breit = bas_cnt >= rb
        r_bin = np.corrcoef(rau, breit)[0, 1]
        print(f"\nRegel: rau = mind. {ru} von 3, breit = mind. {rb} von 4 -> P(rau) {rau.mean():.2f}, P(breit) {breit.mean():.2f}, r(binär) {r_bin:+.2f}")
        for nm, m in [("ruhig & breit", ~rau & breit), ("rau & breit", rau & breit), ("ruhig & schmal", ~rau & ~breit), ("rau & schmal", rau & ~breit)]:
            print(f"   {nm:15} P {m.mean():.2f} | Lücke geschlossen {Y[m, 0].mean():.2f} | Industrie hält {Y[m, 7].mean():.2f}")
print(f"\nLücke geschlossen insgesamt {Y[:, 0].mean():.2f}")
# Marker heute: Anteil erwarteter Treffer je Achse
umf_today = np.mean([P[i] if s > 0 else 1 - P[i] for i, s in UMF])
bas_today = np.mean([P[i] if s > 0 else 1 - P[i] for i, s in BAS])
print(f"Marker heute: Umfeld rau {umf_today:.2f}, Basis breit {bas_today:.2f}")
# alter Vorschlag binär
print("alter Vorschlag U2 x U1, r(binär):", round(np.corrcoef(Y[:, 1], Y[:, 0])[0, 1], 2))

# --- Vergleich und Robustheit ---
K1A = [(1, 1), (6, 1), (7, 1)]; K1B = [(3, 1), (4, 1), (5, 1), (8, 1)]
print("\nWirtschaft (U2,U7,U8) x Staatsdruck (U4,U5,U6,U9): r latent", round(corr_of(K1A, K1B)[0], 2))
base = R.copy(); rs = []
for k in range(2000):
    E = rng.uniform(-0.1, 0.1, (n, n)); E = np.triu(E, 1); E = E + E.T
    Rk = base + E
    if np.linalg.eigvalsh(Rk).min() <= 0.05: continue
    a = np.zeros(n); b = np.zeros(n)
    for i, s in UMF: a[i] = s
    for i, s in BAS: b[i] = s
    rs.append((a @ Rk @ b) / np.sqrt((a @ Rk @ a) * (b @ Rk @ b)))
rs = np.array(rs)
print(f"Robustheit (jede Paar-Korrelation zufällig ±0,1, {len(rs)} Läufe): r latent Median {np.median(rs):+.2f}, 90 % zwischen {np.quantile(rs, .05):+.2f} und {np.quantile(rs, .95):+.2f}")
