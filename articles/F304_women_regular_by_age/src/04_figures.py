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
BLUE, ORANGE, GRAY, INK2, LBLUE = "#2a78d6", "#eb6834", "#9a9893", "#52514e", "#86b6ef"
SRC = "出典：総務省「労働力調査」詳細集計 表10-2・基本集計 表3-1（年平均）をもとに作成者が加工。正規雇用率＝正規の職員・従業員÷人口"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
t = pd.read_csv(RES / "female_by_age_2015_2025.csv")
lab = [a.replace("歳", "").replace("以上", "+") for a in t.age]
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：年齢別の正規・非正規の増減
mm = m["main"]
fig, ax = plt.subplots(figsize=(8.6, 4.9)); fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.17)
x = np.arange(len(t)); w = 0.38
ax.bar(x - w / 2, t.d_regular, w, color=BLUE, label="正規の職員・従業員")
ax.bar(x + w / 2, t.d_nonregular, w, color=GRAY, label="非正規の職員・従業員")
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8.5)
ax.set_ylabel("増減 2015→2025年（万人）"); ax.set_xlabel("年齢（歳）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
fig.suptitle("女性の正規は25〜34歳と45〜59歳で増え、25〜44歳では非正規が減った", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.875, f"正規 +{mm['d_regular_sum_ages']:.0f}万人のうち 25〜44歳 +{mm['d_regular_25_44']:.0f}、45〜64歳 +{mm['d_regular_45_64']:.0f}。25〜44歳の非正規は {mm['d_nonregular_25_44']:+.0f}万人", fontsize=9, color=INK2)
save(fig, "fig1_change_by_age.png")

# 図2：年齢別の正規雇用率（2005・2015・2025年）
s = pd.read_csv(RES / "female_rate_by_age_year.csv")
ages = t.age.tolist()[:12]
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.15)
for y, c in ((2005, LBLUE), (2015, GRAY), (2025, BLUE)):
    v = s[s.year == y].set_index("age").loc[ages, "rate"]
    ax.plot(range(len(ages)), v.values, color=c, lw=2.2, marker="o", ms=4, label=f"{y}年")
ax.set_xticks(range(len(ages))); ax.set_xticklabels([a.replace("歳", "") for a in ages], fontsize=8.5)
ax.set_ylabel("正規雇用率（%、人口に対する割合）"); ax.set_xlabel("年齢（歳）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.legend(frameon=False, fontsize=9)
fig.suptitle("どの年齢でも上がったが、同じ年で見た30代の落ち込みは浅くならなかった", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.885, f"25〜29歳と35〜39歳の差：2015年 {mm['m_dip_start']:.1f}ポイント → 2025年 {mm['m_dip_end']:.1f}ポイント（25〜29歳がより大きく上がったため）", fontsize=9, color=INK2)
save(fig, "fig2_rate_by_age.png")

# 図3：コホートで追う
c = pd.read_csv(RES / "requestion_cohort.csv")
k = c[c.age_start == "25～29歳"]
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.2)
xx = np.arange(len(k))
for xi, (_, r) in zip(xx, k.iterrows()):
    ax.plot([xi, xi], [r.rate_start, r.rate_end], color="#cfcdc8", lw=2.5, zorder=1)
ax.scatter(xx, k.rate_start, color=GRAY, s=40, zorder=2, label="25〜29歳のとき")
ax.scatter(xx, k.rate_end, color=BLUE, s=40, zorder=3, label="10年後（35〜39歳）")
ax.set_xticks(xx); ax.set_xticklabels([b.replace("年生まれ", "") for b in k.birth_years], rotation=45, ha="right", fontsize=8)
ax.set_xlabel("生まれ年"); ax.set_ylabel("正規雇用率（%）"); ax.set_ylim(20, 50); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.suptitle("同じ生まれ年で追うと、30代での落ち込みは小さくなった", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"25〜29歳→10年後の35〜39歳の変化：1973〜77年生まれ {q['change_first']:+.1f}ポイント → 1986〜90年生まれ {q['change_last']:+.1f}ポイント", fontsize=9, color=INK2)
save(fig, "fig3_cohort.png")

# 図4：分解（年齢別）
fig, ax = plt.subplots(figsize=(8.6, 4.9)); fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.17)
ax.bar(x - w / 2, t.rate_effect, w, color=BLUE, label="正規雇用率が上がった分")
ax.bar(x + w / 2, t.pop_effect, w, color=ORANGE, label="人口が変わった分")
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8.5)
ax.set_ylabel("2015→2025年の正規の増減への寄与（万人）"); ax.set_xlabel("年齢（歳）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
fig.suptitle("増えた分は率の上昇。30〜44歳では人口の減少が打ち消した", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"合計：率の分 +{mm['rate_effect']:.0f}万人、人口の分 {mm['pop_effect']:.0f}万人、交差の項 {mm['interaction']:.0f}万人", fontsize=9, color=INK2)
save(fig, "fig4_decomposition.png")
print("ok")
