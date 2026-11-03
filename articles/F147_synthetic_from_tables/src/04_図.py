"""図を作る。入力: results/method_comparison.csv, results/coefficients_main.csv  出力: figures/*.png"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(f).exists():
        fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
res = pd.read_csv(ROOT / "results" / "method_comparison.csv")
coef = pd.read_csv(ROOT / "results" / "coefficients_main.csv")
MAIN = "主（2022・所得6区分）"
m = res[res.tag == MAIN].set_index("method")
METH = ["S0 独立", "S1 BN（木）", "S2 IPF 副業の星形", "S3 IPF 2変数すべて", "S4 BN（親2つ）", "S5 IPF 2変数＋副業を含む3変数", "S6 IPF 3変数すべて"]
SHORT = {"S0 独立": "独立\n(1変数×6)", "S1 BN（木）": "BN・木\n(2変数×5)", "S2 IPF 副業の星形": "副業の星形\n(2変数×6)",
         "S3 IPF 2変数すべて": "2変数すべて\n(15枚)", "S4 BN（親2つ）": "BN・親2つ\n(3変数×5)",
         "S5 IPF 2変数＋副業を含む3変数": "2変数＋副業の\n3変数(25枚)", "S6 IPF 3変数すべて": "3変数すべて\n(20枚)"}
C_M = "#2b6cb0"; C_T = "#c05621"; C_G = "#718096"

# 図1 使う表の大きさと、同時分布の再現（TVD）
fig, ax = plt.subplots(figsize=(8, 5))
OFF = {"S3 IPF 2変数すべて": (-40, 12), "S4 BN（親2つ）": (-20, -22), "S5 IPF 2変数＋副業を含む3変数": (-30, 14)}
for k in METH:
    r = m.loc[k]
    ax.scatter(r.n_cells, r.tvd, s=70, color=C_M, zorder=3)
    ax.annotate(SHORT[k].replace("\n", " "), (r.n_cells, r.tvd), textcoords="offset points", xytext=OFF.get(k, (6, 4)), fontsize=8.5)
ceil = m.loc["本当の表から引き直し"]
ax.axhline(ceil.tvd, color=C_T, ls="--", lw=1.2)
ax.text(22, ceil.tvd + 0.008, f"本当の表から同じ件数を引き直したときのずれ（{ceil.tvd:.3f}）", color=C_T, fontsize=8.5)
ax.set_xscale("log"); ax.set_xlabel("合成に使った表のセルの合計（対数）"); ax.set_ylabel("6変数の同時分布とのずれ（全変動距離）")
ax.set_title("使う表が大きいほど、6変数の組み合わせの再現は近づく", fontsize=12)
ax.set_ylim(0, 0.56); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "fig1_tables_vs_tvd.png", dpi=150); plt.close(fig)

# 図2 オッズ比の再現（主な項目）
TERMS = [("C(sex, Treatment('男'))[T.女]", "女性"), ("C(age, Treatment('35〜44歳'))[T.65〜74歳]", "65〜74歳"),
         ("C(age, Treatment('35〜44歳'))[T.75歳以上]", "75歳以上"), ("C(emp, Treatment('正規'))[T.非正規]", "非正規"),
         ("C(emp, Treatment('正規'))[T.役員]", "役員"), ("C(emp, Treatment('正規'))[T.自営業主など]", "自営業主など"),
         ("C(inc, Treatment('4_300〜499万円'))[T.1_100万円未満]", "所得100万円未満"),
         ("C(inc, Treatment('4_300〜499万円'))[T.6_700万円以上]", "所得700万円以上")]
SHOW = ["本当の表", "S1 BN（木）", "S2 IPF 副業の星形", "S3 IPF 2変数すべて", "S6 IPF 3変数すべて"]
COL = {"本当の表": "black", "S1 BN（木）": "#d69e2e", "S2 IPF 副業の星形": "#e53e3e", "S3 IPF 2変数すべて": "#3182ce", "S6 IPF 3変数すべて": "#38a169"}
LAB = {"本当の表": "本当の表", "S1 BN（木）": "BN・木", "S2 IPF 副業の星形": "副業の星形", "S3 IPF 2変数すべて": "2変数すべて", "S6 IPF 3変数すべて": "3変数すべて"}
fig, ax = plt.subplots(figsize=(8, 5.6))
for j, meth in enumerate(SHOW):
    for i, (t, lab) in enumerate(TERMS):
        r = coef[(coef.method == meth) & (coef.term == t)]
        if r.empty: continue
        y = i + (j - 2) * 0.15
        ax.plot([np.exp(r.lo.iloc[0]), np.exp(r.hi.iloc[0])], [y, y], color=COL[meth], lw=1.2)
        ax.scatter(np.exp(r.est.iloc[0]), y, color=COL[meth], s=22, zorder=3, label=LAB[meth] if i == 0 else None)
ax.axvline(1, color=C_G, lw=0.8)
ax.set_yticks(range(len(TERMS))); ax.set_yticklabels([l for _, l in TERMS]); ax.invert_yaxis()
ax.set_xscale("log"); ax.set_xlabel("副業のオッズ比（他の属性をそろえたもの、対数目盛。正規・男性・35〜44歳・300〜499万円と比べる）")
ax.set_title("2変数の表をすべて使えば、オッズ比はほぼ元どおりになった", fontsize=12)
ax.legend(fontsize=8.5, loc="lower right"); ax.grid(alpha=0.3, axis="x")
fig.tight_layout(); fig.savefig(FIG / "fig2_odds_ratios.png", dpi=150); plt.close(fig)

# 図3 「雇用形態だけで何割を説明できるか」（逸脱度の説明割合）
fig, ax = plt.subplots(figsize=(8.5, 4.8))
order = METH + ["本当の表から引き直し", "本当の表"]
vals = [m.loc[k].dev_emp for k in order]
cols = [C_M] * len(METH) + [C_G, "black"]
ax.bar(range(len(order)), vals, color=cols)
for i, v in enumerate(vals):
    ax.text(i, v + 0.01, f"{v:.0%}", ha="center", fontsize=8.5)
ax.axhline(m.loc["本当の表"].dev_emp, color="black", ls=":", lw=1)
ax.set_xticks(range(len(order)))
ax.set_xticklabels([SHORT.get(k, k.replace("本当の表から引き直し", "本当の表から\n引き直し")) for k in order], fontsize=7.8)
ax.set_ylabel("雇用形態だけで説明できた割合（逸脱度）"); ax.set_ylim(0, 1.08)
ax.set_title("合成の方法しだいで、「雇用形態で7割」は0%にも96%にもなった", fontsize=12)
ax.grid(alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(FIG / "fig3_deviance_emp.png", dpi=150); plt.close(fig)

# 図4 女性の粗いオッズ比と調整後オッズ比
fig, ax = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(len(order)); w = 0.38
cr = [m.loc[k].crude_f for k in order]; ad = [m.loc[k].adj_f for k in order]
ax.bar(x - w / 2, cr, w, color="#a0aec0", label="そのまま比べる（粗いオッズ比）")
ax.bar(x + w / 2, ad, w, color=C_M, label="雇用形態・所得・年齢をそろえる（調整後）")
ax.axhline(1, color="black", lw=0.8)
for i in range(len(order)):
    ax.text(i + w / 2, ad[i] + 0.01, f"{ad[i]:.2f}", ha="center", fontsize=7.8)
ax.set_xticks(x); ax.set_xticklabels([SHORT.get(k, k.replace("本当の表から引き直し", "本当の表から\n引き直し")) for k in order], fontsize=7.8)
ax.set_ylabel("女性の副業のオッズ比（男性＝1）"); ax.set_ylim(0.7, 1.35)
ax.set_title("「女性に多いのは雇用形態と所得のため」を再現できたのは、属性どうしの表を使った方法だけ", fontsize=11)
ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(FIG / "fig4_female_or.png", dpi=150); plt.close(fig)

# 図5 頑健性：条件ごとのオッズ比のずれ
tags = list(dict.fromkeys(res.tag))
rows = METH + ["本当の表から引き直し"]
M = np.array([[res[(res.tag == t) & (res.method == k)].mean_abs_logOR.values[0] for t in tags] for k in rows])
fig, ax = plt.subplots(figsize=(9, 4.8))
im = ax.imshow(M, cmap="Oranges", vmin=0, vmax=0.4, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, f"{M[i, j]:.3f}", ha="center", va="center", fontsize=8, color="black" if M[i, j] < 0.25 else "white")
ax.set_yticks(range(len(rows))); ax.set_yticklabels([SHORT.get(k, k).replace("\n", " ") for k in rows], fontsize=8)
WR = {"BN の構造を AIC で選ぶ": "BN の構造を\nAIC で選ぶ", "周辺表を1千人単位に丸める": "周辺表を\n1千人単位に丸める"}
ax.set_xticks(range(len(tags))); ax.set_xticklabels([WR.get(t, t.replace("（", "\n（")) for t in tags], fontsize=7.8)
ax.set_title("オッズ比のずれ（対数の平均絶対差）：どの条件でも「2変数すべて」以上で引き直しのぶれ並み", fontsize=10.5)
fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout(); fig.savefig(FIG / "fig5_robustness.png", dpi=150); plt.close(fig)
# 図6 正規の人の副業の割合は、年齢とともに増えるか（年齢×雇用形態×副業の3変数の関係）
import importlib.util
spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_分析.py"); A = importlib.util.module_from_spec(spec)
import sys; sys.argv = ["x"]; spec.loader.exec_module(A)
Pc, levels = A.true_table(2022); P = Pc / Pc.sum(); N = int(round(Pc.sum() / 100))
meths, _ = A.methods(P, N)
fig, axs = plt.subplots(1, 2, figsize=(9, 4.2), sharey=True)
SH = [("本当の表", P, "black", "-"), ("2変数すべて", meths["S3 IPF 2変数すべて"][0], "#3182ce", "--"),
      ("2変数＋副業の3変数", meths["S5 IPF 2変数＋副業を含む3変数"][0], "#d69e2e", "-."), ("3変数すべて", meths["S6 IPF 3変数すべて"][0], "#38a169", ":")]
for ax, emp in zip(axs, ["正規", "非正規"]):
    for lab, Q, c, ls in SH:
        d = A.to_long(Q, levels); g = A.wide(d[d.emp == emp], ["age"])
        ax.plot(range(len(g)), g.p * 100, marker="o", color=c, ls=ls, label=lab)
    ax.set_xticks(range(len(g))); ax.set_xticklabels([a.replace("歳", "") for a in g.age], fontsize=8, rotation=30)
    ax.set_title(emp, fontsize=11); ax.grid(alpha=0.3)
axs[0].set_ylabel("副業がある人の割合（%）"); axs[1].legend(fontsize=8.5)
fig.suptitle("「年齢とともに副業が増えるのは正規だけ」は、副業を含む3変数の表がないと消えた", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "fig6_age_emp.png", dpi=150); plt.close(fig)
print("done")
