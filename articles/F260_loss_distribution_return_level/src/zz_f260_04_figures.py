"""04 図：figures/ に PNG を6枚（図6は 05 の問い直しのあとに描く）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from zz_f260_common import ROOT, P, R, MODELS, isf, sf

F = ROOT / "figures"; F.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f or "NotoSansCJKjp-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "savefig.dpi": 160})
C = dict(zip(MODELS, ["#2a78d6", "#1baf7a", "#eda100", "#e87ba4", "#eb6834"]))
INK2 = "#52514e"
S = json.load(open(R / "summary.json"))
A = pd.read_csv(P / "dataset_A.csv"); A = A[A.deflator == "defl_house"].sort_values("loss_2025_oku", ascending=False).reset_index(drop=True)
B = pd.read_csv(P / "dataset_B.csv"); B = B[B.deflator == "defl_house"].sort_values("loss_2025_oku", ascending=False).reset_index(drop=True)
fits = pd.read_csv(R / "fits_all_cases.csv")
rob = pd.read_csv(R / "robustness.csv")
bt = pd.read_csv(R / "bootstrap_rl100_base.csv")
U, LAM = S["u_base"], S["lam_base"]
def save(fig, name): fig.savefig(F / name, bbox_inches="tight"); plt.close(fig)
def man(v): return f"{v/1e4:.1f}兆" if v >= 1e4 else f"{v:,.0f}億"
from matplotlib.ticker import FuncFormatter, FixedLocator
def okuyen(v, _=None): return (f"{v/1e4:,.0f}兆" if v >= 1e4 else f"{v:,.0f}億") if v > 0 else ""
YEN = FuncFormatter(okuyen)
def par(case, m): return json.loads(fits[(fits.case == case) & (fits.model == m)].par.iloc[0])
BASE = fits.case.iloc[0]
CASE_B = [c for c in fits.case.unique() if c.startswith("B：")][0]

# 図1 データ：事故ごとの損害（2025年度の建設費・住宅数に直した額）
fig, ax = plt.subplots(figsize=(10, 5.4))
yrs = A.event_ym.str[:4].astype(int) + (A.event_ym.str[5:7].astype(int) - .5) / 12
ax.scatter(yrs, A.loss_2025_oku, s=36, color=C["指数"], label="協会が個別に調べた35事故（2012〜2025年度）", zorder=3)
old = B[B.fy < 2012]; yo = old.event_ym.str[:4].astype(int) + (old.event_ym.str[5:7].astype(int) - .5) / 12
ax.scatter(yo, old.loss_2025_oku, s=48, color=C["GPD"], marker="D", label="上位10表の2011年度以前の大事故（1991・1999・2004年）", zorder=3)
ax.set_yscale("log")
for u, lab in [(300, "300億円（26件）"), (650, "650億円（15件、基準）"), (1300, "1,300億円（10件）")]:
    ax.axhline(u, color=INK2, lw=.8, ls=":"); ax.text(1990.6, u * 1.07, lab, fontsize=9, color=INK2)
ax.axhline(S["uB"], color=C["GPD"], lw=1, ls="--"); ax.text(1990.6, S["uB"] * 1.07, f"取りこぼしのない足切り {S['uB']:,.0f}億円（35年で8件）", fontsize=9, color=C["GPD"])
for _, r in pd.concat([A.head(3), old]).iterrows():
    t = int(r.event_ym[:4]) + (int(r.event_ym[5:7]) - .5) / 12
    ax.annotate(f"{r['name'].split('（')[0]}  {r.loss_2025_oku:,.0f}億円", (t, r.loss_2025_oku), xytext=(6, -12 if r.fy == 1999 else 4), textcoords="offset points", fontsize=8.5, color=INK2)
ax.set_xlim(1990, 2027); ax.set_ylim(15, 30000); ax.yaxis.set_major_formatter(YEN)
ax.set_ylabel("損害（億円、2025年度の建設費・住宅数に直した額）")
ax.set_title("1事故の損害：2025年の物価と住宅の数なら、いくらになるか", loc="left", fontsize=12.5)
ax.legend(loc="lower right", fontsize=9, frameon=False)
save(fig, "fig1_events_2025scale.png")

# 図2 再現期間のグラフ：観測は同じように合うが、100年より先で分かれる
fig, ax = plt.subplots(figsize=(10, 5.8))
x = A.loss_2025_oku.values; x = x[x > U]; n = len(x)
emp_T = 14 / (np.arange(1, n + 1) - 0.4) * (n + 0.2) / n  # 再現期間の目安（グリンゴルテン型の位置）
emp_T = 1 / (LAM * (np.arange(1, n + 1) - .44) / (n + .12))
ax.scatter(emp_T, np.sort(x)[::-1], color="#0b0b0b", s=30, zorder=5, label="実際の15事故（u=650億円超）")
T = np.logspace(np.log10(1 / LAM * 1.001), np.log10(500), 200)
for m in MODELS:
    p = par(BASE, m); y = isf(m, p, U, 1 / (T * LAM))
    d = fits[(fits.case == BASE) & (fits.model == m)].iloc[0]
    ax.plot(T, y, color=C[m], lw=2, label=f"{m}（ΔAIC {d.daic:.1f}）")
    ax.annotate(man(d.rl100), (100, d.rl100), xytext=((8, -4) if m == "対数正規" else (-46, 8 if m == "GPD" else 4)), textcoords="offset points", fontsize=8.5, color=C[m])
ax.axvline(14, color=INK2, lw=.8, ls=":"); ax.text(14 * 1.05, 600, "記録は14年", fontsize=9, color=INK2)
ax.axvline(100, color=INK2, lw=.8, ls="--"); ax.text(105, 600, "100年に1度", fontsize=9, color=INK2)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(.8, 520); ax.set_ylim(500, 1.2e6)
ax.xaxis.set_major_locator(FixedLocator([1, 2, 5, 10, 20, 50, 100, 200, 500])); ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}")); ax.yaxis.set_major_formatter(YEN)
ax.set_xlabel("再現期間（年）：この額以上の事故が平均して何年に1回起きるか"); ax.set_ylabel("1事故の損害（2025年度換算）")
ax.set_title("5つの分布は記録の範囲ではほぼ同じように合い、その先で大きく分かれる", loc="left", fontsize=12.5)
ax.legend(loc="upper left", fontsize=9, frameon=False)
save(fig, "fig2_return_level_curves.png")

# 図3 100年・200年に1度の額と年間合計の99.5%点（基準ケース）
b = fits[fits.case == BASE].set_index("model").loc[MODELS]
fig, ax = plt.subplots(figsize=(10, 4.8))
yy = np.arange(len(MODELS))[::-1]
for i, (m, k, lab, mk) in enumerate([(None, "rl100", "100年に1度（1事故）", "o"), (None, "rl200", "200年に1度（1事故）", "s"), (None, "agg995", "年間合計の99.5%点", "^")]):
    ax.scatter(b[k], yy + (1 - i) * .22, marker=mk, s=50, color=["#2a78d6", "#eb6834", "#52514e"][i], label=lab, zorder=3)
for j, m in enumerate(MODELS):
    ax.text(b.loc[m, "rl100"], yy[j] + .22 + .12, man(b.loc[m, "rl100"]), fontsize=8.5, color="#2a78d6", ha="center")
ax.axvline(S["largest"], color=INK2, lw=.8, ls=":"); ax.text(S["largest"] * 1.04, -0.45, f"14年間の最大 {S['largest']:,.0f}億円", fontsize=9, color=INK2)
ax.set_xscale("log"); ax.set_yticks(yy, [f"{m}\nΔAIC {b.loc[m,'daic']:.1f}" for m in MODELS])
ax.set_xlabel("円（2025年度換算、対数目盛）"); ax.set_xlim(8000, 8e5); ax.xaxis.set_major_formatter(YEN); ax.set_ylim(-0.7, 4.6)
ax.set_title(f"100年に1度の額：最小 {man(b.rl100.min())}円 〜 最大 {man(b.rl100.max())}円（{b.rl100.max()/b.rl100.min():.1f}倍）", loc="left", fontsize=12.5)
ax.legend(loc="lower right", fontsize=9, frameon=False)
save(fig, "fig3_rl100_by_model.png")

# 図4 ブートストラップ：同じ分布でも、記録の取り方しだいでどれだけ動くか
fig, ax = plt.subplots(figsize=(10, 4.6))
for j, m in enumerate(MODELS):
    v = bt[m].dropna().values; lo, med, hi = np.quantile(v, [.05, .5, .95])
    ax.plot([lo, hi], [yy[j]] * 2, color=C[m], lw=5, solid_capstyle="round", alpha=.85)
    ax.scatter([med], [yy[j]], color="white", edgecolor=C[m], s=40, zorder=4, lw=1.5)
    ax.scatter([b.loc[m, "rl100"]], [yy[j]], color="#0b0b0b", marker="|", s=200, zorder=5)
    ax.text(hi * 1.08, yy[j], f"{man(lo)}〜{man(hi)}（{hi/lo:.1f}倍）", va="center", fontsize=9, color=INK2)
ax.set_xscale("log"); ax.set_yticks(yy, MODELS); ax.set_xlim(3000, 5e6); ax.xaxis.set_major_formatter(YEN)
ax.set_xlabel("100年に1度の額（円、対数目盛）。帯＝90%区間、○＝中央値、｜＝元の記録での値")
ax.set_title("同じ分布でも、14年の記録のゆらぎで100年に1度の額は何倍も動く（2,000回）", loc="left", fontsize=12.5)
save(fig, "fig4_bootstrap_intervals.png")

# 図5 頑健性：ケースごとの100年に1度の額（5分布）
cases = list(rob.case)
short = {c: c.split(" u=")[0].replace("基準：A（2012〜2025年度、14年）", "基準（A、14年）").replace("B：取りこぼしのない大事故（1991〜2025年度、35年）", "B（35年、大事故だけ）").replace("（約25件）", "").replace("（約10件）", "").replace("しきい値小", "しきい値を下げる").replace("しきい値大", "しきい値を上げる") for c in cases}
fig, ax = plt.subplots(figsize=(10, 6.2))
yc = np.arange(len(cases))[::-1]
for j, c in enumerate(cases):
    r = rob.iloc[j]
    vals = [r[f"rl100_{m}"] for m in MODELS]
    ax.plot([min(vals), max(vals)], [yc[j]] * 2, color="#c9c8c2", lw=1.2, zorder=1)
    for m in MODELS:
        ax.scatter(r[f"rl100_{m}"], yc[j], color=C[m], s=60 if m == r.best else 30, edgecolor="#0b0b0b" if m == r.best else "none", zorder=3, label=m if j == 0 else None)
    ax.text(1.3e6, yc[j], f"{r.ratio:.1f}倍", va="center", fontsize=9, color=INK2, ha="right")
ax.set_xscale("log"); ax.set_yticks(yc, [f"{short[c]}（{int(n)}件）" for c, n in zip(cases, rob.n)]); ax.set_xlim(5000, 1.4e6); ax.xaxis.set_major_formatter(YEN)
ax.set_xlabel("100年に1度の額（円、対数目盛）。黒い縁＝AIC最良、右端＝最大÷最小")
ax.set_title("u=650億円前後で当てはめると5〜38倍の開き。大きな事故だけで当てはめると2倍前後", loc="left", fontsize=12.5)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], marker="o", ls="", color=C[m], label=m) for m in MODELS], loc="lower left", fontsize=9, frameon=False, ncol=5, bbox_to_anchor=(0, -0.2))
save(fig, "fig5_robustness.png")
# 図6 問い直し：記録が何年あれば絞れるか（05 の結果）
rq = pd.read_csv(R / "reask_summary.csv")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
for ax, t in zip(axs, ["対数正規", "GPD"]):
    g = rq[rq.truth == t].sort_values("years"); tr = g.true_rl100.iloc[0]
    for k, col, lab, dx in [("same", C[t], "形を知っていて同じ分布で当てはめ", -0.035), ("aic", "#52514e", "5つから AIC 最良を選ぶ", 0.035)]:
        xs = np.log10(g.years) + dx
        ax.vlines(xs, g[f"{k}_lo"] / tr, g[f"{k}_hi"] / tr, color=col, lw=4, alpha=.85, label=lab)
        ax.scatter(xs, g[f"{k}_med"] / tr, color="white", edgecolor=col, zorder=4, s=30)
        for xx, lo, hi in zip(xs, g[f"{k}_lo"] / tr, g[f"{k}_hi"] / tr):
            ax.text(xx + (0.02 if dx > 0 else -0.02), hi * 1.08, f"{hi/lo:.1f}倍", fontsize=8.5, color=col, ha="left" if dx > 0 else "right")
    ax.axhline(1, color="#0b0b0b", lw=.8)
    ax.set_xticks(np.log10(g.years), [f"{y}年" for y in g.years]); ax.set_yscale("log"); ax.set_ylim(0.15, 15)
    ax.yaxis.set_major_locator(FixedLocator([0.2, 0.5, 1, 2, 5, 10])); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}倍"))
    ax.set_title(f"本当の分布が{t}（100年に1度 {man(tr)}円）", loc="left", fontsize=11.5)
    ax.set_xlabel("記録の長さ（年1.07件の割合で事故が起きる）")
axs[0].set_ylabel("推定した100年に1度 ÷ 本当の値（90%の範囲）"); axs[1].legend(loc="lower right", fontsize=9, frameon=False)
fig.suptitle("記録が長くなれば幅は縮むが、140年あっても分布を選ぶ段階で幅が残る（300回ずつ）", x=0.01, ha="left", fontsize=12.5)
save(fig, "fig6_reask_record_length.png")
print("figs ok")
