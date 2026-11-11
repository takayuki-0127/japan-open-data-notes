"""F277 04 図 → figures/"""
import os, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f: font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
P = pd.read_csv(os.path.join(HERE, "..", "results", "A_panel_with_fits.csv"))
J = json.load(open(os.path.join(HERE, "..", "results", "main.json"), encoding="utf-8"))
FIG = os.path.join(HERE, "..", "figures"); os.makedirs(FIG, exist_ok=True)
C1, C2, C3, C4 = "#2f6db5", "#e07b39", "#7a7a7a", "#3a9e5f"
def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(FIG, name), dpi=150); plt.close(fig)

# 図1 上げ幅と第4表
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(P.year, P.y, "-o", color=C1, label="最低賃金の引上げ率（全国加重平均）")
ax.plot(P.year, P.t4, "-s", color=C2, label="賃金改定状況調査 第4表の賃金上昇率")
ax.fill_between(P.year, P.t4, P.y, where=P.y >= P.t4, color=C1, alpha=0.12)
ax.axhline(0, color="k", lw=0.6)
for y in [2007, 2016]: ax.axvline(y - 0.5, color=C3, ls=":", lw=1)
ax.annotate("2020年：目安を示さず", (2020, 0.11), (2020.4, -0.85), arrowprops=dict(arrowstyle="->", color=C3), fontsize=9)
ax.set_ylim(-1.2, 6.9)
ax.set_ylabel("%"); ax.set_xlabel("年度"); ax.set_title("最低賃金の上げ幅は、2007年から第4表を上回り続けている")
ax.legend(loc="upper left", fontsize=9); ax.set_xticks(range(2003, 2027, 2))
save(fig, "fig1_mw_vs_t4.png")

# 図2 差（Y−T4）の年ごとと期間平均
fig, ax = plt.subplots(figsize=(9, 4.6))
cols = [C3 if y <= 2006 else (C2 if y == 2020 else C1) for y in P.year]
ax.bar(P.year, P.gap_t4, color=cols)
per = J["H1"]["mean_gap_by_period"]
for k, (lo, hi) in {"2003-2006": (2003, 2006), "2007-2015": (2007, 2015), "2016-2019": (2016, 2019), "2021-2026": (2021, 2026)}.items():
    ax.hlines(per[k], lo - 0.4, hi + 0.4, color="k", lw=2)
    ax.text((lo + hi) / 2, per[k] + 0.12, f"平均 {per[k]:+.1f}", ha="center", fontsize=9)
ax.axhline(0, color="k", lw=0.6); ax.set_ylabel("ポイント（引上げ率 − 第4表）"); ax.set_xlabel("年度")
ax.set_title("第4表との差は、時期を追うごとに大きくなった"); ax.set_xticks(range(2003, 2027, 2))
save(fig, "fig2_gap_by_period.png")

# 図3 5つの指標での当てはめと、1年ずつ抜いた予測、前年と同じ
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(P.year, P.y, "-o", color="k", label="実際の引上げ率")
ax.plot(P.year, P.fit_m2, "--", color=C1, label=f"5つの指標で当てはめ（決定係数 {J['M2']['r2']:.2f}）")
ax.plot(P.year, P.y - P.loo_res_m2, ":", marker="x", color=C1, label=f"その年を抜いて予測（誤差 {J['M2']['loo_rmse']:.2f}ポイント）")
import statsmodels.api as sm
loo1 = []
for i in P.index:
    m = sm.OLS(P.drop(i)["y"], sm.add_constant(P.drop(i)[["t4"]])).fit()
    loo1.append(float(m.predict(sm.add_constant(P.loc[[i], ["t4"]], has_constant="add")).iloc[0]))
ax.plot(P.year, loo1, ":", marker=".", color=C2, label=f"第4表だけで、その年を抜いて予測（誤差 {J['M1']['loo_rmse']:.2f}ポイント）")
ax.plot(P.year, P.y_prev, "-", color=C3, alpha=0.7, label=f"前年と同じ（誤差 {J['naive_prev']['rmse']:.2f}ポイント）")
ax.set_ylabel("%"); ax.set_xlabel("年度"); ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("指標を5つに増やすと当てはまりは上がるが、予測の誤差は第4表だけより大きい"); ax.set_xticks(range(2003, 2027, 2))
save(fig, "fig3_fit_loo_naive.png")

# 図4 2003〜2015で当てはめて2016〜2026を予測
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(P.year, P.y, "-o", color="k", label="実際")
te = P[P.year >= 2016]
ax.plot(te.year, te.pred_m3.clip(upper=9), "--o", color=C2, label="5つの指標（2003〜2015で当てはめ）")
ax.plot(te.year, te.pred_m3b, "--s", color=C1, label="第4表だけ（2003〜2015で当てはめ）")
for r in te.itertuples():
    if r.pred_m3 > 9: ax.annotate(f"{r.pred_m3:.0f}%", (r.year, 9), (r.year - 0.3, 8.2), fontsize=8, color=C2)
