"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "svg.hashsalt": "f388"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cd1"]
INK = "#0b0b0b"; INK2 = "#52514e"
SRC = "出典：総務省「住宅・土地統計調査」1998〜2023年（住宅の種類、構造、建築の時期別住宅数－全国）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
PER = ["1998-2003", "2003-2008", "2008-2013", "2013-2018", "2018-2023"]
PL = [p.replace("-", "→") for p in PER]
NAME = {"total": "住宅全体", "wood": "木造", "nonwood": "非木造"}

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 なくなった住宅の平均築年数（国交省の値と再現）
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(PER))
mine = [M["mean_age_lost"][k]["total"] for k in PER]
ref = [M["mlit_reference_mean_age_lost"].get(k) for k in PER]
ax.bar(x - 0.18, mine, width=0.34, color=C[0], label="この記事の計算（同じ考え方）")
ax.bar([i + 0.18 for i, r in enumerate(ref) if r], [r for r in ref if r], width=0.34, color="#b9b7b0", label="国交省の資料の値")
for i, v in enumerate(mine):
    ax.text(i - 0.18, v + 0.6, f"{v:.1f}", ha="center", fontsize=9, color=INK)
for i, r in enumerate(ref):
    if r:
        ax.text(i + 0.18, r + 0.6, f"{r:.1f}", ha="center", fontsize=9, color=INK2)
ax.set_xticks(x, PL); ax.set_ylim(0, 45)
ax.set_ylabel("なくなった住宅の平均築年数（年）")
ax.set_title("「約30年」は、なくなった住宅の平均築年数。同じ考え方で計算すると27〜38年", loc="left", fontsize=11.5)
ax.legend(frameon=False, loc="upper left")
fig.subplots_adjust(bottom=0.2, top=0.9)
save(fig, "fig1_mean_age_lost.png", "注：人が住む住宅で、建築時期ごとに5年間で減った数に、その期間の真ん中の築年数をかけて平均。国交省の値は社会資本整備審議会の資料（2008→2013年 32.1年）")

# fig2 生命表（1998〜2023年をまとめた値）
cv = pd.read_csv(RES / "survival_curves.csv")
fig, ax = plt.subplots(figsize=(8, 4.8))
for i, st in enumerate(["total", "wood", "nonwood"]):
    ax.plot(cv.age, cv[f"{st}_pooled"] * 100, color=C[i], lw=2, label=NAME[st])
    med = M["pooled_1998_2023"]["median"][st]
    ax.plot([med], [50], "o", ms=7, color=C[i], mec="white", mew=1.5)
    off = {"total": (1.5, -7), "wood": (-17, -7), "nonwood": (1.5, 3)}[st]
    ax.annotate(f"{NAME[st]} 築{med:.0f}年", (med, 50), xytext=(med + off[0], 50 + off[1]), fontsize=9, color=INK)
ax.axhline(50, color=INK2, lw=0.8, ls="--")
ax.set_xlim(0, 100); ax.set_ylim(0, 102)
ax.set_xlabel("築年数（年）"); ax.set_ylabel("建った住宅のうち、人が住んで残る割合（%）")
ax.set_title("半分が残らなくなるのは築45年。木造は38年、非木造は54年", loc="left", fontsize=11.5)
ax.legend(frameon=False, loc="upper right")
fig.subplots_adjust(bottom=0.22, top=0.9)
save(fig, "fig2_life_table.png", "注：1998〜2023年の5回の5年間をまとめ、築年数10年ごとの残る割合から作った生命表。今の消え方が続いた場合の計算で、予測ではない。\n　　非木造の築60年より先はデータが少なく、ほぼ減らない形になっている")

# fig3 5年で残る割合（期間ごと、住宅全体）
cs = pd.read_csv(RES / "cohort_survival.csv")
cs = cs[cs.structure == "total"]
fig, ax = plt.subplots(figsize=(8, 4.8))
for i, k in enumerate(PER):
    g = cs[cs.y0 == int(k[:4])].sort_values("age_mid")
    ax.plot(g.age_mid, g.ratio * 100, "-o", color=C[i], lw=1.6, ms=6, mec="white", mew=1, label=PL[i])
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xlabel("その5年間の真ん中の築年数（年）"); ax.set_ylabel("5年後にも人が住んで残る割合（%）")
ax.set_title("5年で残る割合は、同じ築年数でも期間によって10ポイント以上ずれる", loc="left", fontsize=11.5)
ax.legend(frameon=False, ncol=3, loc="lower left", title="期間（住宅全体）", fontsize=8.5, title_fontsize=8.5)
ax.set_ylim(70, 107)
fig.subplots_adjust(bottom=0.2, top=0.9)
save(fig, "fig3_survival_by_period.png", "注：点は建築時期のまとまり（1950年以前、1951〜70、71〜80、81〜90、91〜2000、2001〜05、06〜10、11〜15年）。建築の時期「不詳」の増減の影響を受ける")

# fig4 問い直し：平均築年数が上がった理由
d = M["requestion_decomposition"]
fig, ax = plt.subplots(figsize=(8, 4.4))
sts = ["total", "wood"]
y = np.arange(len(sts))
a = [d[s]["stock_aging_effect"] for s in sts]; b = [d[s]["hazard_change_effect"] for s in sts]
ax.barh(y + 0.18, a, height=0.34, color=C[0], label="住宅の年齢構成が古くなった分")
ax.barh(y - 0.18, b, height=0.34, color=C[3], label="築年数ごとの消え方が変わった分")
for i, s in enumerate(sts):
    ax.text(a[i] + 0.08, i + 0.18, f"+{a[i]:.1f}年", va="center", fontsize=9, color=INK)
    ax.text(b[i] + 0.08, i - 0.18, f"+{b[i]:.1f}年", va="center", fontsize=9, color=INK)
ax.set_yticks(y, [f"{NAME[s]}\n（{d[s]['from']:.1f}→{d[s]['to']:.1f}年）" for s in sts])
ax.invert_yaxis(); ax.set_xlim(0, 7)
ax.set_xlabel("なくなった住宅の平均築年数の上がり（1998→2003年 から 2018→2023年、年）")
ax.set_title("平均築年数の上がり6.5年の半分あまりは、住宅の年齢構成が古くなったため", loc="left", fontsize=11.5)
ax.legend(frameon=False, loc="center right")
fig.subplots_adjust(bottom=0.24, top=0.9, left=0.2)
save(fig, "fig4_requestion_decomposition.png", "注：建築時期の構成と消え方（ハザード）を入れ替えた計算の2通りの平均で分けた。消え方は負の値を0にした計算のため、合計は実際の値と少しずれる")
