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
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：日本銀行「企業物価指数」「最終需要・中間需要物価指数」、総務省「消費者物価指数」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))

# ---- 図1：段階ごとの前年同月比（1980〜2022） --------------------------------------------
y = pd.read_csv(R / "yoy_stages_1980_2022.csv", index_col=0)
y.index = pd.PeriodIndex(y.index, freq="M").to_timestamp()
fig, ax = plt.subplots(figsize=(9.0, 5.0))
for col, lab, c in [("素原材料", "素原材料", C[3]), ("中間財", "中間財", C[2]), ("最終財_消費財", "最終財（消費財）", C[1]), ("CPI_工業製品", "消費者物価（工業製品）", C[0])]:
    ax.plot(y.index, y[col], color=c, lw=1.6 if col != "CPI_工業製品" else 2.2, label=lab)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("前年同月比（%）")
ax.legend(frameon=False, fontsize=9.5, loc="upper right", ncol=2)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("値上がりの時期はほぼ同時。下流ほど振れ幅が小さい（1980〜2022年）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：企業物価は2015年基準の需要段階別指数（2022年4月まで）。消費者物価は2020年基準。消費税の引き上げを含む。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_yoy_by_stage.png")

# ---- 図2：12か月の累積の伝わり方 -----------------------------------------------------------
p = pd.read_csv(R / "dl_cumulative_paths.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8.4, 4.9))
for col, lab, c in [("最終財_消費財", "最終財（消費財）から", C[1]), ("中間財", "中間財から", C[2]), ("素原材料", "素原材料から", C[3])]:
    ax.plot(range(13), p[col].values, color=c, lw=2.2, marker="o", ms=4)
    v = main["passthrough_1980_2022_cpi_industrial"][col]
    ax.text(12.3, p[col].values[-1], f"{lab}\n{v['cum']:.3f}（{v['ci95'][0]:.3f}〜{v['ci95'][1]:.3f}）", fontsize=9, color=INK, va="center")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(0, 16.5); ax.set_xticks(range(0, 13, 2))
ax.set_xlabel("上流の値段が動いてからの月数")
ax.set_ylabel("上流が1%上がったときの\n消費者物価（工業製品）の動き（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"消費財の1%の値上がりは、1年で{main['passthrough_1980_2022_cpi_industrial']['最終財_消費財']['cum']:.1f}%が店頭に届く。素原材料からは{main['passthrough_1980_2022_cpi_industrial']['素原材料']['cum']:.3f}%", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：前月比の分布ラグ回帰（0〜12か月、月の効果と消費税の月を除く、1980年1月〜2022年4月）。括弧は95%区間（Newey–West）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.13, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig2_cumulative_passthrough.png")

# ---- 図3：2016〜2026 ステージ別 --------------------------------------------------------------
f = pd.read_csv(R / "yoy_fdid_2016_2026.csv", index_col=0)
f.index = pd.PeriodIndex(f.index, freq="M").to_timestamp()
fig, ax = plt.subplots(figsize=(9.0, 5.0))
box = []
for col, lab, c in [("ステージ1_財", "ステージ1（いちばん上流）", C[3]), ("ステージ4_財", "ステージ4", C[2]), ("最終需要_財", "最終需要", C[1]), ("CPI_生鮮除く財", "消費者物価（生鮮食品を除く財）", C[0])]:
    ax.plot(f.index, f[col], color=c, lw=2, label=lab)
    pk = main["peaks_2021_2024"][col]
    t = pd.Period(pk["peak"], "M").to_timestamp()
    ax.plot([t], [pk["yoy_at_peak"]], marker="o", color=c, ms=7)
    box.append(f"{lab}：{t.year}年{t.month}月 {pk['yoy_at_peak']:.0f}%")
ax.text(0.01, 0.97, "山（2021〜24年）\n" + "\n".join(box), transform=ax.transAxes, fontsize=8.8, color=INK, va="top",
        bbox=dict(facecolor="#fcfcfb", edgecolor=GRID))
ax.legend(frameon=False, fontsize=9, loc="lower left", ncol=2)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("前年同月比（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"2022年の山は、上流から店頭まで{main['peak_gap_stage1_to_cpi_goods_months']}か月の差。高さは69%から7%に", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：最終需要・中間需要物価指数（2020年基準）の財。2016年1月〜2026年9月。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_fdid_stages_2016_2026.png")

# ---- 図4：問い直し（2020→2024年の上昇幅） ----------------------------------------------------
lv = req["level_rise_2020_to_2024_pct"]
labs = ["ステージ1_財", "ステージ2_財", "ステージ3_財", "ステージ4_財", "最終需要_財", "CPI_生鮮除く財"]
names = ["ステージ1", "ステージ2", "ステージ3", "ステージ4", "最終需要", "消費者物価\n（生鮮除く財）"]
fig, ax = plt.subplots(figsize=(8.6, 4.9))
x = np.arange(len(labs))
ax.bar(x, [lv[c] for c in labs], color=[C[3]] * 5 + [C[0]], width=0.6)
for xi, c in zip(x, labs):
    ax.text(xi, lv[c] + 1.5, f"+{lv[c]:.1f}%", ha="center", fontsize=10, color=INK)
ax.set_xticks(x, names)
ax.set_ylabel("2020年平均から2024年平均への上昇率（%）")
ax.set_ylim(0, 105)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"段階を下るごとに上昇は薄まる：上流 +{lv['ステージ1_財']:.1f}% → 店頭 +{lv['CPI_生鮮除く財']:.1f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：最終需要・中間需要物価指数（2020年基準）の財と、消費者物価指数。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig4_level_rise_by_stage.png")
print("figures done")
