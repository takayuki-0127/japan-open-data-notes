"""F202 図1〜6"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RAW, DATA, RES, FIG, setup_font

setup_font()
C1, C2, C3, CG = "#2b6cb0", "#dd6b20", "#2f855a", "#718096"
M = json.load(open(RES / "main.json", encoding="utf-8"))

# 図1 年収の壁を「週の時間」に直すと
nat = pd.read_csv(RES / "wall_hours_national.csv")
nat = nat[nat.year >= 2005]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].plot(nat.year, nat.mw_wavg, color=C1, marker="o", ms=3)
ax[0].set_title("最低賃金（全国加重平均、年度）")
ax[0].set_ylabel("円")
ax[1].plot(nat.year, nat.h_week_1056000, color=C2, marker="o", ms=3, label="106万円（月8.8万円）")
ax[1].plot(nat.year, nat.h_week_1300000, color=C3, marker="o", ms=3, label="130万円")
ax[1].axhline(20, color=CG, ls="--", lw=1)
ax[1].text(2005.3, 20.4, "週20時間", color=CG, fontsize=9)
ax[1].set_title("最低賃金で働くと、壁の手前に収まる週の時間")
ax[1].set_ylabel("時間／週（52週で割った値）")
ax[1].legend(frameon=False)
for a in ax:
    a.grid(alpha=.3)
fig.suptitle("図1 最低賃金が上がるほど、壁の手前で働ける時間は短くなった", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "fig1_wall_hours.png", dpi=150)
plt.close(fig)

# 図2 20時間の線：月8.8万円に届く週の時間（県）
cnt = pd.read_csv(RES / "pref_over_20h_line.csv")
cnt = cnt[cnt.year >= 2015]
ph = pd.read_csv(RES / "pref_hours_2026.csv").sort_values("h_week_for_88k")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].bar(cnt.year, cnt.n_pref_over_20hline, color=C1)
ax[0].set_title("最低賃金が 1,016円以上の県の数（週20時間で月8.8万円を超える）", fontsize=10)
ax[0].set_ylabel("県の数（47）")
ax[0].set_ylim(0, 50)
for x, y in zip(cnt.year, cnt.n_pref_over_20hline):
    ax[0].text(x, y + 0.8, str(y), ha="center", fontsize=8)
ax[1].scatter(ph.h_week_for_88k, np.arange(len(ph)), color=C2, s=14)
ax[1].axvline(20, color=CG, ls="--", lw=1)
ax[1].set_yticks([])
ax[1].set_xlabel("月8.8万円に届く週の時間（2026年度の最低賃金）")
ax[1].set_title("47都道府県（1点が1県、並びは時間の短い順）")
ax[1].text(20.1, 2, "週20時間", color=CG, fontsize=9)
for a in ax:
    a.grid(alpha=.3)
fig.suptitle("図2 2025年度からは全県で「週20時間」働けば月8.8万円を超える", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "fig2_20h_line.png", dpi=150)
plt.close(fig)

# 図3 2017年と2022年：集積の大きさ・就業調整の割合・壁の手前の時間
b = M["f82_b_married_women"]
adj = M["adjust_national"]
wh = M["wall_hours"]
items = [("有配偶の女性の集積の大きさ b\n（F82、50〜149万円）", b["2017"], b["2022"], ""),
         ("非正規の女性で\n就業調整をしている割合", adj["2017_F"], adj["2022_F"], "%"),
         ("非正規の男性で\n就業調整をしている割合", adj["2017_M"], adj["2022_M"], "%"),
         ("130万円の手前に収まる\n週の時間（最低賃金）", wh["2017"]["h130"], wh["2022"]["h130"], "時間")]
fig, ax = plt.subplots(1, 4, figsize=(12, 3.8))
for a, (t, v1, v2, u) in zip(ax, items):
    a.bar([0, 1], [v1, v2], color=[CG, C1], width=0.6)
    a.set_xticks([0, 1], ["2017", "2022"])
    a.set_title(t, fontsize=10)
    for x, v in zip([0, 1], [v1, v2]):
        a.text(x, v * 1.01, f"{v:.2f}{u}" if u == "" else f"{v:.1f}{u}", ha="center", fontsize=9)
    a.set_ylim(0, max(v1, v2) * 1.2)
    a.grid(axis="y", alpha=.3)
fig.suptitle("図3 2017→2022年：壁の手前の時間は12%短くなり、集積と就業調整は少し減った（2時点だけ）", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "fig3_two_points.png", dpi=150)
plt.close(fig)

# 図4 県の就業調整の割合と最低賃金
pa = pd.read_csv(DATA / "panel_adjust.csv")
fig, ax = plt.subplots(1, 3, figsize=(12.5, 4.2))
for a, sex, col, t in [(ax[0], "F", C2, "女性・2022年"), (ax[1], "M", C1, "男性・2022年（比べる相手）")]:
    d = pa[(pa.year == 2022) & (pa.sex == sex)]
    a.scatter(d.mw, d.share_adj, s=d.tot_all / d.tot_all.max() * 220 + 8, color=col, alpha=.55)
    a.set_xlabel("最低賃金（2022年度、円）")
    a.set_ylabel("非正規のうち就業調整をしている割合（%）")
    r = np.corrcoef(d.mw, d.share_adj)[0, 1]
    a.set_title(f"{t}　相関 {r:.2f}", fontsize=10)
    a.grid(alpha=.3)
a0 = pa[(pa.year == 2017) & (pa.sex == "F")].set_index("code")
a1 = pa[(pa.year == 2022) & (pa.sex == "F")].set_index("code")
dx = 100 * (a1.lmw - a0.lmw)
dy = a1.share_adj - a0.share_adj
ax[2].scatter(dx, dy, color=C3, alpha=.6, s=20)
ax[2].axhline(0, color=CG, lw=1)
ax[2].set_xlabel("最低賃金の上がり方 2017→2022（%、対数差）")
ax[2].set_ylabel("就業調整の割合の変化（ポイント）")
ax[2].set_title(f"女性・変化　相関 {np.corrcoef(dx, dy)[0,1]:.2f}", fontsize=10)
ax[2].grid(alpha=.3)
fig.suptitle("図4 最低賃金の高い県ほど就業調整の割合は高いが、男性も同じ形。上がり方の差とは関係が見えない", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "fig4_adjust_pref.png", dpi=150)
plt.close(fig)

# 図5 全国一律にすると、各県の最低賃金は何%上がるか
pi = pd.read_csv(RES / "scenario_pref_increase.csv")
levels = list(M["scenario_summary"].keys())
fig, ax = plt.subplots(figsize=(10, 4.4))
for i, L in enumerate(levels):
    d = pi[pi.level == L]
    over = d.kaitz_new > M["kaitz_obs_max"]
    jit = np.random.default_rng(1).uniform(-0.18, 0.18, len(d))
    ax.scatter(d.pct_up[~over], i + jit[~over], color=C1, s=16, alpha=.7, label="これまでに観測された範囲の中" if i == 0 else None)
    ax.scatter(d.pct_up[over], i + jit[over], color=C2, s=16, alpha=.8, marker="^", label="カイツ指標がこれまでの最大を超える" if i == 0 else None)
ax.set_yticks(range(len(levels)), [l.replace("にそろえる", "\nにそろえる") for l in levels])
ax.set_xlabel("2026年度の最低賃金からの引き上げ幅（%、1点が1県）")
ax.grid(alpha=.3)
ax.legend(frameon=False, loc="lower right")
fig.suptitle("図5 1,500円にそろえると、ほとんどの県がこれまでに観測した範囲の外に出る", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "fig5_uniform_increase.png", dpi=150)
plt.close(fig)

# 図6 雇用の変化の幅（前提を振った幅）
sc = pd.read_csv(RES / "scenario_uniform.csv")
fig, ax = plt.subplots(figsize=(10, 4.6))
for i, L in enumerate(levels):
    s = sc[sc.level == L]
    mb = s[s.elast_name.str.contains("方法の幅")]
    ax.plot([s.d_emp_10k.min(), s.d_emp_10k.max()], [i, i], color=CG, lw=2, label="95%区間の端まで振った幅" if i == 0 else None)
    ax.plot([mb.d_emp_10k.min(), mb.d_emp_10k.max()], [i, i], color=C1, lw=8, solid_capstyle="butt", label="4つの方法の推定の幅" if i == 0 else None)
    ax.scatter([s.d_emp_10k_nonlinear.min()], [i], color=C2, marker="x", s=50, zorder=5, label="範囲外で効き方が2倍なら" if i == 0 else None)
ax.axvline(0, color="k", lw=0.8)
mde = M["mde_people_at1500_10k"]
ax.axvspan(-mde, mde, color=C3, alpha=.08)
ax.set_ylim(-0.5, len(levels) - 0.3)
ax.text(-mde + 5, len(levels) - 0.5, f"緑の帯：1,500円のとき、今のデータで見分けられる最小の差（±{mde:.0f}万人）", fontsize=8, color=C3)
ax.set_yticks(range(len(levels)), [l.replace("にそろえる", "\nにそろえる") for l in levels])
ax.set_xlabel("就業者の変化（万人、2025年の就業者 約6,840万人に対して）")
ax.grid(alpha=.3)
ax.legend(frameon=False, loc="lower left", fontsize=8)
fig.suptitle("図6 全国一律の雇用への影響は「0〜数百万人減」まで幅が広く、ひとつの数字には決まらない", x=0.01, ha="left", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "fig6_scenario_band.png", dpi=150)
plt.close(fig)
print("ok")
