"""S10：高校卒業後の進学率、都道府県の差は縮まっているか。σ収束（ばらつきの推移）とβ収束（低かった県ほど伸びたか）"""
from common import *
import statsmodels.formula.api as smf
d, l = read("SSDSE-B-2026"); d = d.rename(columns={d.columns[0]: "year"})
d["rate"] = d.E4602 / d.E4601 * 100                      # 高等学校卒業者のうち進学者の割合
d["univ_seats"] = d.E6302 / d.A1101 * 1000               # 人口1,000人あたりの大学の学生数（地元の大学の多さの目安）
P = d.pivot(index="year", columns="Prefecture", values="rate")
sig = pd.DataFrame({"mean": P.mean(1), "sd": P.std(1), "cv": P.std(1) / P.mean(1) * 100, "max": P.max(1), "min": P.min(1), "range": P.max(1) - P.min(1)})
sig.round(3).to_csv(RES / "s10_sigma.csv", encoding="utf-8-sig"); print(sig.round(2))
b = pd.DataFrame({"r2012": P.loc[2012], "r2019": P.loc[2019], "r2023": P.loc[2023]}); b["g_all"] = b.r2023 - b.r2012; b["g_pre"] = b.r2019 - b.r2012; b["g_post"] = b.r2023 - b.r2019
m_all = smf.ols("g_all ~ r2012", b).fit(cov_type="HC3"); m_pre = smf.ols("g_pre ~ r2012", b).fit(cov_type="HC3"); m_post = smf.ols("g_post ~ r2019", b).fit(cov_type="HC3")
x23 = d[d.year == 2023].set_index("Prefecture")
b = b.join(x23[["univ_seats"]]); m_seat = smf.ols("r2023 ~ np.log(univ_seats)", b).fit(cov_type="HC3")
print(m_all.params, m_all.pvalues, m_pre.params, m_pre.pvalues, m_post.params, m_post.pvalues, m_seat.params, m_seat.rsquared)
b.round(2).sort_values("r2023").to_csv(RES / "s10_pref.csv", encoding="utf-8-sig")
s = {"mean_2012": sig.loc[2012, "mean"], "mean_2019": sig.loc[2019, "mean"], "mean_2023": sig.loc[2023, "mean"], "sd_2012": sig.loc[2012, "sd"], "sd_min_year": sig.sd.idxmin(), "sd_min": sig.sd.min(), "sd_2023": sig.loc[2023, "sd"],
     "cv_2012": sig.loc[2012, "cv"], "cv_2023": sig.loc[2023, "cv"], "max_2023_pref": P.loc[2023].idxmax(), "max_2023": P.loc[2023].max(), "min_2023_pref": P.loc[2023].idxmin(), "min_2023": P.loc[2023].min(),
     "beta_all": m_all.params.r2012, "beta_all_p": m_all.pvalues.r2012, "beta_pre": m_pre.params.r2012, "beta_pre_p": m_pre.pvalues.r2012, "beta_post": m_post.params.r2019, "beta_post_p": m_post.pvalues.r2019,
     "seat_coef_log": m_seat.params.iloc[1], "seat_r2": m_seat.rsquared, "corr_2012_2023": P.loc[[2012, 2023]].T.corr().iloc[0, 1]}
pd.Series(s).to_csv(RES / "s10_summary.csv", header=["value"]); print(pd.Series(s))

SRC = source("SSDSE-県別推移（SSDSE-B-2026）")
fig, ax = plt.subplots(figsize=(9, 4.2))
for c in P.columns: ax.plot(P.index, P[c], color=GRAY, lw=0.6, alpha=0.5)
for c, col in [(P.loc[2023].idxmax(), ORANGE), (P.loc[2023].idxmin(), BLUE)]: ax.plot(P.index, P[c], color=col, lw=2, label=c)
ax.plot(P.index, sig["mean"], color=INK, lw=2, ls="--", label="47都道府県の平均")
ax.set_ylabel("高校卒業者のうち進学した人（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title(f"進学率は11年で平均{sig.loc[2012, 'mean']:.0f}%→{sig.loc[2023, 'mean']:.0f}%。でも県の差は縮まっていない", loc="left")
fig.text(0.01, -0.04, SRC, fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s10_trend.png"); plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(10, 4))
axs[0].plot(sig.index, sig.sd, marker="o", color=BLUE); axs[0].set_ylabel("県の間の標準偏差（ポイント）"); axs[0].set_title("σ収束：ばらつき", loc="left", fontsize=11); axs[0].set_ylim(5, 8)
axs[1].scatter(b.r2012, b.g_all, s=20, color=LIGHT, edgecolor=BLUE, lw=0.6)
xx = np.linspace(b.r2012.min(), b.r2012.max(), 20); axs[1].plot(xx, m_all.params.Intercept + m_all.params.r2012 * xx, color=ORANGE)
axs[1].set_xlabel("2012年の進学率（%）"); axs[1].set_ylabel("2012→2023年の伸び（ポイント）"); axs[1].set_title("β収束：低かった県ほど伸びたか", loc="left", fontsize=11)
fig.suptitle("ばらつきは2017年まで小さくなり、その後また広がった", x=0.01, ha="left", fontsize=13)
fig.text(0.01, -0.04, SRC, fontsize=7.2, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "s10_convergence.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.scatter(b.univ_seats, b.r2023, s=24, color=LIGHT, edgecolor=BLUE, lw=0.6); ax.set_xscale("log")
xx = np.linspace(b.univ_seats.min(), b.univ_seats.max(), 50); ax.plot(xx, m_seat.params.iloc[0] + m_seat.params.iloc[1] * np.log(xx), color=ORANGE)
for c in ["東京都", "京都府", "沖縄県", "佐賀県", "北海道", "広島県", "愛知県", "鹿児島県"]: ax.annotate(c, (b.loc[c, "univ_seats"], b.loc[c, "r2023"]), xytext=(4, 2), textcoords="offset points", fontsize=8.5)
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
ax.xaxis.set_major_locator(FixedLocator([8, 10, 15, 20, 30, 50])); ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_major_formatter(FixedFormatter(["8", "10", "15", "20", "30", "50"]))
ax.set_xlabel("大学の学生数（人口1,000人あたり、対数目盛）"); ax.set_ylabel("進学率（%、2023年）")
ax.set_title(f"地元に大学が多い県ほど進学率が高い（大学の学生数が2倍で約{m_seat.params.iloc[1] * np.log(2):.0f}ポイント）", loc="left", fontsize=12)
fig.text(0.01, -0.04, SRC, fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s10_seats.png"); plt.close(fig)
