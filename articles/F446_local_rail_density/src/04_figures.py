"""図4枚（PNG）。日付などのメタデータは入れない。運輸局は北から南の順。事業者名の順位は出さない。"""
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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#9b9a97"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：国土交通省「鉄道統計年報」「地域鉄道事業者一覧」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def style(ax, title):
    ax.set_title(title, loc="left", fontsize=12, color=INK, pad=10)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)


m = json.load(open(R / "main.json", encoding="utf-8"))
a = pd.read_csv(R / "aggregate_by_year.csv").set_index("fy")

# 図1：まとめた輸送密度
fig, ax = plt.subplots(figsize=(8.6, 4.6))
ax.plot(a.index, a["agg_density"], color=C[0], lw=2.2, marker="o", ms=4)
for y in (2012, 2019, 2020, 2023):
    ax.annotate(f"{a.loc[y, 'agg_density']:,.0f}", (y, a.loc[y, "agg_density"]), xytext=(0, 8 if y != 2020 else -16),
                textcoords="offset points", ha="center", fontsize=9.5, color=INK)
ax.set_ylim(0, 3500); ax.set_xticks(range(2012, 2024, 2))
ax.set_ylabel("輸送密度（人／日、営業キロの重みつき）"); ax.set_xlabel("年度")
style(ax, f"地域鉄道{m['n_balanced']}社の輸送密度：2012→2019年度に{100 - m['H1_2019_vs_2012_pct']:.0f}%減、2023年度は2019年度の{m['H2_2023_vs_2019_pct']:.0f}%")
fig.subplots_adjust(left=0.11, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig1_aggregate_density.png")

# 図2：輸送密度の帯ごとの事業者の数
c = pd.read_csv(R / "count_by_band.csv").set_index("fy")
fig, ax = plt.subplots(figsize=(8.6, 4.8))
bottom = np.zeros(len(c))
cols = ["#1f4e8c", "#2a78d6", "#8cb8ea", "#f2b38f", "#eb6834"][::-1]
for i, col in enumerate(c.columns):
    ax.bar(c.index, c[col], bottom=bottom, color=cols[i], label=col, width=0.7)
    bottom += c[col].values
for y in c.index:
    v = c.loc[y, "500人未満"] + c.loc[y, "500〜1,000人"]
    ax.text(y, v / 2, f"{v}", ha="center", va="center", fontsize=8.5, color="white")
ax.set_xticks(c.index); ax.tick_params(axis="x", labelsize=9)
ax.set_ylabel("事業者の数"); ax.set_xlabel("年度")
ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.15))
style(ax, "輸送密度1,000人未満の事業者は29社（2012・2019年度）→32社（2023年度）（白い数字）")
fig.subplots_adjust(left=0.08, right=0.97, top=0.89, bottom=0.25)
save(fig, "fig2_count_by_band.png")

# 図3：運輸局別（北から南）
bb = pd.read_csv(R / "by_bureau.csv")
fig, ax = plt.subplots(figsize=(8.6, 4.8))
x = np.arange(len(bb)); wd = 0.26
for j, (col, lab) in enumerate([("agg_2012", "2012年度"), ("agg_2019", "2019年度"), ("agg_2023", "2023年度")]):
    ax.bar(x + (j - 1) * wd, bb[col], wd, color=[C[4], C[0], C[1]][j], label=lab)
ax.set_xticks(x, [f"{g}\n（{n}社）" for g, n in zip(bb["bureau"], bb["n"])], fontsize=9)
ax.set_ylabel("輸送密度（人／日）")
ax.legend(frameon=False, fontsize=9.5)
style(ax, "どの運輸局でも、2023年度は2019年度より低い（運輸局は北から南）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.2)
save(fig, "fig3_by_bureau.png")

# 図4：問い直し　定期と定期外（2019年度＝100）
q = pd.read_csv(R / "requestion_pass_nonpass.csv")
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.5), sharey=True)
for ax, g in zip(axes, ["第三セクター", "中小民鉄"]):
    t = q[q.group == g].set_index("fy")
    ax.plot(t.index, t["pass_idx_2019"], color=C[0], lw=2, label="定期（通勤・通学）")
    ax.plot(t.index, t["nonpass_idx_2019"], color=C[1], lw=2, label="定期外")
    for col, cc, dy in [("pass_idx_2019", C[0], 6), ("nonpass_idx_2019", C[1], -12)]:
        ax.annotate(f"{t.loc[2023, col]:.0f}", (2023, t.loc[2023, col]), xytext=(4, dy), textcoords="offset points", fontsize=9, color=cc)
    ax.axhline(100, color=INK2, lw=0.7, ls=":")
    ax.set_ylim(40, 140); ax.set_xticks(range(2012, 2024, 3)); ax.set_xlabel("年度")
    ax.set_title(g, loc="left", fontsize=11.5, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
axes[0].set_ylabel("人キロ（2019年度＝100）")
axes[0].legend(frameon=False, fontsize=9, loc="lower left")
fig.suptitle("定期外は2020年度に半分近くまで減り、2023年度も9割に届かない", x=0.01, ha="left", fontsize=12, color=INK)
fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.17, wspace=0.08)
save(fig, "fig4_pass_nonpass.png")
print("ok")
