# 図を作る。同じデータを「正直な見せ方」と「印象が強くなる見せ方」で並べる
import pandas as pd, numpy as np, json, pathlib, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Circle
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
R = pathlib.Path(__file__).resolve().parents[1]; F = R/"figures"
ann = pd.read_csv(R/"data/annual.csv", index_col="year")
m = pd.read_csv(R/"data/monthly.csv", parse_dates=["month"])
S = json.load(open(R/"results/summary.json"))
C1, C2, GR = "#2b6cb0", "#c05621", "#888888"

# 1. 縦軸の切り取り（2×2）
fig, ax = plt.subplots(2, 2, figsize=(10, 7))
for i, (col, y0, y1, lab, scale) in enumerate([("employed_sa_10k", 2013, 2025, "就業者（万人）", 1), ("births", 2015, 2025, "出生数（万人）", 1e4)]):
    s = ann.loc[y0:y1, col] / scale
    lo, hi = s.min(), s.max(); pad = .05*(hi-lo)
    for j, (base, title) in enumerate([(0, "縦軸を0から"), (lo-pad, "縦軸を最小値の少し下から")]):
        a = ax[i, j]; a.bar(s.index, s - base, bottom=base, color=C1 if j == 0 else C2, width=.7)
        a.set_ylim(base, hi + (hi-base)*.08)
        d = s.iloc[-1]/s.iloc[0]-1; h = (s.iloc[-1]-base)/(s.iloc[0]-base)
        a.set_title(f"{lab}：{title}\nデータの変化 {d:+.1%}／最初と最後の棒の高さの比 {h:.2f}倍", fontsize=10)
fig.suptitle("同じ数字でも、縦軸の下端しだいで棒の高さの比は大きく変わる", fontsize=12)
fig.tight_layout(); fig.savefig(F/"f70_axis.png", dpi=150); plt.close()

# 2. 期間の切り取り：実質賃金
w = pd.read_csv(R/"results/r2_window10_series.csv", parse_dates=["month"])
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
mm = m.dropna(subset=["real_wage_12m"]); mm = mm[mm.month >= "1985-01-01"]
ax[0].plot(mm.month, mm.real_wage_12m, color=C1); ax[0].set_title("実質賃金指数（現金給与総額、12か月平均）", fontsize=10)
for st, c in [("2006-05-01", C2), ("1990-04-01", "#2f855a")]:
    t0 = pd.Timestamp(st); t1 = t0 + pd.DateOffset(years=10)
    sub = mm[(mm.month >= t0) & (mm.month <= t1)]; ax[0].plot(sub.month, sub.real_wage_12m, color=c, lw=3)
ax[1].plot(w.month, w.chg10*100, color=C1); ax[1].axhline(0, color=GR, lw=.8)
ax[1].set_title("「10年間の変化」を、始まりの月ごとに全部計算（%）", fontsize=10); ax[1].set_xlabel("始まりの月")
r = [x for x in S["window"] if x["N"] == 10][0]
ax[1].text(.02, .05, f"最小 {r['min']:+.1%}（{r['start_min'][:7]}始まり）\n最大 {r['max']:+.1%}（{r['start_max'][:7]}始まり）\nプラスになる始まりの月 {r['share_pos']:.0%}",
           transform=ax[1].transAxes, fontsize=9, bbox=dict(fc="white", ec="none", alpha=.8))
fig.tight_layout(); fig.savefig(F/"f70_window.png", dpi=150); plt.close()

# 3. 二軸
a = ann.loc[2000:2025]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].plot(a.index, a.births/1e4, color=C1, marker="o", ms=3); ax[0].set_ylabel("出生数（万人）", color=C1)
t = ax[0].twinx(); t.plot(a.index, a.cpi_all, color=C2, marker="o", ms=3); t.set_ylabel("消費者物価指数（2020年=100）", color=C2)
t.invert_yaxis(); t.spines["right"].set_visible(True)
ax[0].set_title("二軸：右の軸を上下逆にすると「物価と出生数が\n同じように動いている」ように見える", fontsize=10)
ax[1].scatter(a.births.diff()/1e4, a.cpi_all.diff(), color=C1)
ax[1].set_xlabel("出生数の前年差（万人）"); ax[1].set_ylabel("消費者物価の前年差")
d = S["dual"]; ax[1].set_title(f"水準の相関 {d['corr_levels']:.2f} → 前年差の相関 {d['corr_diffs']:.2f}", fontsize=10)
fig.tight_layout(); fig.savefig(F/"f70_dualaxis.png", dpi=150); plt.close()

