"""727 「有意な差がない」ことを「同じ」と読むと、本当は差のある案を何%で同じとしてしまうのか

架空の2案（A・B）の1人あたりの購入額（円）。ばらつき（標準偏差）は1,000円。
本当の差 d＝0・100・200・300・500円、1案あたりの人数 n＝30・100・300・1,000人。
「同じとみなしてよい差」（同等の幅）は ±200円と、作成者が先に決める。
判定の2通り：
  ふつうの検定：t 検定で p≥0.05（有意な差がない）なら「同じ」
  同等性の検定（TOST）：差の90%区間が ±200円の中に入れば「同じ」（片側5%の検定を2回）
各組み合わせ 4,000回くり返し、「同じ」と判定した割合を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の2案の購入額（作成者が乱数で作成、seed 727）"
rng = np.random.default_rng(727)
SD, MARGIN, REPS = 1000.0, 200.0, 4000
DS, NS = [0, 100, 200, 300, 500], [30, 100, 300, 1000]


def sim(d, n, reps=REPS):
    a = rng.normal(5000, SD, (reps, n)); b = rng.normal(5000 + d, SD, (reps, n))
    diff = b.mean(1) - a.mean(1)
    sp = np.sqrt((a.var(1, ddof=1) + b.var(1, ddof=1)) / 2); se = sp * np.sqrt(2 / n); df = 2 * n - 2
    p = 2 * stats.t.sf(np.abs(diff / se), df)
    tq = stats.t.ppf(0.95, df)
    lo, hi = diff - tq * se, diff + tq * se
    return diff, se, p >= 0.05, (lo > -MARGIN) & (hi < MARGIN), lo, hi


rows = []
for d in DS:
    for n in NS:
        diff, se, same_plain, same_tost, *_ = sim(d, n)
        rows.append({"true_diff": d, "n": n, "same_plain_pct": same_plain.mean() * 100, "same_tost_pct": same_tost.mean() * 100})
S = pd.DataFrame(rows); S.round(2).to_csv(RES / "summary.csv", index=False)
g = lambda d, n, c: round(float(S[(S.true_diff == d) & (S.n == n)][c].iloc[0]), 1)

out = {"sd": SD, "margin": MARGIN, "reps": REPS,
       "same_pct": {f"d{d}_n{n}": {"plain": g(d, n, "same_plain_pct"), "tost": g(d, n, "same_tost_pct")} for d in DS for n in NS}}
json.dump(out, open(RES / "a727_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：本当の差ごとの「同じ」の割合（n＝30 と 1,000）
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, n in zip(axes, [30, 1000]):
    s = S[S.n == n]
    ax.plot(s.true_diff, s.same_plain_pct, marker="o", color=ORANGE, label="有意な差がない（p≥0.05）")
    ax.plot(s.true_diff, s.same_tost_pct, marker="o", color=BLUE, label="同等性の検定（TOST、±200円）")
    for r in s.itertuples():
        up = r.same_plain_pct >= r.same_tost_pct
        ax.text(r.true_diff + 12, r.same_plain_pct + (3 if up else -7), f"{r.same_plain_pct:.0f}", color=ORANGE, ha="left", fontsize=8)
        ax.text(r.true_diff + 12, r.same_tost_pct + (-7 if up else 3), f"{r.same_tost_pct:.0f}", color=BLUE, ha="left", fontsize=8)
    ax.axvspan(-20, MARGIN, color=LIGHT, alpha=0.3, lw=0); ax.set_xlim(-20, 520); ax.set_ylim(-10, 105)
    ax.set_xlabel("本当の差（円）"); ax.set_title(f"1案 {n:,}人")
axes[0].set_ylabel("「同じ」と判定した割合（%）"); axes[0].legend(frameon=False, fontsize=8.5, loc="center right")
fig.suptitle("1案30人では、差が500円あっても半分が「有意な差がない」（色の帯は ±200円の中）", y=1.02)
save(fig, "a727_by_diff.png", SRC)

# 図2：人数ごと（差300円と差0円）
fig, ax = plt.subplots(figsize=(8, 3.8)); xs = [str(n) for n in NS]
for d, ls in [(300, "-"), (0, "--")]:
    s = S[S.true_diff == d]
    ax.plot(xs, s.same_plain_pct, ls=ls, marker="o", color=ORANGE, label=f"有意な差がない（本当の差 {d}円）")
    ax.plot(xs, s.same_tost_pct, ls=ls, marker="o", color=BLUE, label=f"TOST（本当の差 {d}円）")
ax.set_xlabel("1案あたりの人数"); ax.set_ylabel("「同じ」と判定した割合（%）"); ax.legend(frameon=False, fontsize=8, ncol=2)
ax.set_ylim(-5, 110)
ax.set_title("ふつうの検定は人数が少ないほど「同じ」と言う。TOST は人数が多いほど「同じ」を示せる")
save(fig, "a727_by_n.png", SRC)

# 図3：区間の例（本当の差300円、n＝100、20回）
diff, se, sp_, st_, lo, hi = sim(300, 100, reps=20)
lo95 = diff - stats.t.ppf(0.975, 198) * se; hi95 = diff + stats.t.ppf(0.975, 198) * se
fig, ax = plt.subplots(figsize=(8, 4)); y = np.arange(20)
for i in y:
    col = ORANGE if (lo95[i] < 0 < hi95[i]) else GRAY
    ax.plot([lo95[i], hi95[i]], [i, i], color=col, lw=2); ax.plot(diff[i], i, "o", color=col, ms=4)
ax.axvline(0, color=INK, lw=0.8); ax.axvline(300, color=GREEN, lw=1, ls="--")
ax.axvspan(-MARGIN, MARGIN, color=LIGHT, alpha=0.35, lw=0)
ax.set_yticks([]); ax.set_xlabel("B−A の差と95%区間（円）")
ax.set_title(f"本当の差300円・1案100人：20回中{int((lo95 < 0).__and__(hi95 > 0).sum())}回で区間が0をまたぐ（オレンジ）")
ax.set_ylim(-2, 19.7); ax.text(300, -1.5, "本当の差", color=GREEN, ha="center", fontsize=8.5); ax.text(0, -1.5, "±200円の帯", color=BLUE, ha="center", fontsize=8.5)
save(fig, "a727_intervals.png", SRC)
print(json.dumps(out, ensure_ascii=False))
