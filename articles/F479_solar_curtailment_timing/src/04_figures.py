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
SRC = "出典：九州電力送配電「エリア需給実績データ」（九州本土）、資源エネルギー庁 系統WG資料（2024年9月18日）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
fy = pd.read_csv(R / "fy_summary.csv").set_index("fy").loc[2018:]
fm = pd.read_csv(R / "fy_month_gwh.csv").set_index("fy")
hp = pd.read_csv(R / "hour_share_by_period.csv").set_index("hour")
daily = pd.read_csv(R / "daily.csv")

# ---- 図1：年度ごとの抑制量と抑制率（上下2段。軸は1つずつ） ------------------------------------
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.8, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
a1.bar(fy.index, fy.pv_cut_gwh, width=0.65, color=C[1])
for y, v in fy.pv_cut_gwh.items():
    a1.text(y, v + 20, f"{v:,.0f}", ha="center", fontsize=9, color=INK)
a1.set_ylabel("太陽光の抑制量（GWh）")
a1.set_ylim(0, 1450)
a1.grid(axis="y", color=GRID, lw=0.8); a1.set_axisbelow(True)
a2.plot(fy.index, fy.re_cut_rate_pct, color=C[0], lw=2, marker="o", ms=6, label="このデータから計算（太陽光＋風力）")
a2.scatter(fy.index, fy.official_rate_pct, s=70, facecolors="none", edgecolors=INK, lw=1.3, zorder=3, label="資源エネルギー庁の公表値")
for y, v in fy.re_cut_rate_pct.items():
    a2.text(y, v + 0.55, f"{v:.1f}%", ha="center", fontsize=8.8, color=INK)
a2.set_ylabel("出力制御率（%）")
a2.set_ylim(0, 10.5)
a2.set_xticks(fy.index); a2.set_xticklabels([f"{y}年度" for y in fy.index], fontsize=9)
a2.legend(loc="upper left", frameon=False, fontsize=8.8)
a2.grid(axis="y", color=GRID, lw=0.8); a2.set_axisbelow(True)
a1.set_title(f"九州の出力制御は2023年度に最大（{main['fy_pv_cut_gwh']['2023']:,.0f}GWh）、その後も2022年度までより多い", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：出力制御率＝抑制量÷（発電実績＋抑制量）。公表値は2018〜2023年度の実績。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.93, bottom=0.12, hspace=0.12)
save(fig, "fig1_fy_curtailment.png")

# ---- 図2：年度×月のヒートマップ（単色の濃淡） -------------------------------------------------
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("seq", ["#f4f3ef", "#f6c7a9", "#eb6834", "#8f3412"])
fig, ax = plt.subplots(figsize=(8.8, 5.0))
order = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
M = fm[[str(m) for m in order]].loc[2018:]
im = ax.imshow(M.values, aspect="auto", cmap=cmap, vmin=0, vmax=float(M.values.max()))
ax.set_xticks(range(12)); ax.set_xticklabels([f"{m}月" for m in order])
ax.set_yticks(range(len(M))); ax.set_yticklabels([f"{y}年度" for y in M.index])
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M.values[i, j]
        if v >= 1:
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.2, color="white" if v > 180 else INK)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.set_label("抑制量（GWh）")
ax.set_title(f"抑制の{main['spring_share_pct']:.0f}%は3〜5月。秋（9〜11月）は{main['autumn_share_pct']:.0f}%、夏（6〜8月）は{main['jun_aug_share_pct']:.0f}%", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：数字は月ごとの太陽光の抑制量（GWh、1未満は空白）。割合は2018〜2025年度の合計に対するもの。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.11, right=0.90, top=0.92, bottom=0.13)
save(fig, "fig2_month_heatmap.png")

# ---- 図3：時刻ごとの割合 --------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
hrs = np.arange(6, 19)
w = 0.38
ax.bar(hrs - w / 2 - 0.02, hp.loc[hrs, "fy2018_2022"], width=w, color=C[0], label="2018〜2022年度", zorder=2)
ax.bar(hrs + w / 2 + 0.02, hp.loc[hrs, "fy2023_2025"], width=w, color=C[1], label="2023〜2025年度", zorder=2)
ax.axvspan(10.5, 13.5, color="#efeeea", lw=0, zorder=0)
ax.text(12, 25.2, f"11〜13時台で{main['noon_11_13_share_pct']:.0f}%", ha="center", fontsize=9.5, color=INK)
ax.set_xticks(hrs); ax.set_xticklabels([f"{x}時" for x in hrs], fontsize=9)
ax.set_ylabel("1日の抑制量に占める割合（%）"); ax.set_ylim(0, 27)
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"抑制は昼の{main['peak_hour']}時台が最も多い（{main['peak_hour_share_pct']:.0f}%）。時刻の形は期間で変わらない", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：「12時」は12:00〜13:00。期間ごとの合計を100%とした割合。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig3_hour_profile.png")

# ---- 図4：春の日の昼の需要と抑制量（休日・平日） ---------------------------------------------------
sp = daily[daily.month.isin([3, 4, 5])]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for hol, col, lab in [(0, C[0], "平日"), (1, C[1], "休日（土日・祝日）")]:
    g = sp[sp.holiday == hol]
    ax.scatter(g.noon_demand_gw, g.cut_gwh, s=14, color=col, alpha=0.55, edgecolors="none", label=f"{lab}（{len(g)}日）")
ax.set_xlabel("昼（11〜13時台）の平均エリア需要（GW）")
ax.set_ylabel("1日の太陽光の抑制量（GWh）")
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("休日は昼の需要が低い日が多い。需要でそろえると休日と平日の差は大きく縮む", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, f"注：2019〜2026年の3〜5月の日（2018年10月以降のうち春の日）。昼の平均需要は全日で平日{req['noon_demand_gw_weekday']:.1f}GW、休日{req['noon_demand_gw_holiday']:.1f}GW。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig4_demand_vs_cut.png")
print("ok")
