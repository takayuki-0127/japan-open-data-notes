"""図を作る（Noto Sans CJK JP）。"""
import pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
ROOT = pathlib.Path(__file__).resolve().parents[1]; FIG = ROOT / "figures"
df = pd.read_csv(ROOT / "data" / "articles.csv")
TYPE = {"E": "効果・関係の推定", "P": "予測", "D": "記述・測定・作法"}
COL = {"Y": "#9aa5b1", "U": "#e0a03a", "N": "#c8553d"}
LAB = {"Y": "はっきりした答えが出た", "U": "手法・前提しだいで言い切れない", "N": "差・関係は見えなかった"}
# 1 種類別の内訳
fig, ax = plt.subplots(figsize=(8, 4.0))
order = ["E", "P", "D"]; left = np.zeros(3)
for o in ["N", "U", "Y"]:
    v = np.array([((df.type == t) & (df.outcome == o)).sum() for t in order])
    ax.barh([TYPE[t] for t in order], v, left=left, color=COL[o], label=LAB[o])
    for i, (l, x) in enumerate(zip(left, v)):
        if x: ax.text(l + x / 2, i, str(x), ha="center", va="center", color="white", fontsize=10)
    left += v
for i, t in enumerate(order):
    s = df[df.type == t]; ax.text(left[i] + 0.8, i, f"{s.broad.mean():.0%}", va="center", fontsize=10)
ax.invert_yaxis(); ax.set_xlabel("記事数（右の％は「見えなかった＋言い切れない」の割合）")
ax.set_xlim(0, 62); ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=8, frameon=False); ax.set_title("118本の看板記事の結論：種類別", loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig1_by_type.png", dpi=150)
# 2 手法の系統別
b = df.groupby("family").agg(n=("broad", "size"), s=("broad", "mean")).sort_values("s")
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.barh(b.index, b.s, color=["#c8553d" if f == "因果推論" else "#7d8b99" for f in b.index])
for i, (n, s) in enumerate(zip(b.n, b.s)): ax.text(s + 0.01, i, f"{s:.0%}（{n}本）", va="center", fontsize=9)
ax.axvline(df.broad.mean(), color="k", lw=0.8, ls="--"); ax.text(df.broad.mean() + 0.01, len(b) - 0.4, f"全体 {df.broad.mean():.0%}", fontsize=9)
ax.set_xlim(0, 0.85); ax.set_xlabel("「見えなかった＋言い切れない」の割合"); ax.set_title("手法の系統別", loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig2_by_family.png", dpi=150)
# 3 効果の記事：分析の単位別
E_ = df[df.type == "E"]
u = E_.groupby("unit").agg(n=("broad", "size"), s=("broad", "mean"), sn=("strict", "mean"))
u = u.loc[[x for x in ["都道府県（47）", "市区町村（約1,700）", "法人・地点など（1万以上）", "全国の時系列", "その他"] if x in u.index]]
fig, ax = plt.subplots(figsize=(8, 3.8)); x = np.arange(len(u))
ax.bar(x - 0.2, u.sn, 0.4, color=COL["N"], label="見えなかった")
ax.bar(x + 0.2, u.s, 0.4, color=COL["U"], label="見えなかった＋言い切れない")
for i, (n, s) in enumerate(zip(u.n, u.s)): ax.text(i + 0.2, s + 0.02, f"{n}本", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([t.replace("（", "\n（") for t in u.index], fontsize=9); ax.set_ylim(0, 1); ax.set_ylabel("割合")
ax.legend(frameon=False, fontsize=9); ax.set_title("効果・関係を推定した39本：データの単位が大きいほど「見えた」わけではない", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig3_effect_by_unit.png", dpi=150)
# 4 記事番号に沿って
fig, ax = plt.subplots(figsize=(9, 3.4))
ymap = {"E": 2, "P": 1, "D": 0}
for o in ["Y", "U", "N"]:
    s = df[df.outcome == o]; ax.scatter(s.num, s.type.map(ymap), s=46 if o != "Y" else 18, color=COL[o], label=LAB[o], zorder=3)
roll = df.sort_values("num").broad.rolling(20, center=True, min_periods=10).mean()
ax2 = ax.twinx(); ax2.plot(df.sort_values("num").num, roll, color="k", lw=1.2); ax2.set_ylim(0, 1); ax2.set_ylabel("前後20本の割合", fontsize=9)
ax.set_yticks([0, 1, 2]); ax.set_yticklabels([TYPE["D"], TYPE["P"], TYPE["E"]]); ax.set_ylim(-0.6, 2.6); ax.set_xlabel("記事番号（F01〜F120）")
ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=3, bbox_to_anchor=(0, 1.18)); fig.tight_layout(); fig.savefig(FIG / "fig4_timeline.png", dpi=150)
# 5 検出力への言及
fig, ax = plt.subplots(figsize=(7, 3.2))
g = E_.groupby("outcome").power.agg(["mean", "size"]).reindex(["N", "U", "Y"])
ax.bar([LAB[o] for o in g.index], g["mean"], color=[COL[o] for o in g.index])
for i, (m, n) in enumerate(zip(g["mean"], g["size"])): ax.text(i, m + 0.02, f"{m:.0%}（{int(round(m*n))}/{n}本）", ha="center", fontsize=9)
ax.set_ylim(0, 0.6); ax.set_ylabel("検出力に触れた割合"); ax.tick_params(axis="x", labelsize=8)
ax.set_title("効果・関係の推定39本：「見えなかった」記事でも、検出力に触れたのは4本に1本", loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "fig5_power_mention.png", dpi=150)
print("ok")
