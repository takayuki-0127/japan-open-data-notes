"""図4枚（PNG）。日付などのメタデータは入れない。都道府県は名前を出さず、地方で色分けする。"""
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
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7a5cc4", "#3d9fb5", "#8a8a85"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「国勢調査」（時系列データ、令和7年 人口等基本集計 原数値・不詳補完値）をもとに作成者が加工して作成"
META = {"Software": None}
RORDER = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.4, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.14)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
# 図1：全国の不詳の割合
na = pd.read_csv(R / "age_unknown_national.csv"); na = na[na.year >= 1975]
mt = pd.Series(m["marital_rate_total15_by_year"]); mt.index = mt.index.astype(int); mt = mt[mt.index >= 1975]
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(na.year, na.rate, color=C[0], lw=2.4, marker="o", ms=4, label="年齢「不詳」（総人口に対する割合）")
ax.plot(mt.index, mt.values, color=C[1], lw=2.0, marker="s", ms=4, ls="--", label="配偶関係「不詳」（15歳以上に対する割合）")
for x, y, c in [(2000, na[na.year == 2000].rate.iloc[0], C[0]), (2025, na[na.year == 2025].rate.iloc[0], C[0]), (2025, mt[2025], C[1])]:
    ax.annotate(f"{y:.2f}%", (x, y), textcoords="offset points", xytext=(6, -4 if c == C[0] else 4), fontsize=9.5, color=c)
ax.set_xlim(1972, 2030); ax.set_ylim(0, 5.2); ax.set_ylabel("不詳の割合（%）"); ax.legend(frameon=False, loc="upper left")
finish(fig, ax, f"年齢「不詳」は2000年 {m['age_unknown_rate']['2000']:.2f}% → 2025年 {m['age_unknown_rate']['2025']:.2f}%（全国、原数値）")
save(fig, "fig1_national_unknown.png")

# 図2：地方別（北から南）
rg = pd.read_csv(R / "age_unknown_region.csv")
Y = [2000, 2010, 2020, 2025]
x = np.arange(len(RORDER)); w = 0.2
fig, ax = plt.subplots(figsize=(9, 5.2))
for k, y in enumerate(Y):
    v = rg[rg.year == y].set_index("region").reindex(RORDER).rate.values
    ax.bar(x + (k - 1.5) * w, v, width=w, color=[C[7], C[6], C[0], C[1]][k], label=f"{y}年")
ax.set_xticks(x, RORDER); ax.set_ylabel("年齢「不詳」の割合（%）"); ax.legend(frameon=False, loc="upper left", ncol=4)
finish(fig, ax, "年齢「不詳」はどの地方でも増えた（地方は北から南の順）")
save(fig, "fig2_region_unknown.png")

# 図3：配偶関係「不詳」の年齢別（男女計）
mr = pd.read_csv(R / "marital_unknown_national_rate.csv")
AG = ["15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳",
      "60～64歳", "65～69歳", "70～74歳", "75～79歳", "80～84歳", "85歳以上"]
fig, ax = plt.subplots(figsize=(9, 5.2))
for y, c, ls in [(2000, C[7], ":"), (2010, C[6], "--"), (2020, C[0], "-"), (2025, C[1], "-")]:
    s = mr[(mr.year == y) & (mr.sex == ("総数" if y == 2025 else "総数(計算)"))].set_index("age").reindex(AG).rate
    ax.plot(np.arange(len(AG)), s.values, color=c, lw=2.2 if y >= 2020 else 1.5, ls=ls, marker="o", ms=3.5, label=f"{y}年")
ax.set_xticks(np.arange(len(AG)), [a.replace("歳", "") for a in AG], rotation=45, ha="right", fontsize=9)
ax.set_ylabel("配偶関係「不詳」の割合（%、男女計）"); ax.legend(frameon=False, loc="upper right")
ax.annotate("2000年は15〜34歳の不詳が\nほぼ0（表の作り方が違う可能性）", (2, 0.1), xytext=(4.6, 7.2), fontsize=9, color=INK2,
            arrowprops={"arrowstyle": "->", "color": INK2, "lw": 0.8})
finish(fig, ax, f"2025年の配偶関係「不詳」は25〜34歳で {m['marital_rate_2534_2025']:.1f}%、65歳以上で {m['marital_rate_65plus_2025']:.1f}%")
fig.subplots_adjust(bottom=0.2)
save(fig, "fig3_marital_by_age.png")

# 図4：補完の影響（都道府県、2025年）
im = pd.read_csv(R / "imputation_effect.csv")
p = im[(im.year == 2025) & (im.pref_code > 0)]
fig, ax = plt.subplots(figsize=(9, 5.4))
for i, rgn in enumerate(RORDER):
    q = p[p.region == rgn]
    ax.scatter(q.unknown_rate, q.d65, s=34, color=C[i], label=rgn, edgecolor="white", lw=0.5, zorder=3)
n = im[(im.year == 2025) & (im.pref_code == 0)].iloc[0]
ax.scatter([n.unknown_rate], [n.d65], s=110, marker="D", color=INK, zorder=4, label="全国")
ax.annotate(f"全国：{n.s65_original:.2f}% → {n.s65_imputed:.2f}%（{n.d65:+.2f}）", (n.unknown_rate, n.d65), xytext=(10, -16),
            textcoords="offset points", fontsize=9.5)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlabel("年齢「不詳」の割合（%、原数値）"); ax.set_ylabel("65歳以上の割合の差（補完値−原数値、ポイント）")
ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="lower left")
finish(fig, ax, "不詳の多い都道府県ほど、補完すると65歳以上の割合が小さくなる（2025年）")
fig.subplots_adjust(left=0.1, bottom=0.16)
save(fig, "fig4_imputation_effect.png")
print("ok")
