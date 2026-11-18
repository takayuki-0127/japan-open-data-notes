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
C = {"truck": "#8a8984", "ship": "#2a78d6", "rail": "#eb6834", "roro": "#1baf7a", "cont": "#eda100"}
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：国土交通省「自動車輸送統計調査」「鉄道輸送統計調査」「内航船舶輸送統計調査」をもとに作成者が加工して作成"
META = {"Software": None}
main = json.load(open(R / "main.json", encoding="utf-8"))
rq = json.load(open(R / "requestion.json", encoding="utf-8"))
a = pd.read_csv(ROOT / "data" / "annual_fy.csv").set_index("fy")
FY = list(a.index)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


def fyticks(ax):
    ax.set_xticks(FY); ax.set_xticklabels([f"{y % 100:02d}" for y in FY]); ax.set_xlabel("年度（20xx年度）")


# 図1：機関別のトンキロと、鉄道＋内航の割合
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.6, 5.0), gridspec_kw={"width_ratios": [1.35, 1]})
for k, lab, col in (("truck_tkm", "トラック（営業用＋自家用）", C["truck"]), ("ship_tkm", "内航", C["ship"]), ("rail_tkm", "鉄道", C["rail"])):
    ax.plot(FY, a[k] / 1000, color=col, lw=2.0, marker="o", ms=3.5, label=lab)
ax.set_ylim(0, 280); ax.set_ylabel("十億トンキロ"); fyticks(ax); ax.grid(axis="y", color=GRID, lw=0.6)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 0.1), fontsize=9)
ax.set_title("輸送トンキロ（重さ×距離）", loc="left", fontsize=11)
sh = 100 * (a.rail_tkm + a.ship_tkm) / (a.truck_tkm + a.rail_tkm + a.ship_tkm)
ax2.plot(FY, sh, color=C["ship"], lw=2.2, marker="o", ms=3.5)
for fy in (2015, 2024, 2025):
    ax2.annotate(f"{sh[fy]:.1f}%", (fy, sh[fy]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=INK2)
ax2.set_ylim(38, 48); ax2.set_ylabel("%"); fyticks(ax2); ax2.grid(axis="y", color=GRID, lw=0.6)
ax2.set_title("鉄道＋内航の割合（トンキロ）", loc="left", fontsize=11)
fig.suptitle(f"2015→2025年度、鉄道＋内航の割合は{main['share_rail_ship_2015']:.1f}%から{main['share_rail_ship_2025']:.1f}%へ。量はどれも減った",
             x=0.01, ha="left", fontsize=12.5)
fig.subplots_adjust(bottom=0.22, top=0.84, left=0.07, right=0.98, wspace=0.28)
foot(fig, "2025年度の鉄道は月報の月の合計（速報）。自動車は2020年4月の調査方法の変更を遡って接続した値")
save(fig, "fig1_mode_tonkm_share.png")

# 図2：ユニットロード（鉄道コンテナ＋RORO船＋コンテナ専用船）と倍増のペース
u = pd.read_csv(R / "unitload_fy.csv").set_index("fy")
fig, ax = plt.subplots(figsize=(8.8, 5.0))
b = np.zeros(len(FY))
for k, lab, col in (("rail_cont", "鉄道コンテナ", C["rail"]), ("roro", "内航 RORO船", C["roro"]), ("contship", "内航 コンテナ専用船", C["cont"])):
    ax.bar(FY, u[k] / 1000, bottom=b, color=col, width=0.7, label=lab); b += u[k].values / 1000
yy = [y for y in FY if y >= 2023] + [2026, 2027, 2028]
ax.plot(yy, [u.loc[2023, "unitload"] / 1000 * 2 ** ((y - 2023) / 10) for y in yy], color=INK2, lw=1.4, ls="--",
        label="2023年度から10年で2倍になるペース（年7.2%）")
ax.set_xlim(2014.4, 2028.6); ax.set_ylim(0, 60)
ax.set_xticks(list(range(2015, 2029))); ax.set_xticklabels([f"{y % 100:02d}" for y in range(2015, 2029)]); ax.set_xlabel("年度（20xx年度）")
ax.set_ylabel("十億トンキロ"); ax.grid(axis="y", color=GRID, lw=0.6)
ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=2)
ax.set_title(f"鉄道コンテナ＋RORO船＋コンテナ船は、2023→2025年度に年{main['unit_cagr_2023_2025']:.1f}%の伸び（{main['unit_tkm_2023']/1000:.1f}→{main['unit_tkm_2025']/1000:.1f}十億トンキロ）",
             loc="left", fontsize=12)
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.08, right=0.98)
foot(fig, "RORO船・コンテナ専用船は内航船舶輸送統計の大型鋼船（営業用）。フェリーは統計の対象外のため入らない。破線は比べるための目安")
save(fig, "fig2_unitload_vs_double_pace.png")

