"""670 退会と転居の2つの理由で会員が抜けるとき、片方を打ち切りにした生存曲線は、退会の割合をどれだけ大きく見るのか

架空の会員 2万人。入会の時期は 0〜4年の間に散らばり、5年の時点で観察を締める（まだ残っている人は打ち切り）。
会員が抜ける理由は2つ：退会（1年あたりの起きやすさ 0.15）と転居（0〜0.30 で変える）。どちらかが起きると、もう片方は起きない。
「3年以内に退会で抜ける人の割合」を2通りで出す：
  1−Kaplan–Meier：転居で抜けた人を「打ち切り」として扱う生存曲線
  累積発生関数（Aalen–Johansen）：転居で抜けた人は、もう退会しない人として扱う
本当の値は式で出せる：h1/(h1+h2)×(1−exp(−(h1+h2)×3))。各 100 回くり返す。数字は置いた起きやすさで決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の会員の退会と転居（作成者が乱数で作成、seed 670）"
rng = np.random.default_rng(670)
N, H1, T0, REPS = 20_000, 0.15, 3.0, 100
H2S = [0.0, 0.05, 0.10, 0.20, 0.30]
GRID = np.linspace(0, 5, 101)


def simulate(h2):
    t1 = rng.exponential(1 / H1, N)
    t2 = rng.exponential(1 / h2, N) if h2 > 0 else np.full(N, np.inf)
    entry = rng.uniform(0, 4, N); c = 5 - entry
    t = np.minimum(np.minimum(t1, t2), c)
    cause = np.where(t == t1, 1, np.where(t == t2, 2, 0))
    return t, cause


def curves(t, cause):
    o = np.argsort(t); ts = t[o]; e = cause[o]
    n = len(t) - np.arange(len(t))
    km1 = np.cumprod(1 - (e == 1) / n)
    s_all = np.cumprod(1 - (e > 0) / n)
    s_prev = np.concatenate([[1.0], s_all[:-1]])
    cif1 = np.cumsum(s_prev * (e == 1) / n)
    km2 = np.cumprod(1 - (e == 2) / n)
    cif2 = np.cumsum(s_prev * (e == 2) / n)

    def at(arr, x, base):
        i = np.searchsorted(ts, x, side="right") - 1
        return np.where(i >= 0, arr[np.clip(i, 0, None)], base)
    return {"1-km1": 1 - at(km1, GRID, 1.0), "cif1": at(cif1, GRID, 0.0),
            "1-km2": 1 - at(km2, GRID, 1.0), "cif2": at(cif2, GRID, 0.0), "1-s_all": 1 - at(s_all, GRID, 1.0)}


def truth(h2, x):
    h = H1 + h2
    return H1 / h * (1 - np.exp(-h * x)), (h2 / h * (1 - np.exp(-h * x)) if h2 > 0 else 0 * x)


i3 = int(np.argmin(np.abs(GRID - T0)))
rows, curve_rows = [], []
for h2 in H2S:
    acc = {k: np.zeros(len(GRID)) for k in ["1-km1", "cif1", "1-km2", "cif2", "1-s_all"]}
    for r in range(REPS):
        t, cause = simulate(h2)
        cv = curves(t, cause)
        for k in acc: acc[k] += cv[k] / REPS
        rows.append({"h2": h2, "rep": r, "km": cv["1-km1"][i3], "cif": cv["cif1"][i3],
                     "km_plus_km2": cv["1-km1"][i3] + cv["1-km2"][i3], "all_exit": cv["1-s_all"][i3]})
    tr1, tr2 = truth(h2, GRID)
    for j, g in enumerate(GRID):
        curve_rows.append({"h2": h2, "year": round(g, 2), "true_cif1": tr1[j], **{k: acc[k][j] for k in acc}})
D = pd.DataFrame(rows); C = pd.DataFrame(curve_rows)
C.round(5).to_csv(RES / "curves.csv", index=False)
S = D.groupby("h2").agg(km=("km", "mean"), cif=("cif", "mean"), km_sd=("km", "std"), cif_sd=("cif", "std"),
                        km_plus_km2=("km_plus_km2", "mean"), all_exit=("all_exit", "mean")).reset_index()
S["true"] = [truth(h, np.array([T0]))[0][0] for h in S.h2]
S["true_km_target"] = 1 - np.exp(-H1 * T0)
S["km_over_pct"] = 100 * (S.km / S.true - 1)
S.round(5).to_csv(RES / "summary.csv", index=False)
out = {"members": N, "h_cancel": H1, "years": T0, "reps": REPS, "by_h_move": {}}
for _, s in S.iterrows():
    out["by_h_move"][str(s.h2)] = {"true_pct": round(100 * s.true, 2), "one_minus_km_pct": round(100 * s.km, 2), "cif_pct": round(100 * s.cif, 2),
                                   "km_over_pct": round(s.km_over_pct, 1), "km_cancel_plus_km_move_pct": round(100 * s.km_plus_km2, 2),
                                   "all_exit_pct": round(100 * s.all_exit, 2)}
json.dump(out, open(RES / "a670_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：転居 0.20 の曲線
fig, ax = plt.subplots(figsize=(8.5, 4.2))
q = C[C.h2 == 0.20]
ax.plot(q.year, 100 * q["1-km1"], color=ORANGE, lw=2, label="1−Kaplan–Meier（転居を打ち切り）")
ax.plot(q.year, 100 * q.cif1, color=BLUE, lw=2, label="累積発生関数")
ax.plot(q.year, 100 * q.true_cif1, color=INK, ls=":", lw=1.5, label="本当")
v1, v2 = 100 * float(q["1-km1"].iloc[i3]), 100 * float(q.cif1.iloc[i3])
ax.annotate(f"{v1:.1f}%", (T0, v1), xytext=(T0 - .55, v1 + 3), fontsize=9, color=ORANGE)
ax.annotate(f"{v2:.1f}%", (T0, v2), xytext=(T0 + .3, v2 - 4), fontsize=9, color=BLUE)
ax.set_xlabel("入会からの年数"); ax.set_ylabel("退会で抜けた割合（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("転居（1年あたり0.20）があるとき：打ち切り扱いは退会を大きく見る")
save(fig, "a670_curves.png", SRC)

# 図2：転居の起きやすさごとの3年の値
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.plot(S.h2, 100 * S.km, marker="o", color=ORANGE, label="1−Kaplan–Meier")
ax.plot(S.h2, 100 * S.cif, marker="s", color=BLUE, label="累積発生関数")
ax.plot(S.h2, 100 * S.true, ls=":", color=INK, label="本当")
for x, v, p in zip(S.h2, 100 * S.km, S.km_over_pct):
    if x > 0: ax.text(x, v + 1, f"+{p:.0f}%", ha="center", fontsize=9, color=ORANGE)
ax.set_xlabel("転居の起きやすさ（1年あたり）"); ax.set_ylabel("3年以内に退会で抜ける割合（%）"); ax.set_ylim(0, 45)
ax.legend(frameon=False, fontsize=9); ax.set_title("転居が多いほど、打ち切り扱いのずれは大きくなる")
save(fig, "a670_by_move_rate.png", SRC)

# 図3：2つの 1−KM の合計と、実際に抜けた割合
fig, ax = plt.subplots(figsize=(8.5, 4.2))
x = np.arange(len(H2S)); w = .38
ax.bar(x - w / 2, 100 * S.km_plus_km2, w, color=ORANGE, label="退会の1−KM＋転居の1−KM")
ax.bar(x + w / 2, 100 * S.all_exit, w, color=GRAY, label="実際に抜けた割合（理由を問わない）")
for xx, a, b in zip(x, 100 * S.km_plus_km2, 100 * S.all_exit):
    ax.text(xx - w / 2, a + .8, f"{a:.1f}", ha="center", fontsize=8.5); ax.text(xx + w / 2, b + .8, f"{b:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"転居 {h:.2f}" for h in H2S]); ax.set_ylabel("3年以内（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("理由別の1−KMを足すと、抜けた人より多くなる")
save(fig, "a670_sum_exceeds.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
