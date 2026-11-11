"""04 図：6枚。都道府県の名前は図に出さない（悪い順の並びにしないため）。"""
import json, pathlib, itertools
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 150})
B = pathlib.Path(__file__).resolve().parents[1]; F = B / "figures"; F.mkdir(exist_ok=True)
R = json.load(open(B / "results" / "main.json"))
lv = pd.read_csv(B / "results" / "A_levels_fy2017_2024.csv", index_col=0)
C1, C2, C3, GR = "#2b6cb0", "#dd6b20", "#2f855a", "#888888"

# 図1 料率の水準 vs 保険金の水準
fig, ax = plt.subplots(figsize=(7.2, 5.6))
x, y = np.log(lv.C), np.log(lv.R)
ax.scatter(lv.C, lv.R, s=45, color=C1, alpha=.6, edgecolor="white")
cx = np.exp(np.average(x)); cy = np.exp(np.average(y)); xs = np.exp(np.linspace(x.min() - .1, x.max() + .1, 50))
ax.plot(xs, cy * (xs / cx) ** 1, color=GR, ls="--", lw=1.2, label="保険金の差がそのまま料率に出る線（傾き1）")
b = R["main"]["slope_b"]; a = y.mean() - b * x.mean()
ax.plot(xs, np.exp(a) * xs ** b, color=C2, lw=2, label=f"実際の当てはめ（傾き{b:.2f}）")
ax.set_xscale("log"); ax.set_yscale("log")
for axis in (ax.xaxis, ax.yaxis):
    axis.set_major_locator(matplotlib.ticker.FixedLocator([0.5, 0.7, 1, 1.5, 2, 3, 4, 5])); axis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%g")); axis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_xlabel("保険金の水準：支払保険金 ÷ 新契約の保険金額（1,000円あたり、円）"); ax.set_ylabel("料率の水準：保険料 ÷ 保険金額（1,000円あたり、円）")
ax.set_title("住宅の火災保険：47都道府県の料率と保険金（2017〜2024年度の合計）", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.text(0.99, 0.02, f"順位相関 {R['main']['spearman']:.2f}", transform=ax.transAxes, ha="right", fontsize=9, color=GR)
fig.tight_layout(); fig.savefig(F / "fig1_rate_vs_claims.png"); plt.close()

# 図2 長期の損害率の分布
fig, ax = plt.subplots(figsize=(7.2, 3.8))
L = np.sort(lv.L.values)
ax.scatter(L, np.random.default_rng(1).uniform(-.25, .25, len(L)), color=C1, alpha=.7, s=40)
ax.axvline(R["main"]["national_L"], color=C2, lw=2); ax.text(R["main"]["national_L"], .33, f" 全国 {R['main']['national_L']*100:.0f}%", color=C2, fontsize=10)
q = R["main"]["L_iqr"]; ax.axvspan(q[0], q[2], color=C1, alpha=.08); ax.text((q[0] + q[2]) / 2, -.42, f"真ん中半分 {q[0]*100:.0f}〜{q[2]*100:.0f}%", ha="center", fontsize=9, color=C1)
ax.set_yticks([]); ax.set_ylim(-.5, .45); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax.set_xlabel("長期の損害率＝支払保険金 ÷ 新契約の保険料（2017〜2024年度の合計）"); ax.set_title("47都道府県の長期の損害率（1点が1都道府県、名前は出していない）", fontsize=12)
fig.tight_layout(); fig.savefig(F / "fig2_loss_ratio_spread.png"); plt.close()

# 図3 年度ごとの支払保険金と、各都道府県の「いちばん大きかった年」
nat = pd.DataFrame(R["national_by_fy"]).T; nat.index = nat.index.astype(int); nat = nat.loc[2017:]
cnt = pd.Series(R["H3_top_year_counts"]); cnt.index = cnt.index.astype(int)
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].bar(nat.index, nat.claim_oku / 1e4, color=[C2 if i in (2018, 2019) else C1 for i in nat.index]); ax[0].set_title("全国の支払保険金（兆円、住宅）", fontsize=11)
ax[0].set_xticks(nat.index); ax[0].set_xticklabels([f"{i}" for i in nat.index], fontsize=9)
ax2 = ax[0].twinx(); ax2.plot(nat.index, nat.L * 100, color=GR, marker="o"); ax2.set_ylabel("損害率（単年、%）", color=GR); ax2.spines["top"].set_visible(False)
ax[1].bar(cnt.index, cnt.values, color=[C2 if i in (2018, 2019) else C1 for i in cnt.index]); ax[1].set_xticks(cnt.index); ax[1].set_xticklabels([f"{i}" for i in cnt.index], fontsize=9)
ax[1].set_title("支払保険金がいちばん大きかった年度（都道府県の数）", fontsize=11)
for a in ax: a.set_xlabel("年度")
fig.tight_layout(); fig.savefig(F / "fig3_years.png"); plt.close()

