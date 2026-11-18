"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
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
INK, INK2, GRID, MUTED = "#0b0b0b", "#52514e", "#e4e3df", "#a3a29c"
SRC = "出典：農林水産省（林野庁）「特用林産物生産統計調査」（2005〜2025年）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


A = pd.read_csv(R / "annual_national.csv")
IT = pd.read_csv(R / "items_2005_2025.csv")
G = pd.read_csv(R / "requestion_regions.csv")

# 図1：生しいたけ（原木・菌床）
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.bar(A.year, A.fresh_bed / 1000, color=C[0], width=0.7, label="菌床栽培", edgecolor="#fcfcfb", linewidth=1)
ax.bar(A.year, A.fresh_log / 1000, bottom=A.fresh_bed / 1000, color=C[3], width=0.7, label="原木栽培", edgecolor="#fcfcfb", linewidth=1)
for y in (2005, 2010, 2015, 2020, 2025):
    s = A[A.year == y].iloc[0]
    ax.text(y, s.fresh_total / 1000 + 1.2, f"原木{s.log_share_fresh_pct:.1f}%", ha="center", fontsize=8.8, color=INK)
ax.set_xlabel("年"); ax.set_ylabel("生産量（千トン）")
ax.set_xticks(range(2005, 2026, 5))
ax.legend(frameon=False, loc="upper left", ncol=2)
ax.set_ylim(0, 92)
finish(fig, ax, "生しいたけの原木栽培の割合は、2005年の28.9%から2025年の4.9%へ")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig1_fresh_shiitake_log_bed.png")

# 図2：きのこの品目別（2005年と2025年）
lab = {"生しいたけ": "生しいたけ", "乾しいたけ_生換算": "乾しいたけ（生に換算）", "えのきたけ": "えのきたけ", "ぶなしめじ": "ぶなしめじ",
       "まいたけ": "まいたけ", "エリンギ": "エリンギ", "なめこ": "なめこ", "ひらたけ": "ひらたけ"}
fig, ax = plt.subplots(figsize=(9, 5.4))
ys = list(range(len(IT)))[::-1]
h = 0.38
ax.barh([y + h / 2 for y in ys], IT.t_2005 / 1000, height=h, color=MUTED, label="2005年")
ax.barh([y - h / 2 for y in ys], IT.t_2025 / 1000, height=h, color=C[0], label="2025年")
for y, (_, s) in zip(ys, IT.iterrows()):
    ax.text(max(s.t_2005, s.t_2025) / 1000 + 2, y, f"{s.change_pct:+.1f}%（割合 {s.share_2005_pct:.1f}→{s.share_2025_pct:.1f}%）",
            va="center", fontsize=8.8, color=INK)
ax.set_yticks(ys, [lab[i] for i in IT.item])
ax.set_xlabel("生産量（千トン）")
ax.set_xlim(0, 190)
ax.legend(frameon=False, loc="lower right")
finish(fig, ax, "増えたのはえのきたけ・ぶなしめじ・まいたけ。乾しいたけは6割近く減った", grid="x")
fig.text(0.01, 0.045, "注：割合はきのこ類総計（2005年41.9万トン、2025年44.2万トン）に占める割合。乾しいたけは表の生換算値。", fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.2, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig2_kinoko_items.png")

# 図3：生産者数
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.axvspan(2004.5, 2009.5, color="#f0efeb", zorder=0)
ax.plot(A.year, A.prod_log_dry, color=C[3], lw=2, marker="o", ms=4, label="原木（主に乾しいたけ）")
ax.plot(A.year, A.prod_log_fresh, color=C[1], lw=2, marker="o", ms=4, label="原木（主に生しいたけ）")
ax.plot(A.year, A.prod_bed, color=C[0], lw=2, marker="o", ms=4, label="菌床")
ax.text(2004.7, 9500, "2009年までは\n数え方が違う\n（2010年から、\n乾・生の両方を\n作る戸は収入の\n多い方だけに\n数える注）", fontsize=8.3, color=INK2, va="top")
for col in ["prod_log_dry", "prod_log_fresh", "prod_bed"]:
    v = A[A.year == 2025][col].iloc[0]
    ax.annotate(f"{v:,.0f}", (2025, v), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK)
ax.set_xlabel("年"); ax.set_ylabel("生産者（戸）")
ax.set_xticks(range(2005, 2026, 5)); ax.set_xlim(2004.5, 2026.8)
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "原木の生産者は2013→2023年に47.4%減。菌床の生産者は減り方が小さい")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig3_producers.png")

# 図4：地方別（北から南）の原木の生しいたけと乾しいたけ
regs = list(G[G.year == 2005].sort_values("order").region)
fig, axes = plt.subplots(1, 2, figsize=(10, 5.4))
x = range(len(regs))
for ax, col, ttl in [(axes[0], "fresh_log", "原木栽培の生しいたけ（トン）"), (axes[1], "dry_total", "乾しいたけ（トン）")]:
    v05 = G[G.year == 2005].sort_values("order")[col].values
    v25 = G[G.year == 2025].sort_values("order")[col].values
    ax.bar([i - 0.2 for i in x], v05, width=0.4, color=MUTED, label="2005年")
    ax.bar([i + 0.2 for i in x], v25, width=0.4, color=C[3] if col == "fresh_log" else C[2], label="2025年")
    ax.set_xticks(list(x), regs, rotation=45, ha="right", fontsize=9)
    ax.set_title(ttl, loc="left", fontsize=11, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left" if col == "fresh_log" else "upper left", fontsize=9)
fig.suptitle("どの地方でも原木の生しいたけは76〜89%減。乾しいたけは九州・沖縄が全国の7割に",
             x=0.01, ha="left", fontsize=12, color=INK)
fig.text(0.01, 0.045, "注：地方は北から南の順。2025年は近畿と四国で原木の生しいたけが秘匿の県が1県ずつあり、その県は足していない。", fontsize=7.6, color=INK2)
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.25, wspace=0.22)
save(fig, "fig4_regions_log_dry.png")
print("ok")
