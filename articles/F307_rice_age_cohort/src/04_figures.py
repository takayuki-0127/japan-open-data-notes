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
SRC = "出典：総務省「家計調査」二人以上の世帯 第4-6表（世帯主の年齢階級別、年次）をもとに作成者が加工"
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：年齢別の推移（1世帯あたり）
b = pd.read_csv(RES / "rice_quantity_by_year.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.83, top=0.83, bottom=0.14)
for k, a in enumerate(AG):
    ax.plot(b.index, b[a], color=C6[k], lw=2)
    off = {"50～59歳": 0.5, "70歳以上": 1.5, "60～69歳": -1.5, "40～49歳": -3.5}.get(a, 0)
    ax.text(2025.4, b[a].iloc[-1] + off, a, fontsize=8.5, va="center", color="#0b0b0b")
ax.set_ylabel("米の購入数量（kg／世帯・年）"); ax.set_xlabel("年"); ax.set_ylim(0, 125); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("米を買う量は、年齢の高い世帯ほど大きく減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"二人以上の世帯、世帯主の年齢別。平均 {m['H1']['平均'][0]:.1f}kg（2002〜04年）→ {m['H1']['平均'][1]:.1f}kg（2019〜21年）", fontsize=9, color=INK2)
save(fig, "fig1_rice_by_age_year.png")

# 図2：減り方（1世帯あたり・1人あたり）
c1 = pd.read_csv(RES / "h1_rice_quantity_change.csv", index_col=0).loc[AG]
cp = pd.read_csv(RES / "h2_rice_per_person_change.csv", index_col=0).loc[AG]
fig, ax = plt.subplots(figsize=(8.2, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.16)
x = np.arange(len(AG)); w = 0.38
ax.bar(x - w / 2, c1.logchange, w, color=C6[0], label="1世帯あたり")
ax.bar(x + w / 2, cp.logchange, w, color=GRAY, label="1人あたり（世帯人員で割る）")
for xi, v in zip(x - w / 2, c1.logchange): ax.text(xi, v - 1.5, f"{v:.0f}", ha="center", va="top", fontsize=8.5)
for xi, v in zip(x + w / 2, cp.logchange): ax.text(xi, v - 1.5, f"{v:.0f}", ha="center", va="top", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(AG); ax.set_ylim(-60, 5)
ax.set_ylabel("購入数量の変化（対数差×100）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.suptitle("若い世帯ほど減ったのではなく、高齢の世帯ほど減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"2002〜04年平均 → 2019〜21年平均。29歳以下と30代の平均 {m['H3']['young_mean']:.0f}、60代と70歳以上の平均 {m['H3']['old_mean']:.0f}", fontsize=9, color=INK2)
save(fig, "fig2_change_by_age.png")

# 図3：生まれ年で並べる（1人あたり）
t = pd.read_csv(RES / "requestion_cells.csv")
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.14)
for k, a in enumerate(AG):
    s = t[t.age == a].sort_values("birth_mid")
    ax.plot(s.birth_mid, s.pp, color=C6[k], lw=2, label=a)
ax.set_xlabel("生まれ年（およそ。調査年 − 年齢の階級の中央）"); ax.set_ylabel("米の購入数量（kg／人・年）")
ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper right")
fig.suptitle("生まれ年で並べると、年齢の違う線がつながる", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, "1人あたりの量。新しい生まれ年ほど少ない。同じ生まれ年なら、年齢が変わっても量はおおむね近い（70歳以上はやや低い）", fontsize=9, color=INK2)
save(fig, "fig3_by_birth_year.png")

# 図4：年齢＋世代のモデルの世代の差
ce = q["cohort_effect_pp_log100"]
ks = [int(k) for k in ce]; vs = [ce[k] for k in ce]
fig, ax = plt.subplots(figsize=(8.2, 4.8)); fig.subplots_adjust(left=0.1, right=0.97, top=0.81, bottom=0.15)
ax.plot(ks, vs, color=C6[0], lw=2.2, marker="o", ms=5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xlabel("生まれ年（5年ごと、およそ）"); ax.set_ylabel("1925年ごろ生まれとの差（対数差×100）")
ax.grid(axis="y", color="#e6e5e1", lw=0.6)
qq = q["lpp"]
fig.suptitle("時代の分を置かず、年齢と世代だけで並べた世代の差", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.88, f"1人あたり、2002〜2025年の144マス。当てはまり（AIC）：年齢＋世代 {qq['aic_age_cohort']:.0f}、年齢＋時代 {qq['aic_age_period']:.0f}。\n時代の効果を0と置く仮定の上の値で、時代の動きがあればこの傾きに混ざる", fontsize=8.5, color=INK2)
save(fig, "fig4_cohort_effects.png")
print("ok")