# 4. 累積・割合と実数
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].bar(a.index, a.births/1e4, color=C1, label="毎年の出生数（万人）")
t = ax[0].twinx(); t.plot(a.index, a.births.cumsum()/1e4, color=C2, lw=2, label="2000年からの累計（万人）"); t.spines["right"].set_visible(True)
t.set_ylabel("累計（万人）", color=C2); ax[0].set_ylabel("毎年（万人）", color=C1)
ax[0].set_title("累計のグラフは、毎年が減っていても上がり続ける", fontsize=10)
b = ann.loc[2005:2015]
ax[1].plot(b.index, b.tfr/b.tfr.iloc[0]*100, color=C2, marker="o", ms=3, label="合計特殊出生率")
ax[1].plot(b.index, b.births/b.births.iloc[0]*100, color=C1, marker="o", ms=3, label="出生数")
ax[1].axhline(100, color=GR, lw=.8); ax[1].legend(frameon=False); ax[1].set_ylabel("2005年=100")
ax[1].set_title("割合（出生率）は上がり、実数（出生数）は下がった（2005→15年）", fontsize=10)
fig.tight_layout(); fig.savefig(F/"f70_cum_rate.png", dpi=150); plt.close()

# 5. 面積
v0, v1 = a.births.iloc[0], a.births.iloc[-1]; ratio = v1/v0
fig, ax = plt.subplots(1, 3, figsize=(11, 3.8))
ax[0].bar(["2000年", "2025年"], [v0/1e4, v1/1e4], color=C1); ax[0].set_title(f"棒：見た目の比 {ratio:.2f}", fontsize=10)
for k, (title, r1) in enumerate([(f"円（面積を値に比例）：見た目の比 {ratio:.2f}", np.sqrt(ratio)), (f"円（半径を値に比例）：見た目の比 {ratio**2:.2f}", ratio)], start=1):
    a2 = ax[k]; a2.add_patch(Circle((1, 1), 1, color=C1)); a2.add_patch(Circle((3.2, 1-(1-r1)), r1, color=C2))
    a2.set_xlim(-.2, 4.4); a2.set_ylim(-.2, 2.2); a2.set_aspect("equal"); a2.axis("off"); a2.set_title(title, fontsize=10)
    a2.text(1, -.15, "2000年", ha="center", fontsize=9); a2.text(3.2, -.15, "2025年", ha="center", fontsize=9)
fig.suptitle(f"出生数 2000年 {v0/1e4:.0f}万人 → 2025年 {v1/1e4:.0f}万人（{ratio-1:+.0%}）", fontsize=11)
fig.tight_layout(); fig.savefig(F/"f70_area.png", dpi=150); plt.close()

# 6. lie factor のまとめ（頑健性）
s = pd.read_csv(R/"results/r7_lie_factor_summary.csv")
s["label"] = s.case + "｜" + s.how
s = s[s.lie_factor > 0].sort_values("lie_factor")
fig, ax = plt.subplots(figsize=(10, 5.5))
ax.barh(s.label, s.lie_factor, color=[C1 if abs(x-1) < .01 else C2 for x in s.lie_factor]); ax.set_xscale("log"); ax.axvline(1, color=GR, lw=.8)
ax.set_xlabel("lie factor（図で見える変化 ÷ データの変化、1なら正直、対数目盛）"); ax.tick_params(axis="y", labelsize=8)
ax.set_title("見せ方ごとの「誇張の大きさ」", fontsize=11)
fig.tight_layout(); fig.savefig(F/"f70_lie_factor.png", dpi=150); plt.close()
print("ok")
