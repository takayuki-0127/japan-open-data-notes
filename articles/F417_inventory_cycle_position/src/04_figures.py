"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7d5ba6"]
PH_C = {"回復": "#1baf7a", "積み増し": "#2a78d6", "積み上がり": "#eb6834", "調整": "#7d5ba6"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：経済産業省「鉱工業生産・出荷・在庫指数」（e-Stat）、内閣府「景気基準日付」をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
d = pd.read_csv(R / "quarterly_cycle.csv", index_col=0)


def finish(fig, ax, title, grid="both", bottom=0.14):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.015, SRC, fontsize=7.4, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def qlabel(q):
    return f"{q[:4]}年{ {'1':'1〜3','2':'4〜6','3':'7〜9','4':'10〜12'}[q[-1]] }月期"


# 図1：在庫循環図（2012〜2026年。2009〜2011年は枠が広がるので除く）
fig, ax = plt.subplots(figsize=(8.0, 6.6))
s = d[d.index >= "2012Q1"]
lim_x, lim_y = (-8, 12), (-11, 13)
ax.axhline(0, color=INK2, lw=0.9); ax.axvline(0, color=INK2, lw=0.9)
ax.plot([-20, 20], [-20, 20], color=INK2, lw=0.9, ls="--")
ax.text(9.0, 10.6, "45度線", color=INK2, fontsize=9)
xs = s.x.clip(*lim_x); ys = s.y.clip(*lim_y)
ax.plot(xs, ys, color="#b9b8b3", lw=0.9, zorder=1)
for q, a, b, ph, rc in zip(s.index, xs, ys, s.phase, s.recession):
    ax.scatter(a, b, s=46 if rc else 26, color=PH_C[ph], edgecolor=INK if rc else "none", lw=1.1, zorder=3)
for ph, (tx, ty) in {"回復": (6.2, -9.8), "積み増し": (8.0, 2.0), "積み上がり": (-7.4, 11.4), "調整": (-7.4, -9.8)}.items():
    ax.text(tx, ty, ph, color=PH_C[ph], fontsize=11, fontweight="bold")
last = m["latest"]["quarter"]
ax.annotate(f"直近：{qlabel(last)}\n出荷 {m['latest']['x']:+.1f}%・在庫 {m['latest']['y']:+.1f}%", (d.x[last], d.y[last]),
            xytext=(4.3, 5.8), fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK, lw=0.8))
