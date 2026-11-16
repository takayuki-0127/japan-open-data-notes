"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC = "出典：総務省「労働力調査」基本集計 長期時系列表4(1)（年平均）をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
d = pd.read_csv(D / "lfs_status.csv"); d = d[d.year >= 1990]
P = {s: d[d.sex == s].set_index("year") for s in ["total", "male", "female"]}
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：雇人のない業主の数
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.86, top=0.83, bottom=0.14)
for s, c, lab in [("total", C6[0], "男女計"), ("male", C6[2], "男性"), ("female", C6[1], "女性")]:
    ax.plot(P[s].index, P[s].solo, color=c, lw=2); ax.text(2025.5, P[s].solo.iloc[-1], lab, fontsize=9, color=c, va="center")
ax.set_ylabel("雇人のない業主（万人）"); ax.set_xlabel("年"); ax.set_ylim(0, 750); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
s0 = m["solo"]["total"]
fig.suptitle("ひとりで事業をする人（雇人のない業主）は、長い目で見て減った", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.885, f"2000〜02年平均 {s0['start']:.0f}万人 → 2023〜25年平均 {s0['end']:.0f}万人（対数差×100 で {s0['dlog']:.0f}）。雇人のない業主 ＝ 自営業主 − 雇有業主", fontsize=9, color=INK2)
save(fig, "fig1_solo_count.png")

# 図2：就業者に占める割合
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.86, top=0.83, bottom=0.14)
for s, c, lab in [("total", C6[0], "男女計"), ("male", C6[2], "男性"), ("female", C6[1], "女性")]:
    v = 100 * P[s].solo / P[s].employed; ax.plot(v.index, v, color=c, lw=2); ax.text(2025.5, v.iloc[-1], lab, fontsize=9, color=c, va="center")
ax.set_ylabel("就業者に占める雇人のない業主の割合（%）"); ax.set_xlabel("年"); ax.set_ylim(0, 14); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("働く人に占める割合は下がり、女性は2016年ごろから横ばい", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"男女計：2000〜02年平均 {m['share']['start']:.1f}% → 2023〜25年平均 {m['share']['end']:.1f}%（{m['share']['change_pt']:+.1f}ポイント）", fontsize=9, color=INK2)
save(fig, "fig2_solo_share.png")

# 図3：働き方の種類別（2000〜02年平均＝100）
t = P["total"]; base = t.loc[2000:2002].mean(numeric_only=True)
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.84, top=0.83, bottom=0.14)
for col, c, lab in [("employees", C6[0], "雇用者"), ("solo", C6[1], "雇人のない業主"), ("with_employees", C6[2], "雇有業主"), ("family", GRAY, "家族従業者")]:
    v = 100 * t[col] / base[col]; v = v.loc[2000:]; ax.plot(v.index, v, color=c, lw=2); ax.text(2025.5, v.iloc[-1], lab, fontsize=9, color=c, va="center")
ax.axhline(100, color=GRAY, lw=0.6, ls=":")
ax.set_ylabel("指数（2000〜02年平均＝100）"); ax.set_xlabel("年"); ax.set_ylim(0, 130); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("雇われる人は増え、自営の人はどの形でも減った", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"2000〜02年→2023〜25年（対数差×100）：雇用者 {m['employees_dlog']:+.0f}、雇人のない業主 {m['solo']['total']['dlog']:+.0f}、雇有業主 {m['with_employees_dlog']:+.0f}", fontsize=9, color=INK2)
save(fig, "fig3_status_index.png")

# 図4：2010年以降の男女（2013〜15年平均＝100）
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.8, top=0.83, bottom=0.14)
for s, col, c, lab, ls in [("female", "solo", C6[1], "女性の雇人のない業主", "-"), ("male", "solo", C6[2], "男性の雇人のない業主", "-"), ("female", "employed", C6[1], "女性の就業者", "--")]:
    v = 100 * P[s][col] / P[s].loc[2013:2015, col].mean(); v = v.loc[2010:]
    ax.plot(v.index, v, color=c, lw=2, ls=ls); ax.text(2025.5, v.iloc[-1], lab, fontsize=8.5, color=c, va="center")
ax.axhline(100, color=GRAY, lw=0.6, ls=":")
ax.set_ylabel("指数（2013〜15年平均＝100）"); ax.set_xlabel("年"); ax.set_ylim(85, 120); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("最近は女性のひとり事業主が増えたが、女性の就業者の伸びより小さい", x=0.02, ha="left", fontsize=12, y=0.97)
sh = q["share"]
fig.text(0.02, 0.885, f"2013〜15年→2023〜25年：女性の雇人のない業主 {m['H4']['female']['dlog']:+.1f}、男性 {m['H4']['male']['dlog']:+.1f}。女性の就業者に占める割合は {sh['female']['y2013_15']:.1f}%→{sh['female']['y2023_25']:.1f}%", fontsize=9, color=INK2)
save(fig, "fig4_recent_by_sex.png")
print("ok")