# 図3：月の前年同月比（2021年4月〜2026年3月）
y = pd.read_csv(R / "yoy_monthly.csv")
y["t"] = y.year + (y.month - 0.5) / 12
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for k, lab, col in (("truck_comm_tkm", "営業用トラック", C["truck"]), ("rail_cont_tkm", "鉄道コンテナ", C["rail"]), ("ship_comm_tkm", "内航（営業用）", C["ship"])):
    ax.plot(y.t, y[k + "_yoy"], color=col, lw=1.6, label=lab)
    for p, (t0, t1) in (("before", (2022 + 3 / 12, 2024 + 3 / 12)), ("after", (2024 + 3 / 12, 2026 + 3 / 12))):
        ax.hlines(main[f"yoy_mean_{k}_{p}"], t0, t1, color=col, lw=3.0, alpha=0.55)
ax.axvline(2024 + 3 / 12, color=INK2, lw=0.9, ls="--")
ax.text(2024 + 3 / 12 + 0.04, -19.5, "2024年4月", fontsize=9, color=INK2)
ax.axhline(0, color=INK2, lw=0.6)
ax.set_ylim(-22, 22); ax.set_xlim(2021.25, 2026.25)
ax.set_xticks(range(2022, 2027)); ax.set_xticklabels([f"{t}年" for t in range(2022, 2027)])
ax.set_ylabel("前年同月比（%）"); ax.grid(axis="y", color=GRID, lw=0.6)
ax.legend(frameon=False, loc="lower left", fontsize=9, ncol=3)
ax.set_title(f"2024年4月以降、営業用トラックは平均{main['yoy_mean_truck_comm_tkm_after']:+.1f}%、鉄道コンテナ{main['yoy_mean_rail_cont_tkm_after']:+.1f}%、内航{main['yoy_mean_ship_comm_tkm_after']:+.1f}%",
             loc="left", fontsize=12)
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.08, right=0.98)
foot(fig, "太い横線は2022年4月〜2024年3月と2024年4月〜2026年3月の平均。トンキロの前年同月比")
save(fig, "fig3_yoy_monthly.png")

# 図4：割合の変化を分子と分母に分ける
d = pd.read_csv(R / "share_decomp.csv")
sel = [("unit_vs_truckcomm", 2023, 2025, "ユニットロードの割合\n（分母：＋営業用トラック）\n2023→2025年度"),
       ("unit_vs_truckcomm", 2015, 2025, "同\n2015→2025年度"),
       ("railship_vs_truck", 2024, 2025, "鉄道＋内航の割合\n（分母：＋トラック全体）\n2024→2025年度"),
       ("railship_vs_truck", 2015, 2025, "同\n2015→2025年度")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for i, (nm, t0, t1, lab) in enumerate(sel):
    r = d[(d.share == nm) & (d["from"] == t0) & (d["to"] == t1)].iloc[0]
    ax.bar(i - 0.2, r.numerator_pt, 0.38, color=C["ship"], label="分子（船・鉄道の量）の寄与" if i == 0 else None)
    ax.bar(i + 0.2, r.denominator_pt, 0.38, color=C["truck"], label="分母（トラックの量）の寄与" if i == 0 else None)
    ax.plot([i - 0.42, i + 0.42], [r.change_pt] * 2, color="#1d1d1b", lw=2)
    ax.text(i, max(r.numerator_pt, r.denominator_pt, r.change_pt) + 0.25, f"変化 {r.change_pt:+.2f}pt", ha="center", fontsize=9, color=INK2)
ax.axhline(0, color=INK2, lw=0.7)
ax.set_xticks(range(len(sel))); ax.set_xticklabels([s[3] for s in sel], fontsize=8.8)
ax.set_ylabel("割合の変化（ポイント）"); ax.set_ylim(-6, 4.5); ax.grid(axis="y", color=GRID, lw=0.6)
ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.set_title("割合が上がった年度は、船・鉄道が増えたからではなく、トラックが減ったから", loc="left", fontsize=12.5)
fig.subplots_adjust(bottom=0.24, top=0.9, left=0.08, right=0.98)
foot(fig, "黒い横線は割合の変化の合計（分子の寄与＋分母の寄与）")
save(fig, "fig4_share_decomposition.png")
print("figures saved")