for q, txt, off in [("2018Q4", "2018年10〜12月期（山）", (-7.6, 7.6)), ("2012Q1", "2012年1〜3月期（山）", (6.0, 12.3))]:
    ax.annotate(txt, (d.x[q], d.y[q]), xytext=off, fontsize=8.6, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
ax.scatter([], [], s=46, color="white", edgecolor=INK, lw=1.1, label="黒い縁：景気の後退期")
ax.legend(frameon=False, fontsize=8.6, loc="lower right", bbox_to_anchor=(1.0, 0.08))
ax.set_xlim(*lim_x); ax.set_ylim(*lim_y)
ax.set_xlabel("出荷の前年同期比（%）")
ax.set_ylabel("在庫（期末）の前年同期比（%）")
ax.text(-7.8, -10.8, "2020年4〜6月期〜2021年4〜6月期は枠の外の値を端に寄せた", fontsize=7.8, color=INK2)
finish(fig, ax, "鉱工業の在庫循環図（2012年1〜3月期〜2026年7〜9月期）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.12)
save(fig, "fig1_cycle_diagram.png")

# 図2：局面の帯と景気の後退期（2009〜2026年）
fig, ax = plt.subplots(figsize=(9.0, 4.6))
xpos = np.arange(len(d))
ax.bar(xpos, d.x - d.y, color=[PH_C[p] for p in d.phase], width=0.85)
for i, rc in enumerate(d.recession):
    if rc:
        ax.axvspan(i - 0.5, i + 0.5, color="#d9d8d3", alpha=0.6, zorder=0)
ax.axhline(0, color=INK2, lw=0.8)
ticks = [i for i, q in enumerate(d.index) if q.endswith("Q1") and int(q[:4]) % 2 == 1]
ax.set_xticks(ticks); ax.set_xticklabels([d.index[i][:4] for i in ticks])
ax.set_ylim(-32, 38)
ax.set_ylabel("出荷の伸び − 在庫の伸び（%pt）")
hd = [Patch(color=PH_C[ph], label=ph) for ph in ["回復", "積み増し", "積み上がり", "調整"]] + [Patch(color="#d9d8d3", label="景気の後退期")]
ax.legend(handles=hd, frameon=False, fontsize=8.6, ncol=5, loc="upper right")
ax.text(len(d) - 1, -30.5, "2020年7〜9月期以降は景気の山が未定", fontsize=8, color=INK2, ha="right")
finish(fig, ax, f"後退期の{m['H1_rec_in_upper_or_adjust_pct']}%は「積み上がり・調整」。ただし拡張期にも多い", grid="y")
fig.subplots_adjust(left=0.09, right=0.98, top=0.88, bottom=0.12)
save(fig, "fig2_phase_timeline.png")

# 図3：業種別の局面（2014〜2026年、業種は統計の並び順）
ic = pd.read_csv(R / "industry_cycle.csv")
inds = list(m["industry"]["same_by_industry"].keys())
qs = sorted(ic.quarter.unique())
code = {"回復": 0, "積み増し": 1, "積み上がり": 2, "調整": 3}
mat = np.full((len(inds) + 1, len(qs)), np.nan)
tot = d.phase.reindex(qs)
for j, q in enumerate(qs):
    mat[0, j] = code[tot[q]]
for i, n in enumerate(inds):
    s_ = ic[ic.industry == n].set_index("quarter").phase
    for j, q in enumerate(qs):
        if q in s_.index:
            mat[i + 1, j] = code[s_[q]]
fig, ax = plt.subplots(figsize=(9.6, 6.2))
cmap = ListedColormap([PH_C[k] for k in ["回復", "積み増し", "積み上がり", "調整"]])
ax.imshow(mat, aspect="auto", cmap=cmap, vmin=-0.5, vmax=3.5, interpolation="nearest")
ax.axhline(0.5, color="white", lw=3)
ax.set_yticks(range(len(inds) + 1)); ax.set_yticklabels(["鉱工業（全体）"] + [n.replace("工業", "") if n != "鉱業" else n for n in inds], fontsize=8.6)
tk = [j for j, q in enumerate(qs) if q.endswith("Q1") and int(q[:4]) % 2 == 0]
ax.set_xticks(tk); ax.set_xticklabels([qs[j][:4] for j in tk])
hd = [Patch(color=PH_C[ph], label=ph) for ph in ["回復", "積み増し", "積み上がり", "調整"]]
ax.legend(handles=hd, frameon=False, fontsize=8.6, ncol=4, loc="upper left", bbox_to_anchor=(0.0, -0.06))
for sp in ax.spines.values():
    sp.set_visible(False)
finish(fig, ax, f"全体と同じ局面にいる業種は平均{m['industry']['sync_mean_pct']}%。直近は回復・積み上がり・調整が5業種ずつ", grid=None)
fig.subplots_adjust(left=0.2, right=0.98, top=0.9, bottom=0.16)
save(fig, "fig3_industry_phases.png")

# 図4：後退期を見分ける力（AUC）：出荷の伸びだけ と 出荷−在庫
rb = m["robustness"]
labs = list(rb.keys())
fig, ax = plt.subplots(figsize=(8.6, 4.8))
y = np.arange(len(labs))[::-1]
for yi, k in zip(y, labs):
    ax.plot([rb[k]["auc_x"], rb[k]["auc_gap"]], [yi, yi], color=GRID, lw=3, zorder=1)
ax.scatter([rb[k]["auc_x"] for k in labs], y, color=C[0], s=36, zorder=2, label="出荷の伸びだけ")
ax.scatter([rb[k]["auc_gap"] for k in labs], y, color=C[1], s=36, zorder=3, label="出荷の伸び − 在庫の伸び")
ax.axvline(0.5, color=INK2, lw=0.9, ls=":")
ax.text(0.505, y[0] + 0.25, "0.5＝当てずっぽう", fontsize=8.4, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8.8)
ax.set_xlim(0.45, 0.85)
ax.set_xlabel("景気の後退期を見分ける力（AUC）")
ax.legend(frameon=False, fontsize=8.8, loc="lower right")
finish(fig, ax, "在庫を足しても、後退期を見分ける力はほとんど上がらない", grid="x")
fig.subplots_adjust(left=0.33, right=0.97, top=0.88, bottom=0.15)
save(fig, "fig4_auc_checks.png")
print("figures done")
