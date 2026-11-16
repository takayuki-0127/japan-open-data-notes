"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC = "出典：総務省「家計調査」二人以上の世帯 第4-6表（世帯主の年齢階級別、年次）、総務省「消費者物価指数」をもとに作成者が加工"
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
MID = dict(zip(AG, [25, 35, 45, 55, 65, 75]))
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：品目別の推移（名目、全年齢の平均）
a = pd.read_csv(RES / "items_avg_by_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.1, right=0.86, top=0.83, bottom=0.14)
for k, (c, lab) in enumerate([("newspaper", "新聞"), ("books", "書籍"), ("magazine", "雑誌")]):
    ax.plot(a.index, a[c] / 1000, color=C6[k], lw=2)
    ax.text(2025.4, a[c].iloc[-1] / 1000, lab, fontsize=9, va="center")
ax.set_ylabel("1世帯の年間の支出（千円、名目）"); ax.set_xlabel("年"); ax.set_ylim(0, 42); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("新聞・書籍・雑誌への支出は、20年余りでそろって減った", x=0.02, ha="left", fontsize=13, y=0.97)
H2 = m["H2"]
fig.text(0.02, 0.885, f"二人以上の世帯の平均。2002〜04年平均→2023〜25年平均の対数差×100：新聞 {H2['newspaper']:.0f}、書籍 {H2['books']:.0f}、雑誌 {H2['magazine']:.0f}", fontsize=9, color=INK2)
save(fig, "fig1_items_by_year.png")

# 図2：新聞の減り方（年齢別、名目と実質）
c = pd.read_csv(RES / "changes_by_item_age.csv").set_index(["item", "kind"])
nom, real = c.loc[("newspaper", "nominal"), AG].astype(float), c.loc[("newspaper", "real"), AG].astype(float)
fig, ax = plt.subplots(figsize=(8.2, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.16)
x = np.arange(len(AG)); w = 0.38
ax.bar(x - w / 2, nom, w, color=C6[0], label="名目")
ax.bar(x + w / 2, real, w, color=GRAY, label="実質（書籍・他の印刷物の物価で割る）")
for xi, v in zip(x - w / 2, nom): ax.text(xi, v - 4, f"{v:.0f}", ha="center", va="top", fontsize=8.5)
for xi, v in zip(x + w / 2, real): ax.text(xi, v - 4, f"{v:.0f}", ha="center", va="top", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(AG); ax.set_ylim(-310, 15)
ax.set_ylabel("新聞の支出の変化（対数差×100）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.suptitle("新聞の支出は、若い世帯ほど大きく減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"世帯主の年齢別、2002〜04年平均 → 2023〜25年平均。名目：29歳以下と30代の平均 {m['H3']['young']:.0f}、60代と70歳以上の平均 {m['H3']['old']:.0f}", fontsize=9, color=INK2)
save(fig, "fig2_newspaper_change_by_age.png")

# 図3：新聞の支出を生まれ年で並べる
n = pd.read_csv(RES / "newspaper_by_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.1, right=0.97, top=0.83, bottom=0.14)
for k, g in enumerate(AG):
    by = n.index - MID[g]
    ax.plot(by, n[g] / 1000, color=C6[k], lw=2, label=g)
ax.set_xlabel("世帯主のおおよその生まれ年（調査年 − 年齢の階級の中央）"); ax.set_ylabel("新聞の年間の支出（千円、名目）")
ax.set_ylim(0, 46); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="lower left")
fig.suptitle("新聞の支出は、生まれ年が同じなら年齢が違ってもほぼつながる", x=0.02, ha="left", fontsize=13, y=0.97)
H4 = m["H4"]
fig.text(0.02, 0.885, f"各線は1つの年齢の階級の2002〜2025年。AIC：年齢＋世代 {H4['aic_age_cohort']:.0f}、年齢＋時代 {H4['aic_age_period']:.0f}（小さいほど当てはまりがよい）", fontsize=9, color=INK2)
save(fig, "fig3_newspaper_by_birth_year.png")

# 図4：年齢の構成を固定した場合
t = pd.read_csv(RES / "requestion_composition.csv").set_index("item")
items = [("newspaper", "新聞"), ("books", "書籍"), ("magazine", "雑誌"), ("print_total", "書籍・他の印刷物")]
fig, ax = plt.subplots(figsize=(8.2, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.16)
x = np.arange(len(items))
p = [t.loc[k, "published_change"] for k, _ in items]; f = [t.loc[k, "fixed_weight_change"] for k, _ in items]
ax.bar(x - w / 2, p, w, color=C6[0], label="公表の平均（年齢の構成は毎年の実際）")
ax.bar(x + w / 2, f, w, color=GRAY, label="年齢の構成を2002〜04年に固定")
for xi, v in zip(x - w / 2, p): ax.text(xi, v - 2, f"{v:.0f}", ha="center", va="top", fontsize=8.5)
for xi, v in zip(x + w / 2, f): ax.text(xi, v - 2, f"{v:.0f}", ha="center", va="top", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([l for _, l in items]); ax.set_ylim(-112, 8)
ax.set_ylabel("支出の変化（名目、対数差×100）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.suptitle("高齢の世帯が増えたことが、新聞の減り方を小さく見せていた", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"70歳以上の世帯の割合：{q['weights_start']['70歳以上']:.0f}% → {q['weights_end']['70歳以上']:.0f}%。書籍は逆に、構成の変化で減り方が大きく見えた", fontsize=9, color=INK2)
save(fig, "fig4_composition_fixed.png")
print("ok")
