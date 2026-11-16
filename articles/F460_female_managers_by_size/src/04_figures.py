"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：厚生労働省「雇用均等基本調査」（企業調査）役職別女性管理職（等）割合をもとに作成者が加工して作成"
META = {"Software": None}
SIX = ["5,000人以上", "1,000~4,999人", "300~999人", "100~299人", "30~99人", "10~29人"]
LAB = [s.replace("~", "〜") for s in SIX]
main = json.load(open(R / "main.json", encoding="utf-8")); req = json.load(open(R / "requestion.json", encoding="utf-8"))
ser = pd.read_csv(R / "series_kacho_up.csv", index_col="year")
sp = pd.read_csv(R / "requestion_spread.csv", index_col="year")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：2025年度 規模別 課長相当職以上と係長相当職
t = main["table_2025"]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
y = np.arange(len(SIX))
a = [t[s]["kacho_up"] for s in SIX]; b = [t[s]["kakari"] for s in SIX]
ax.barh(y - 0.2, a, 0.38, color=C[0], label="課長相当職以上（役員含む）")
ax.barh(y + 0.2, b, 0.38, color=C[2], label="係長相当職")
for i in range(len(SIX)):
    ax.text(a[i] + 0.3, y[i] - 0.2, f"{a[i]:.1f}%", va="center", fontsize=9, color=C[0])
    ax.text(b[i] + 0.3, y[i] + 0.2, f"{b[i]:.1f}%", va="center", fontsize=9, color=C[2])
ax.set_yticks(y, LAB); ax.invert_yaxis(); ax.set_xlim(0, 30)
ax.set_xlabel("その役職に占める女性の割合（%）"); ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper right")
ax.set_title("図1　企業の規模別の女性の割合（2025年度）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.17, right=0.97, top=0.9, bottom=0.2)
foot(fig, "並びは企業の規模の大きい順（常用労働者数）。")
save(fig, "fig1_by_size_2025.png")

# 図2：課長相当職以上の推移
fig, ax = plt.subplots(figsize=(8.8, 4.8))
cols = ["#1f4e8c", C[0], "#7fb0e8", "#9b9a96", C[3], C[1]]
for s, l, c in zip(SIX, LAB, cols):
    ax.plot(ser.index, ser[s], marker="o", ms=3.5, color=c, lw=1.8, label=l)
    if s in ("30~99人", "10~29人"):
        ax.text(2025.3, ser.loc[2025, s], f"{l} {ser.loc[2025, s]:.1f}%", va="center", fontsize=8.5, color=c)
b4 = ser.loc[2025, SIX[:4]]
ax.text(2025.3, b4.mean(), f"100人以上の4規模\n{b4.min():.1f}〜{b4.max():.1f}%", va="center", fontsize=8.5, color=INK2)
ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
ax.set_xlim(2010.5, 2028.5); ax.set_ylim(0, 28); ax.set_ylabel("課長相当職以上に占める女性の割合（%）")
ax.set_xticks([2011, 2013, 2015, 2017, 2019, 2021, 2023, 2025])
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.set_title("図2　課長相当職以上（役員含む）の女性の割合の推移", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.2)
foot(fig, "2012・2014年度は同じ表が見つからず点がない。")
save(fig, "fig2_series_kacho_up.png")

# 図3：役職ごとの倍率（10〜29人 ÷ 5,000人以上）
rr = main["H3"]["ratio_by_role_2025"]
r11 = main["robustness"]["R1_roles_gap"]
names = ["役員", "部長相当職", "課長相当職", "係長相当職"]; keys = ["yakuin", "bucho", "kacho", "kakari"]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
x = np.arange(4)
vals = [rr[k] for k in keys]
ax.bar(x, vals, 0.55, color=C[0])
for i, vv in enumerate(vals):
    ax.text(i, vv + 0.08, f"{vv:.1f}倍", ha="center", fontsize=10, color=C[0])
ax.axhline(1, color=INK2, lw=0.8)
ax.set_xticks(x, names); ax.set_ylim(0, 4.8); ax.set_ylabel("10〜29人 ÷ 5,000人以上（倍）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.set_title("図3　小さい会社と大きい会社の女性の割合の倍率（役職別、2025年度）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.2)
foot(fig, "1倍より上なら、10〜29人の会社の方が女性の割合が高い。")
save(fig, "fig3_ratio_by_role.png")

# 図4：100人以上の4規模の幅と、小さい規模との差
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.plot(sp.index, sp.big4_range, marker="o", ms=3.5, color=C[0], lw=2, label="100人以上の4つの規模の中の幅（最大−最小）")
ax.plot(sp.index, sp.s10_29_minus_big4_mean, marker="o", ms=3.5, color=C[1], lw=2, label="10〜29人 − 100人以上の4規模の平均")
ax.plot(sp.index, sp.s30_99_minus_big4_mean, marker="o", ms=3.5, color=C[3], lw=2, label="30〜99人 − 100人以上の4規模の平均")
ax.set_ylim(0, 20); ax.set_ylabel("ポイント（課長相当職以上）")
ax.set_xticks([2011, 2013, 2015, 2017, 2019, 2021, 2023, 2025])
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("図4　規模の差は、100人より下で開く", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.2)
foot(fig)
save(fig, "fig4_spread.png")
print("figures ok")
