"""図6枚"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

C1, C2, C3, CG = "#2a6f97", "#e07a2f", "#7a9e3b", "#9a9a9a"
S = pd.read_csv(RES / "news_noise_tests.csv")
P = pd.read_csv(RES / "predictability_oos.csv")
R = pd.read_csv(RES / "robustness.csv")
K = pd.read_csv(RES / "maikin_prelim_final.csv")
K["r"] = K.f - K.p
ORDER_G = ["GDP", "民間消費", "住宅投資", "設備投資", "政府消費", "公共投資", "輸出", "輸入"]

# 図1 GDP：段階ごとの改定の大きさ（ノイズ比＝改定の標準偏差÷確定値の標準偏差）
g = S[S.統計 == "GDP"].pivot(index="系列", columns="段階", values="ノイズ比").reindex(ORDER_G)
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(len(g))
for i, (st, c) in enumerate([("1次→2次", C3), ("1次→1年後", C1), ("1次→最新", C2)]):
    ax.bar(x + (i - 1) * 0.27, g[st], 0.27, color=c, label=st)
ax.set_xticks(x, g.index)
ax.set_ylabel("改定のばらつき ÷ 確定値のばらつき")
ax.axhline(0.5, color=CG, lw=0.8, ls="--")
ax.set_title("GDP の需要項目：1次速報からの改定は、項目と段階でどれだけ大きいか（実質・前期比）", fontsize=11)
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig1_gdp_noise_ratio.png", dpi=150); plt.close(fig)

# 図2 ニュースかノイズか：corr(改定, 速報) と corr(改定, 確定値)
b = pd.concat([S[(S.統計 == "GDP") & (S.段階 == "1次→1年後")], S[S.統計 == "毎月勤労統計"]])
fig, ax = plt.subplots(figsize=(8, 6.4))
for stat, c, mk in [("GDP", C1, "o"), ("毎月勤労統計", C2, "s")]:
    d = b[b.統計 == stat]
    ax.scatter(d["corr(r,p)"], d["corr(r,f)"], s=60, color=c, marker=mk, label=stat + ("（1次→1年後）" if stat == "GDP" else "（速報→確報）"), zorder=3)
    for _, r in d.iterrows():
        ax.annotate(r.系列, (r["corr(r,p)"], r["corr(r,f)"]), xytext=(4, 4), textcoords="offset points", fontsize=9)
ax.axhline(0, color=CG, lw=0.8); ax.axvline(0, color=CG, lw=0.8)
fig.text(0.5, 0.01, "上にあるほど、改定は速報のあとに入った情報（ニュース）。左にあるほど、改定は速報の振れすぎ（ノイズ）を戻している", ha="center", fontsize=8.5, color="#444444")
ax.set_xlabel("改定と速報の相関（マイナスほどノイズ型）")
ax.set_ylabel("改定と確定値の相関（プラスほどニュース型）")
ax.set_title("速報の直され方は「ニュース型」か「ノイズ型」か", fontsize=12)
ax.legend(frameon=False, loc="upper right")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig2_news_noise_map.png", dpi=150); plt.close(fig)

# 図3 毎勤：所定内給与と給与総額の前年比の改定（確報−速報）の推移
fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
for ax, it, c in zip(axes, ["所定内給与", "給与総額"], [C1, C2]):
    d = K[K.系列 == it].copy()
    d["t"] = pd.PeriodIndex(d.月, freq="M").to_timestamp()
    ax.bar(d.t, d.r, width=25, color=np.where(d.r < 0, c, CG))
    roll = d.set_index("t").r.rolling(12).mean()
    ax.plot(roll.index, roll.values, color="black", lw=1.2, label="12か月の平均")
    ax.axhline(0, color=CG, lw=0.8)
    ax.set_ylabel("ポイント")
    ax.set_title(f"{it}の前年比：確報 − 速報（平均 {d.r.mean():+.2f}、下に直された月 {(d.r < 0).mean():.0%}）", fontsize=10.5, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(frameon=False, loc="upper right")
fig.suptitle("毎月勤労統計：確報で前年比はどう直されたか（事業所規模5人以上・調査産業計）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig3_maikin_revisions.png", dpi=150); plt.close(fig)

# 図4 特別給与：月別の改定の大きさ
d = K[K.系列 == "特別給与"].copy()
d["月番号"] = d.月.str[5:].astype(int)
m = d.groupby("月番号").r.apply(lambda x: x.abs().mean())
fig, ax = plt.subplots(figsize=(9, 4.2))
cols = [C2 if k in (6, 7, 12) else C1 for k in m.index]
ax.bar(m.index, m.values, color=cols)
ax.set_xticks(range(1, 13), [f"{k}月" for k in range(1, 13)])
ax.set_ylabel("前年比の改定の平均絶対（ポイント）")
ax.set_title("特別給与（賞与など）の前年比は、賞与の月（橙）より、それ以外の月で大きく直される", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig4_bonus_by_month.png", dpi=150); plt.close(fig)

# 図5 改定を予測できるか（拡大窓の予測で、改定0とした場合との二乗誤差の比）
p = P[P.段階.isin(["1次→1年後", "速報→確報"])].copy()
p["名"] = np.where(p.統計 == "GDP", "GDP：" + p.系列, "毎勤：" + p.系列)
p = p.sort_values("RMSE比（モデル/改定0）")
fig, ax = plt.subplots(figsize=(8.5, 6))
cc = [C1 if s == "GDP" else C2 for s in p.統計]
ax.barh(p.名, p["RMSE比（モデル/改定0）"], color=cc)
ax.axvline(1, color="black", lw=1)
for i, (_, r) in enumerate(p.iterrows()):
    if r["DMのp（片側）"] < 0.05:
        ax.text(r["RMSE比（モデル/改定0）"] + 0.005, i, "＊", va="center", fontsize=10)
ax.set_xlim(0.8, 1.2)
ax.set_xlabel("予測誤差の比（1より小さいほど、速報から改定を前もって当てられる）")
ax.set_title("速報の値から改定を当てられるか（拡大窓・1期ずつ先を予測、＊は5%で有意）", fontsize=11)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig5_predictability.png", dpi=150); plt.close(fig)

# 図6 頑健性：r~p の傾き（マイナスほどノイズ型）を設定ごとに
sel = [("GDP", "GDP"), ("GDP", "設備投資"), ("GDP", "政府消費"), ("毎月勤労統計", "給与総額"), ("毎月勤労統計", "特別給与"), ("毎月勤労統計", "所定内給与")]
fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
for ax, (stat, it) in zip(axes.ravel(), sel):
    d = R[(R.統計 == stat) & (R.系列 == it)].iloc[::-1]
    col = [C2 if q < 0.05 else CG for q in d["r~p のp"]]
    ax.barh(range(len(d)), d["r~p の傾き"], color=col)
    ax.set_yticks(range(len(d)), [s.replace("（", "\n（") if len(s) > 14 else s for s in d.設定], fontsize=7.5)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(f"{'GDP' if stat == 'GDP' else '毎勤'}：{it}", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("改定を速報で回帰した傾き（橙は5%で0と区別できる＝ノイズ型の証拠）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig6_robustness.png", dpi=150); plt.close(fig)
print("ok")