ax.axvline(2015.5, color=C3, ls=":"); ax.set_ylim(-0.5, 9.5)
ax.text(2015.6, 9.0, "←当てはめ｜予測→", fontsize=9, color=C3)
ax.set_ylabel("%（9%より上は数字で表示）"); ax.set_xlabel("年度"); ax.legend(fontsize=8.5, loc="upper left")
ax.set_title("2015年までの関係は、春季賃上げが跳ねた2023年以降には延ばせない"); ax.set_xticks(range(2003, 2027, 2))
save(fig, "fig4_out_of_sample.png")

# 図5 頑健性（同じ年どうしで比べる）
R = json.load(open(os.path.join(HERE, "..", "results", "review_checks.json"), encoding="utf-8"))
rb = J["robust"]; sy = R["same_years_compare"]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.5]})
lab = ["基本", "R1 物価を前年の暦年に", "R2 2009・2020年度を除く", "R4 円で"]
r2 = [J["M2"]["r2"], rb["R1_cpi_calendar"]["r2"], rb["R2_excl_2020_2009"]["r2"], rb["R4_yen"]["r2"]]
axs[0].barh(lab[::-1], r2[::-1], color=C1); axs[0].axvline(0.7, color="k", ls="--", lw=1)
axs[0].set_title("5つの指標の決定係数（破線＝基準0.7）", fontsize=10); axs[0].set_xlim(0, 1)
conds = [("基本（2004〜26年度）", sy["base_2004_2026"]["five_loo"], sy["base_2004_2026"]["t4_only_loo"], sy["base_2004_2026"]["naive"]),
         ("R1 物価を暦年に（同じ年）", sy["base_2004_2026"]["five_cal_loo"], sy["base_2004_2026"]["t4_only_loo"], sy["base_2004_2026"]["naive"]),
         ("R2 2009・2020を除く", sy["excl_2009_2020"]["five_loo"], sy["excl_2009_2020"]["t4_only_loo"], sy["excl_2009_2020"]["naive"]),
         ("R2 さらに2021も除く", sy["excl_2009_2020_2021"]["five_loo"], sy["excl_2009_2020_2021"]["t4_only_loo"], sy["excl_2009_2020_2021"]["naive"])]
yy = np.arange(len(conds))[::-1]; h = 0.26
axs[1].barh(yy + h, [c[1] for c in conds], h, color=C1, label="5つの指標")
axs[1].barh(yy, [c[2] for c in conds], h, color=C2, label="第4表だけ")
axs[1].barh(yy - h, [c[3] for c in conds], h, color=C3, label="前年と同じ")
for k, c in zip(yy, conds):
    for dy, v in ((h, c[1]), (0, c[2]), (-h, c[3])): axs[1].text(v + 0.01, k + dy, f"{v:.2f}", va="center", fontsize=8)
axs[1].set_yticks(yy); axs[1].set_yticklabels([c[0] for c in conds]); axs[1].set_xlim(0, 1.35)
axs[1].set_title("同じ年で比べた、1年ずつ抜いた予測の誤差（ポイント）", fontsize=10); axs[1].legend(fontsize=8, loc="lower right")
fig.text(0.99, 0.01, f"R4（円、{R['yen_same_years']['n']}年）：5指標 {R['yen_same_years']['five_loo']:.1f}円、前年と同じ {R['yen_same_years']['naive']:.1f}円", fontsize=8, ha="right")
for ax in axs: ax.tick_params(labelsize=8.5)
fig.suptitle("どの指標が先を読めるかは、どの年を入れるかで入れ替わる", fontsize=11)
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(os.path.join(FIG, "fig5_robustness.png"), dpi=150); plt.close(fig)

# 図6 問い直し：第4表と前年の最低賃金の引上げ
fig, ax = plt.subplots(figsize=(8, 5))
q = P[P.year >= 2004]
sc = ax.scatter(q.y_prev, q.t4, c=q.spr, cmap="viridis", s=60)
for r in q.itertuples():
    if r.year in (2007, 2009, 2016, 2021, 2023, 2026): ax.annotate(str(r.year), (r.y_prev, r.t4), (6, 6) if r.year != 2021 else (8, 10), textcoords="offset points", fontsize=9)
cb = fig.colorbar(sc, ax=ax); cb.set_label("その年の春季賃上げ率（%）")
b = J["reask"]["prev_spr_emp"]["coef"]["y_prev"]
ax.set_xlabel("前年度の最低賃金の引上げ率（%）"); ax.set_ylabel("その年の第4表の賃金上昇率（%）")
ax.set_title(f"第4表は前年の引上げとともに動く（春季賃上げ・人手不足をそろえても1ポイントあたり+{b:.2f}）", fontsize=10)
save(fig, "fig6_reask_t4_prev_mw.png")
print(sorted(os.listdir(FIG)))