# 図4 頑健性：順位相関と傾き
rows = [("基本（2017〜24年度、保険金額あたり）", R["main"]), ("1件あたりで測る", R["robust"]["per_contract"]), ("前半 2017〜20年度", R["robust"]["first_half_2017_2020"]),
        ("後半 2021〜24年度", R["robust"]["second_half_2021_2024"]), ("2018・2019年度を除く", R["robust"]["drop_top2_national_years"]),
        ("保険料で重みづけ", R["robust"]["weighted_by_premium"]), ("1年契約だけ 2014〜16年度", R["robust"]["one_year_contracts_2014_2016"])]
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
yy = np.arange(len(rows))[::-1]
ax[0].scatter([r[1]["spearman"] for r in rows], yy, color=C1, s=50); ax[0].axvline(.5, color=C2, ls="--", lw=1); ax[0].text(.52, len(rows) - 1.5, "H1 の基準 0.5", color=C2, fontsize=9)
ax[0].set_yticks(yy); ax[0].set_yticklabels([r[0] for r in rows], fontsize=9); ax[0].set_xlim(-.1, 1); ax[0].set_title("料率と保険金の順位相関", fontsize=11)
for i, (n, r) in zip(yy, rows):
    ax[1].plot([r["slope_ci_lo"], r["slope_ci_hi"]], [i, i], color=C1); ax[1].scatter(r["slope_b"], i, color=C1, s=50)
ax[1].axvline(1, color=GR, ls="--", lw=1); ax[1].axvline(0, color=GR, lw=.8); ax[1].set_xlim(-.15, 1.1); ax[1].set_title("料率の差 ÷ 保険金の差（傾き、95%区間）", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig4_robustness.png"); plt.close()

# 図5 H4
h4 = pd.read_csv(B / "results" / "C_H4.csv", index_col=0)
fig, ax = plt.subplots(figsize=(7, 4.8))
ax.scatter(h4.L_2017_19, h4.dlogRrel_1719_2224 * 100, color=C1, alpha=.7, s=40)
ax.axhline(0, color=GR, lw=.8); ax.set_xscale("log"); ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.3, 0.5, 0.7, 1, 1.5, 2, 3])); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0)); ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_xlabel("2017〜19年度の損害率（対数目盛）"); ax.set_ylabel("料率の全国比の変化（%、2017〜19→2022〜24年度）")
ax.set_title(f"前の損害率が高かった地域ほど、料率が相対的に上がったか（順位相関 {R['H4']['spearman']:.2f}）", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig5_h4.png"); plt.close()

# 図6 問い直し：8年の実績はどれだけ揺れるか
rq = R["reask"]; r1 = rq["reliability_1yr"]; n = np.arange(1, 61); rel = n * r1 / (1 + (n - 1) * r1)
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].plot(n, rel, color=C1, lw=2); ax[0].axhline(.8, color=GR, ls="--", lw=1); ax[0].axvline(8, color=C2, lw=1)
ax[0].text(9, rq["reliability_C_8yr"] - .08, f"8年で {rq['reliability_C_8yr']:.2f}", color=C2); ax[0].text(rq["years_for_rel_0_8"] + 1, .72, f"0.8 に届くのは数十年（目安）", color=GR, fontsize=9)
ax[0].set_xlabel("実績を集めた年数"); ax[0].set_ylabel("保険金の水準の信頼性（目安）"); ax[0].set_ylim(0, 1); ax[0].set_title("実績の保険金で地域の差を測るときの信頼性", fontsize=11)
rv = R["review"]
lab = ["傾き：観測", "傾き：補正（折半の幅）", "傾き：補正（再標本化95%）", "傾き：2018・19年度を除く6年で補正"]
mid = [rq["slope_observed"], rq["slope_corrected"], rq["slope_corrected"], rv["corrected_slope_6yr"]]
lo = [R["main"]["slope_ci_lo"], rv["corrected_slope_split_range"][0], rv["corrected_slope_boot95"][0], rv["corrected_slope_6yr"]]
hi = [R["main"]["slope_ci_hi"], rv["corrected_slope_split_range"][1], rv["corrected_slope_boot95"][1], rv["corrected_slope_6yr"]]
yy2 = np.arange(len(lab))[::-1]
for y_, m_, l_, h_, c_ in zip(yy2, mid, lo, hi, [C2, C1, C1, C3]):
    ax[1].plot([l_, h_], [y_, y_], color=c_, lw=2); ax[1].scatter(m_, y_, color=c_, s=50, zorder=3); ax[1].text(max(h_, m_) + .03, y_, f"{m_:.2f}", va="center", fontsize=9)
ax[1].axvline(1, color=GR, ls="--", lw=1); ax[1].set_yticks(yy2); ax[1].set_yticklabels(lab, fontsize=9); ax[1].set_xlim(0, 1.45)
ax[1].set_title("料率と保険金の傾き（対数）：補正の幅は大きい", fontsize=11)
fig.tight_layout(); fig.savefig(F / "fig6_reask_reliability.png"); plt.close()
print("ok")
