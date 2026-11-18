"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from common import ROOT

R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#8a63d2"]
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SRC = "出典：文部科学省「学校基本調査」（高等学校 全日制・定時制、本科、各年度5月1日時点）をもとに作成者が加工して作成"
META = {"Software": None}
comma = ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")


def finish(fig, ax, title, pad=12):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=pad)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
by = pd.read_csv(R / "by_year.csv", index_col="year")

# ---- 図1：学科別の生徒数 ----
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ser = [("商業", C[0]), ("工業", C[1]), ("農業", C[2]), ("家庭", C[3]), ("総合学科", C[4]), ("その他専門", C[5])]
lab = {"その他専門": "その他の専門学科（理数・外国語など）"}
for g, c in ser:
    ax.plot(by.index, by[g], color=c, lw=2.2, marker="o", ms=4.5, label=lab.get(g, g))
    off = {"商業": 9000, "総合学科": -9000}.get(g, 0)
    ax.text(2025.8, by[g].iloc[-1] + off, f"{lab.get(g, g)[:6]} {by[g].iloc[-1] / 1e4:.1f}万", va="center", fontsize=8.8, color=INK)
ax.set_xlim(1983, 2033)
ax.set_xticks(list(by.index))
ax.set_ylim(0, 640000)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, p: f"{v / 1e4:.0f}万"))
ax.set_xlabel("年度")
ax.set_ylabel("生徒数（人）")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper right", fontsize=9, bbox_to_anchor=(0.86, 1.0))
finish(fig, ax, "商業は58.2万人→15.8万人（−73%）、工業は47.8万人→19.8万人（−59%）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig1_course_counts.png")

# ---- 図2：職業学科の減少の分解 ----
rob = pd.DataFrame(m["robustness"])
rows = rob[rob.check.str.startswith("職業学科")].reset_index(drop=True)
names = ["1985→2025年度", "1995→2025年度", "2010→2025年度"]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
yy = [2, 1, 0]
ax.barh(yy, rows.size_effect, color=C[0], height=0.5, label="高校生全体が減った効果", edgecolor=BG, lw=1)
ax.barh(yy, rows.share_effect, left=rows.size_effect, color=C[3], height=0.5, label="職業学科を選ぶ割合が下がった効果", edgecolor=BG, lw=1)
for y, (_, r) in zip(yy, rows.iterrows()):
    ax.text(r.size_effect / 2, y, f"{r.size_effect / 1e4:.1f}万", ha="center", va="center", fontsize=9, color="white")
    ax.text(r.size_effect + r.share_effect / 2, y, f"{r.share_effect / 1e4:.1f}万", ha="center", va="center", fontsize=9, color=INK)
    ax.text(r.change - 8000, y, f"計 {r.change / 1e4:.1f}万人\n（{r.share_from_pct:.1f}%→{r.share_to_pct:.1f}%）", ha="right", va="center", fontsize=8.8, color=INK)
ax.set_yticks(yy)
ax.set_yticklabels(names)
ax.set_xlim(-1250000, 20000)
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, p: f"{v / 1e4:.0f}万"))
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("職業学科の生徒数の変化（人）")
ax.grid(axis="x", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="lower left", fontsize=9)
finish(fig, ax, "職業学科の減少（1985→2025年度 −91.9万人）は、全体の減少の効果の方が大きい")
fig.subplots_adjust(left=0.15, right=0.97, top=0.88, bottom=0.17)
save(fig, "fig2_decomposition.png")

# ---- 図3：地方別の職業学科の割合（北から南） ----
REG = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州沖縄"]
rg = m["region"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = list(range(len(REG)))
for i, g in zip(x, REG):
    a, b = rg[g]["voc_share_2010_pct"], rg[g]["voc_share_2025_pct"]
    ax.plot([i, i], [b, a], color=GRID, lw=3, zorder=1)
    ax.scatter([i], [a], s=60, color=C[0], zorder=2, edgecolor=BG, linewidth=1.5, label="2010年度" if i == 0 else None)
    ax.scatter([i], [b], s=60, color=C[1], zorder=3, edgecolor=BG, linewidth=1.5, label="2025年度" if i == 0 else None)
    ax.text(i + 0.12, a, f"{a:.1f}", va="center", fontsize=8.6, color=INK)
    ax.text(i + 0.12, b, f"{b:.1f}", va="center", fontsize=8.6, color=INK)
ax.axhline(m["voc_share_2025_pct"], color=INK2, lw=0.8, ls=":")
ax.text(7.45, m["voc_share_2025_pct"] + 0.5, f"全国 2025年度 {m['voc_share_2025_pct']:.1f}%", ha="right", fontsize=8.4, color=INK2)
ax.set_xticks(x)
ax.set_xticklabels(REG)
ax.set_ylim(0, 35)
ax.set_ylabel("職業学科の生徒の割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper left", fontsize=9.2, ncol=2)
finish(fig, ax, "どの地方も2010→2025年度に1.6〜3.1ポイント下がった（北から南に並べた）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.14)
save(fig, "fig3_region_share.png")

# ---- 図4：工業・商業の中の小学科（2005・2025年度） ----
fig, axes = plt.subplots(1, 2, figsize=(9.6, 5.2), gridspec_kw={"width_ratios": [1.25, 1]})
for ax, course, ks in [(axes[0], "工業", ["機械関係", "電子機械関係", "電気関係", "電子関係", "情報技術関係", "建築関係", "土木関係", "化学工業関係"]),
                       (axes[1], "商業", ["商業関係", "情報処理関係", "国際経済関係", "会計関係", "流通経済関係"])]:
    d = q["key_subcourses"][course]
    yy = list(range(len(ks)))[::-1]
    v05 = [d[k]["2005"]["n"] for k in ks]
    v25 = [d[k]["2025"]["n"] for k in ks]
    ax.barh([y + 0.19 for y in yy], v05, height=0.36, color=C[0], label="2005年度", edgecolor=BG, lw=1)
    ax.barh([y - 0.19 for y in yy], v25, height=0.36, color=C[1], label="2025年度", edgecolor=BG, lw=1)
    for y, a, b in zip(yy, v05, v25):
        ax.text(b + 1500, y - 0.19, f"{b / 1e4:.1f}万", va="center", fontsize=8.2, color=INK)
    ax.set_yticks(yy)
    ax.set_yticklabels([k.replace("関係", "") for k in ks])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, p: f"{v / 1e4:.0f}万"))
    ax.set_title(f"{course}（計 {q['totals'][course]['2005'] / 1e4:.1f}万→{q['totals'][course]['2025'] / 1e4:.1f}万人）", fontsize=10.5, color=INK, loc="left")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
axes[0].set_xlim(0, 85000)
axes[1].set_xlim(0, 175000)
axes[1].set_xticks([0, 50000, 100000, 150000])
axes[0].set_xticks([0, 20000, 40000, 60000, 80000])
axes[1].legend(frameon=False, loc="lower right", fontsize=9)
fig.suptitle("2005→2025年度、商業の情報処理は7.1万→3.5万人、工業の情報技術は2.4万→1.7万人", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.98, top=0.85, bottom=0.12, wspace=0.42)
save(fig, "fig4_subcourses.png")
print("ok")
