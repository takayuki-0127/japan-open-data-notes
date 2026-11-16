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
SRC = "出典：文部科学省「公立学校教員採用選考試験の実施状況」（各年度）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
lt = pd.read_csv(ROOT / "data" / "long_term.csv")
lt["ratio"] = lt.applicants / lt.hires
dc = pd.read_csv(R / "decomposition.csv")
pv = pd.read_csv(R / "requestion_prior_vs_not_hired.csv")

# ---- 図1：倍率の長い流れ -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for ty, c in [("中学校", C[1]), ("高等学校", C[2]), ("小学校", C[0]), ("計", INK2)]:
    q = lt[lt.type == ty]
    ax.plot(q.year, q.ratio, color=c, lw=2.4 if ty == "小学校" else 1.6, ls="--" if ty == "計" else "-")
    yv = float(q.ratio.iloc[-1]); off = {"中学校": 0.2, "高等学校": 0.9, "小学校": -0.6, "計": -0.15}[ty]
    ax.text(2025.6, yv + off, f"{'全体' if ty == '計' else ty} {yv:.1f}倍", fontsize=9, color=INK, va="center")
q = lt[lt.type == "小学校"].set_index("year")
ax.plot([2000], [q.loc[2000, "ratio"]], "o", color=C[0], ms=7, mec="#fcfcfb", mew=2)
ax.text(2000, q.loc[2000, "ratio"] + 0.6, f"小学校 2000年度 {q.loc[2000,'ratio']:.1f}倍", ha="center", fontsize=9, color=INK)
ax.set_xlim(1978, 2033); ax.set_ylim(0, 19.5)
ax.set_ylabel("倍率（受験者÷採用者）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"小学校の倍率は2000年度の{q.loc[2000,'ratio']:.1f}倍から2025年度の{q.loc[2025,'ratio']:.1f}倍に", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：公立学校の教員採用選考。年度は採用の年度（試験はその前の年）。全体は養護教諭・栄養教諭を含む。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_ratio_long.png")

# ---- 図2：小学校の受験者と採用者 -------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(q.index, q.applicants / 1e4, color=C[0], lw=2, label="受験者")
ax.plot(q.index, q.hires / 1e4, color=C[1], lw=2, label="採用者")
for y in [2000, 2012, 2025]:
    ax.axvline(y, color=GRID, lw=1, zorder=0)
for y, col, dy in [(2000, "applicants", 0.35), (2012, "applicants", 0.35), (2025, "applicants", 0.35), (2000, "hires", 0.3), (2012, "hires", 0.35), (2025, "hires", 0.35)]:
    v = q.loc[y, col] / 1e4
    ax.text(y, v + dy, f"{v:.1f}万", ha="center", fontsize=8.8, color=INK)
ax.text(2006, 7.3, "前半：採用者が\n3.7倍に", ha="center", fontsize=9, color=INK2)
ax.text(2018.5, 7.3, "後半：受験者が\n4割減", ha="center", fontsize=9, color=INK2)
ax.legend(loc="lower left", frameon=False)
ax.set_xlim(1978, 2026.5); ax.set_ylim(0, 8.2)
ax.set_ylabel("人数（万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("小学校：2000→12年度は採用者が増え、2012→25年度は受験者が減った", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：公立小学校。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig2_elem_applicants_hires.png")

# ---- 図3：小学校の新卒・既卒の受験者と、前の年に採用されなかった人 -----------------------
p = pv[pv.type == "小学校"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(p.year, p.not_hired_prev / 1e4, color=INK2, lw=1.6, ls="--", label=f"前の年度の受験者−採用者（採用されなかった人）：{p.not_hired_prev.iloc[0]:,.0f}→{p.not_hired_prev.iloc[-1]:,.0f}")
ax.plot(p.year, p["既卒"] / 1e4, color=C[1], lw=2.2, marker="o", ms=4, label=f"既卒の受験者：{p['既卒'].iloc[0]:,.0f}→{p['既卒'].iloc[-1]:,.0f}")
ax.plot(p.year, p["新卒"] / 1e4, color=C[0], lw=2.2, marker="o", ms=4, label=f"新卒の受験者：{p['新卒'].iloc[0]:,.0f}→{p['新卒'].iloc[-1]:,.0f}")
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_xlim(2011.5, 2025.5); ax.set_ylim(0, 5)
ax.set_xticks(range(2012, 2026, 2))
ax.set_ylabel("人数（万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("小学校：減ったのは既卒の受験者。前の年に採用されなかった人の数と一緒に減った", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：2012年度・2021年度は次の年度の表の前年度の欄。新卒・既卒の表は一部の市を含まない年があり、図2の受験者とは少し違う。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig3_elem_new_prior.png")

# ---- 図4：倍率の変化の分解（対数） -------------------------------------------------------
types = ["小学校", "中学校", "高等学校", "計"]
fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.8), sharey=True)
for ax, per, ttl in [(axes[0], "前半（倍率の山→受験者の山）", "前半：倍率の山 → 受験者の山"), (axes[1], "後半（受験者の山→2025）", "後半：受験者の山 → 2025年度")]:
    z = dc[dc.period == per].set_index("type").loc[types]
    yy = np.arange(len(types))[::-1]
    ca = z.share_applicants * z.dlogR; ch = z.share_hires * z.dlogR
    ax.barh(yy + 0.18, ca, height=0.34, color=C[0], label="受験者の変化の分")
    ax.barh(yy - 0.18, ch, height=0.34, color=C[1], label="採用者の変化の分")
    for y_, (t, r) in zip(yy, z.iterrows()):
        ax.text(-1.47, y_ + 0.43, f"{int(r.start)}→{int(r.end)}年度　{r.ratio_start:.1f}倍→{r.ratio_end:.1f}倍", fontsize=8.2, color=INK2, va="center")
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlim(-1.5, 0.6)
    ax.set_title(ttl, loc="left", fontsize=11)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_xlabel("倍率の変化（対数）への寄与　左ほど倍率を下げた")
axes[0].set_yticks(np.arange(len(types))[::-1]); axes[0].set_yticklabels(["小学校", "中学校", "高等学校", "全体"])
h_, l_ = axes[1].get_legend_handles_labels()
fig.legend(h_, l_, loc="upper right", frameon=False, fontsize=9, ncol=2, bbox_to_anchor=(0.98, 0.99))
fig.suptitle("前半は採用者の増加、後半は受験者の減少が倍率を下げた", x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：ln(倍率の比) ＝ ln(受験者の比) − ln(採用者の比)。区切りの年は校種ごとに、1990年度以降の倍率の山と、その後の受験者の山。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.17, wspace=0.08)
save(fig, "fig4_decomposition.png")
print("figures ok")
