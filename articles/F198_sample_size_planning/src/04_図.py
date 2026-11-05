"""04 図：5枚。"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA, RES, FIG, n_margin, n_cv

plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
C1, C2, C3, C4, GR = "#2a6f97", "#e07a5f", "#81b29a", "#9c6644", "#888888"
S = json.load(open(RES / "summary.json"))

# 1. 必要な人数と割合 p
p = np.logspace(np.log10(0.005), np.log10(0.5), 200)
fig, ax = plt.subplots(figsize=(8, 5))
for e, c in ((0.01, C1), (0.03, C3), (0.05, C2)):
    ax.plot(p * 100, n_margin(p, e), color=c, lw=2, label=f"誤差の幅 ±{int(e*100)}ポイント")
for cv, ls in ((0.05, "--"), (0.10, ":")):
    ax.plot(p * 100, n_cv(p, cv), color=C4, lw=2, ls=ls, label=f"標準誤差率 {int(cv*100)}%（割合に対する相対）")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xticks([0.5, 1, 2.5, 5, 10, 25, 50]); ax.set_xticklabels(["0.5", "1", "2.5", "5", "10", "25", "50"])
ax.set_xlabel("推定したい割合 p（%）"); ax.set_ylabel("必要な人数（単純無作為、95%）")
ax.set_title("同じ「精度」でも、決め方で必要な人数は100倍ちがう")
ax.legend(fontsize=9, frameon=False, loc="upper right")
ax.grid(alpha=0.3, which="both")
fig.tight_layout(); fig.savefig(FIG / "f198_01_required_n.png"); plt.close(fig)

# 2. 実際の標本の大きさと、区分の数で要る人数
sv = pd.read_csv(DATA / "survey_designs.csv")
sv["n_use"] = sv.persons_or_units.fillna(sv.households)
lab = [s + ("（世帯）" if np.isnan(r) else "") for s, r in zip(sv.statistic, sv.persons_or_units)]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
y = np.arange(len(sv))[::-1]
ax.barh(y, sv.n_use, color=C1, alpha=0.85)
for yy, v in zip(y, sv.n_use):
    ax.text(v * 1.08, yy, f"{v/1e4:.1f}万" if v >= 1e4 else f"{v:,.0f}", va="center", fontsize=9)
for D, c, nm in ((1, C3, "全国だけ"), (11, C2, "11の地域ごと"), (47, C4, "47都道府県ごと")):
    v = D * n_margin(0.5, 0.01, 1.5)
    ax.axvline(v, color=c, ls="--", lw=1.5)
    ax.text(v * 1.06, -0.62, f"{nm} {v/1e4:.1f}万", color=c, fontsize=8.5, ha="left", va="center",
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9.5)
ax.set_xscale("log"); ax.set_xlim(3e3, 4e6); ax.set_ylim(-0.95, len(sv) - 0.5)
ax.set_xlabel("標本の大きさ（人・企業。家計調査は世帯）")
ax.set_title("点線：割合50%を±1ポイントで出すのに要る人数（設計効果1.5を仮定）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f198_02_surveys.png"); plt.close(fig)

# 3. 労働力調査：公表の標準誤差と単純無作為の比較
B = pd.read_csv(RES / "B_lfs_deff_by_size.csv")
mi = pd.read_csv(RES / "B_lfs_main_items_neff.csv")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axs[0]
ax.plot(B.size_10k, B.monthly_se_10k, "o-", color=C2, label="公表の標準誤差（月次）")
ax.plot(B.size_10k, B.srs_monthly_10k, "s--", color=C1, label="同じ10万人の単純無作為")
for x, yv, d in zip(B.size_10k, B.monthly_se_10k, B.deff_monthly):
    ax.text(x, yv * 1.12, f"{d:.2f}", fontsize=8, ha="center", color=C2)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("推定値の大きさ（万人）"); ax.set_ylabel("標準誤差（万人）")
ax.set_title("数字は設計効果（分散の比）", fontsize=11)
ax.legend(fontsize=9, frameon=False)
ax = axs[1]
m = mi.sort_values("neff_annual")
cols = [C2 if v < 250000 else C1 for v in m.neff_annual]
ax.barh(m.item, m.neff_annual / 1e4, color=cols)
ax.axvline(S["lfs_neff_annual_median"] / 1e4, color=GR, ls="--", lw=1)
ax.text(S["lfs_neff_annual_median"] / 1e4, -1.2, "大きさ別の表の中央値", fontsize=8, color=GR, ha="center")
ax.set_xlabel("年平均の「単純無作為なら何人分か」（万人）")
ax.tick_params(axis="y", labelsize=8)
ax.set_title("項目によって有効な人数は5倍ちがう（2025年平均）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f198_03_lfs_deff.png"); plt.close(fig)

# 4. 失業率の月々の変化を見分けるには
cv = pd.read_csv(RES / "C_mdc_curve.csv")
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.plot(cv.n_labor / 1e4, cv["mdc_pt_rho0.0"], color=C1, lw=2, label="2か月の標本が独立")
ax.plot(cv.n_labor / 1e4, cv["mdc_pt_rho0.5"], color=C3, lw=2, ls="--", label="推定値の相関0.5（標本の重なりを仮定）")
ax.axvline(S["nL"] / 1e4, color=C2, lw=1.5)
ax.text(S["nL"] / 1e4 * 1.05, 0.9, f"いまの労働力人口の標本\n約{S['nL']/1e4:.1f}万人", color=C2, fontsize=9)
for d in (0.1, 0.2, 0.3):
    ax.axhline(d, color=GR, lw=0.6, ls=":")
ax.set_xscale("log"); ax.set_ylim(0, 1.0)
ax.set_xlabel("毎月の標本のうち労働力人口（万人）"); ax.set_ylabel("見分けられる変化（ポイント）")
ax.set_title("失業率（約2.5%）の前月差を検出力80%で見分けられる大きさ", fontsize=11)
ax.legend(fontsize=9, frameon=False)
fig.tight_layout(); fig.savefig(FIG / "f198_04_change.png"); plt.close(fig)

# 5. シミュレーション
E = pd.read_csv(RES / "E_simulation.csv")
E["case"] = E.apply(lambda r: f"p={r.p:g}\n" + (f"±{r.target[3:]}" if r.target.startswith("abs") else f"率{float(r.target[2:])*100:g}%"), axis=1)
cases = E.case.unique()
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=False)
x = np.arange(len(cases)); w = 0.38
for ax, col, ttl in ((axs[0], "share_within_target", "狙った誤差の幅に入った割合"), (axs[1], "wald_coverage", "95%区間（正規近似）が本当の値を含んだ割合")):
    a = E[E.label == "式の人数"].set_index("case").loc[cases, col]
    b = E[E.label == "式の1/4"].set_index("case").loc[cases, col]
    ax.bar(x - w / 2, a * 100, w, color=C1, label="式どおりの人数")
    ax.bar(x + w / 2, b * 100, w, color=C2, label="その1/4の人数")
    ax.axhline(95, color=GR, ls="--", lw=1)
    ax.set_xticks(x); ax.set_xticklabels(cases, fontsize=8.5)
    ax.set_ylim(50, 100); ax.set_ylabel("%"); ax.set_title(ttl, fontsize=11)
axs[0].legend(fontsize=9, frameon=False, loc="upper center", bbox_to_anchor=(1.1, -0.13), ncol=2)
fig.suptitle("2万回のくり返し：式どおりなら狙いどおり。ただし p=1% では区間がずれる", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f198_05_simulation.png"); plt.close(fig)
print("ok")
