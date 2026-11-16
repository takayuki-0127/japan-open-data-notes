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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "axes.unicode_minus": False})
KG1, KG2, KE1, KE2 = "#1f5fae", "#9cc3ec", "#d4561f", "#f4b48f"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「学校基本調査」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
ns = pd.read_csv(R / "national_series.csv", index_col=0)
bk = pd.read_csv(R / "completers_breakdown_2025.csv")
q = pd.read_csv(R / "prefecture_metrics.csv", index_col=0)

# ---- 図1：就園率の推移 -----------------------------------------------------------------------
s = ns.loc[2000:2025]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(s.index, s["kg_rate"], color=KG1, lw=2.2, marker="o", ms=3.5)
ke = s.loc[2016:]
ax.plot(ke.index, ke["ke_rate"], color=KE1, lw=2.2, marker="o", ms=3.5)
ax.plot(s.index, s["rate_sum"], color=INK2, lw=1.3, ls="--")
ax.axvline(2015, color=GRID, lw=6, zorder=0)
ax.text(2015.3, 63, "2015年：幼保連携型認定こども園ができる", color=INK2, fontsize=9, va="bottom")
ax.text(2025.3, s.loc[2025, "kg_rate"], f"幼稚園\n{s.loc[2025, 'kg_rate']:.1f}", color=KG1, va="center", fontsize=9.5)
ax.text(2025.3, s.loc[2025, "ke_rate"], f"こども園\n{s.loc[2025, 'ke_rate']:.1f}", color=KE1, va="center", fontsize=9.5)
ax.text(2025.3, s.loc[2025, "rate_sum"] + 2, f"合計\n{s.loc[2025, 'rate_sum']:.1f}", color=INK2, va="center", fontsize=9.5)
ax.text(2000, s.loc[2000, "kg_rate"] + 2.2, f"{s.loc[2000, 'kg_rate']:.1f}", color=KG1, fontsize=9)
ax.text(2014, s.loc[2014, "kg_rate"] + 2.2, f"{s.loc[2014, 'kg_rate']:.1f}", color=KG1, fontsize=9, ha="center")
ax.set_xlim(1999.5, 2028.5); ax.set_ylim(0, 70)
ax.set_ylabel("小学校等1年生100人あたりの修了者（人）")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_title("幼稚園と幼保連携型認定こども園の就園率（各年3月の修了者 ÷ その年の1年生）", fontsize=11, loc="left")
fig.text(0.01, 0.01, SRC + "（総括表 4 進学率）", fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig1_rates.png")

# ---- 図2：2014年と2025年の内訳 ---------------------------------------------------------------
H2 = main["H2"]
fig, ax = plt.subplots(figsize=(7.4, 4.8))
ax.bar(0, H2["kg_rate_2014"], color=KG1, width=0.55)
ax.text(0, H2["kg_rate_2014"] / 2, f"幼稚園\n{H2['kg_rate_2014']:.1f}", color="white", ha="center", va="center", fontsize=10)
bottom = 0
cols = [KG1, KG2, KE1, KE2]
txtc = ["white", INK, "white", INK]
for (_, r), c, tc in zip(bk.iterrows(), cols, txtc):
    v = r["per100_2025"]
    ax.bar(1, v, bottom=bottom, color=c, width=0.55)
    ax.text(1.32, bottom + v / 2, f"{r['part']}  {v:.1f}", va="center", fontsize=9.5, color=INK)
    bottom += v
ax.text(0, H2["kg_rate_2014"] + 1.2, f"計 {H2['kg_rate_2014']:.1f}", ha="center", fontsize=9.5)
ax.text(1, bottom + 1.2, f"計 {bottom:.1f}", ha="center", fontsize=9.5)
edu = H2["robust_exclude_kg_n2"]["edu_type_rate"]
ax.text(1.32, 58, f"1号（教育の時間だけ）は\n幼稚園＋こども園で {edu:.1f}", fontsize=9.5, color=INK, va="center",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=GRID))
ax.set_xticks([0, 1]); ax.set_xticklabels(["2014年3月の修了者", "2025年3月の修了者"])
ax.set_xlim(-0.6, 2.4); ax.set_ylim(0, 66)
ax.set_ylabel("小学校等1年生100人あたり（人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("幼稚園・こども園を出た子の内訳（1号＝教育標準時間認定、2号＝保育認定）", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC + "。\n2025年の1号・2号の分け方は推計（こども園は2024年5月の5歳、幼稚園は2025年5月の5歳の割合を使った）", fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.06, 1, 1))
save(fig, "fig2_breakdown.png")

# ---- 図3：都道府県の散布図 -------------------------------------------------------------------
H3 = main["H3"]
fig, ax = plt.subplots(figsize=(7.2, 5.2))
ax.scatter(q["ke_n1_share"], q["kg_decline_pct"], s=34, color=KE1, alpha=0.85, edgecolor="white", lw=0.6)
xx = np.array([0, 75])
ax.plot(xx, H3["ols_intercept"] + H3["ols_slope"] * xx, color=INK2, lw=1, ls="--")
ax.text(2, 86,
        f"順位相関 {H3['spearman']:.2f}\n（47都道府県）", fontsize=9.5, color=INK2)
ax.set_xlim(0, 75); ax.set_ylim(30, 95)
ax.set_xlabel("2025年：教育の時間だけ通う3〜5歳（1号）のうち、こども園にいる割合（%）")
ax.set_ylabel("幼稚園の在園者の減り方 2014→2025年（%）")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("1号の子がこども園に多くいる都道府県ほど、幼稚園の在園者が大きく減った", fontsize=10.5, loc="left")
fig.text(0.01, 0.01, SRC + "。点は都道府県（名前は付けない）", fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
save(fig, "fig3_pref_scatter.png")

# ---- 図4：都道府県の内訳（北から南） --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 11))
y = np.arange(len(q))[::-1]
left = np.zeros(len(q))
labs = [("sh_kg_n1", KG1, "幼稚園 1号"), ("sh_kg_n2", KG2, "幼稚園 2号"),
        ("sh_ke_n1", KE1, "こども園 1号"), ("sh_ke_n2", KE2, "こども園 2号")]
for c, col, lab in labs:
    ax.barh(y, q[c].values, left=left, color=col, height=0.78, label=lab)
    left += q[c].values
ax.set_yticks(y); ax.set_yticklabels(q.index, fontsize=9)
ax.set_xlim(0, 100); ax.set_ylim(-0.7, len(q) - 0.3)
ax.set_xlabel("2025年の3〜5歳の在園者（幼稚園＋幼保連携型認定こども園）に占める割合（%）")
ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=9.5)
ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
ax.set_title("都道府県ごとの内訳（北から南の順）", fontsize=11, loc="left", pad=26)
fig.text(0.01, 0.006, SRC + "（3〜5歳・認定区分別の表）", fontsize=8, color=INK2)
fig.tight_layout(rect=(0, 0.015, 1, 1))
save(fig, "fig4_pref_composition.png")
print("figures done")
