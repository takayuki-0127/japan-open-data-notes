"""04 図（PNG、日付などのメタデータは入れない）。"""
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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「家計調査」家計収支編 二人以上の世帯 第4-6表、「消費者物価指数」2025年基準 をもとに作成者が加工して作成"
META = {"Software": None}
fmt = matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
LAB = ["29歳以下", "30代", "40代", "50代", "60代", "70歳以上"]


def finish(fig, title, bottom=0.15):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.78 if "\n" in title else 0.84, bottom=bottom, wspace=0.25)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


b = pd.read_csv(R / "by_year.csv")
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
avg = b[b.group == "平均"].set_index("year")

# 図1：平均の世帯の名目と実質
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=False)
for ax, item, name, col in ((axes[0], "choco", "チョコ（チョコレート＋チョコレート菓子）", C[1]), (axes[1], "snack", "スナック菓子", C[0])):
    ax.plot(avg.index, avg[item], color=col, lw=2, label="名目（その年の円）")
    ax.plot(avg.index, avg[item + "_real"], color=col, lw=2, ls="--", label="実質（2025年の値段の円）")
    ax.annotate(f"{avg[item].iloc[-1]:,.0f}\n（2025年は\n名目＝実質）", (2025, avg[item].iloc[-1]), textcoords="offset points", xytext=(4, 0),
                va="center", fontsize=8)
    ax.set_title(name, loc="left", fontsize=10.5)
    ax.yaxis.set_major_formatter(fmt); ax.set_ylim(0, None); ax.set_xlim(2004, 2029)
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.set_ylabel("1世帯当たり年間の支出（円）")
    ax.legend(frameon=False, fontsize=8.6, loc="lower left")
cn, cr = m["choco"]["nominal"]["平均"]["pct"], m["choco"]["real"]["平均"]["pct"]
sr = m["snack"]["real"]["平均"]["pct"]
cs = m["robustness"]["実質（菓子類の指数）"]["choco_平均"]
finish(fig, f"チョコは名目{cn:+.1f}%、チョコレートの物価指数で割ると{cr:+.1f}%（菓子類の指数なら{cs:+.1f}%）。\nスナック菓子はポテトチップスの指数で割っても{sr:+.1f}%（2005〜07年→2023〜25年）")
save(fig, "fig1_nominal_vs_real.png")

# 図2：年齢別の伸び（名目・実質）
g = pd.read_csv(R / "growth_by_age.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
x = np.arange(len(AGES))
for ax, item, name in ((axes[0], "choco", "チョコ"), (axes[1], "snack", "スナック菓子")):
    for k, (kind, lab, col) in enumerate((("nominal", "名目", C[1] if item == "choco" else C[0]), ("real", "実質", "#9a9993"))):
        v = g[(g.item == item) & (g.kind == kind)].set_index("group").loc[AGES, "pct"]
        bars = ax.bar(x + (k - 0.5) * 0.38, v, width=0.38, color=col, label=lab)
        for xi, vi in zip(x + (k - 0.5) * 0.38, v):
            ax.text(xi, vi + (4 if vi >= 0 else -4), f"{vi:+.0f}", ha="center", va="bottom" if vi >= 0 else "top", fontsize=7.8)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(x, LAB, fontsize=9); ax.set_title(name, loc="left", fontsize=10.5)
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8.6, loc="upper left")
axes[0].set_ylabel("2005〜07年→2023〜25年の伸び（%）")
axes[0].set_xlabel("世帯主の年齢"); axes[1].set_xlabel("世帯主の年齢")
finish(fig, "どちらも世帯主が60代の世帯で最も伸びた（実質はチョコレート・ポテトチップスの物価指数で割った値）", bottom=0.18)
save(fig, "fig2_growth_by_age.png")

# 図3：同じ生まれ年の世帯を10年追う（問い直し）
c = pd.read_csv(R / "cohort.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
tr = ["29歳以下→30代", "30代→40代", "40代→50代", "50代→60代"]
for ax, item, name in ((axes[0], "choco_real", "チョコ（実質）"), (axes[1], "snack_real", "スナック菓子（実質）")):
    d = c[c.item == item]
    for k, (w, mk) in enumerate((("2005-07→2015-17", "o"), ("2013-15→2023-25", "s"))):
        e = d[d.window == w]
        xs = np.arange(4) + (k - 0.5) * 0.25
        ax.scatter(xs, e.cohort_pct, color=C[1] if item == "choco_real" else C[0], marker=mk, s=42, zorder=3,
                   label=f"同じ層を10年追った変化 {w}")
        ax.scatter(xs, e.age_gap_pct_at_start, facecolor="none", edgecolor=INK2, marker=mk, s=42, zorder=3,
                   label=f"始めの年の1つ上の年齢との差 {w}")
        for xi, a0, a1 in zip(xs, e.age_gap_pct_at_start, e.cohort_pct):
            ax.plot([xi, xi], [a0, a1], color=GRID, lw=1.4, zorder=2)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(range(4), tr, fontsize=8.6); ax.set_title(name, loc="left", fontsize=10.5)
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
axes[0].set_ylabel("変化（%）")
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, frameon=False, fontsize=7.8, bbox_to_anchor=(0.5, 0.05))
finish(fig, "同じ生まれ年の世帯を追うと、スナック菓子は8組すべてで年齢の差より上。\nチョコはチョコレートの指数で割ると3組（菓子類の指数なら7組）で、物価の指数の選び方で読みが変わる", bottom=0.27)
save(fig, "fig3_cohort.png")

# 図4：菓子類の伸びの内訳
ic = pd.read_csv(R / "items_contrib.csv", index_col=0).drop("sweets")
JA = {"choco": "チョコ", "snack": "スナック菓子", "icecream": "アイスクリーム・シャーベット", "other": "他の菓子", "wagashi_other": "他の和生菓子",
      "yogashi_other": "他の洋生菓子", "senbei": "せんべい", "biscuit": "ビスケット", "candy": "キャンデー", "cake": "ケーキ", "jelly": "ゼリー",
      "pudding": "プリン", "castella": "カステラ", "manju": "まんじゅう", "yokan": "ようかん"}
ic = ic.loc[list(JA)][::-1]
fig, ax = plt.subplots(figsize=(10, 5.2))
cols = [C[1] if k == "choco" else C[0] if k == "snack" else "#b9b8b2" for k in ic.index]
ax.barh([JA[k] for k in ic.index], ic["diff"], color=cols)
for i, (k, r) in enumerate(ic.iterrows()):
    ax.text(max(r["diff"], 0) + 60, i, f"{r['diff']:+,.0f}円（{r.share_of_sweets_growth_pct:+.1f}%）", va="center", ha="left", fontsize=8.4)
ax.axvline(0, color=INK2, lw=0.8); ax.xaxis.set_major_formatter(fmt); ax.set_xlim(-1500, 7600)
ax.set_xlabel("1世帯当たり年間の支出の変化（円、名目。かっこは菓子類全体の伸びに占める割合）")
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
tot = m["sweets"]["nominal"]["平均"]["diff"]
cs = ic.loc[["choco", "snack"], "share_of_sweets_growth_pct"].sum()
fig.suptitle(f"菓子類の伸び（{tot:+,.0f}円）のうち、チョコとスナック菓子は合わせて{cs:.0f}%（品目の並びは表の順）", x=0.01, ha="left", fontsize=12.5)
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.22, right=0.97, top=0.9, bottom=0.14)
save(fig, "fig4_items_contrib.png")
print("ok")
