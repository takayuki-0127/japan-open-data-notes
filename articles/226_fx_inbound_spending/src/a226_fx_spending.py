"""226 為替レートと訪日客1人あたりの支出は連動しているか（国籍×年のパネル回帰）"""
from common import *
import statsmodels.formula.api as smf

d = load()
d["ls"] = np.log(d.spend); d["lfx"] = np.log(d.jpy_per)
d.round(4).to_csv(RES / "panel_nationality_year.csv", index=False)
main = d[d.year != 2022]

rows = []
specs = {"A 国籍の固定効果のみ（2019・23〜25年）": ("ls ~ lfx + C(nationality)", main),
         "B 国籍＋年の固定効果（2019・23〜25年）": ("ls ~ lfx + C(nationality) + C(year)", main),
         "C Bに2022年を加える": ("ls ~ lfx + C(nationality) + C(year)", d),
         "D 2023〜25年だけ（国籍＋年）": ("ls ~ lfx + C(nationality) + C(year)", d[d.year >= 2023])}
M = {}
for k, (f, data) in specs.items():
    m = smf.ols(f, data).fit(cov_type="cluster", cov_kwds={"groups": data["nationality"]}); M[k] = m
    rows.append({"model": k, "beta": m.params["lfx"], "se": m.bse["lfx"], "lo95": m.conf_int().loc["lfx", 0], "hi95": m.conf_int().loc["lfx", 1],
                 "p_beta0": m.pvalues["lfx"], "p_beta1": 2 * (1 - __import__("scipy").stats.norm.cdf(abs((m.params["lfx"] - 1) / m.bse["lfx"]))),
                 "n": int(m.nobs)})
reg = pd.DataFrame(rows).round(3); reg.to_csv(RES / "regressions.csv", index=False); print(reg.to_string())

# 2019→2025 の変化（円・現地通貨・為替）
w = d.pivot(index="nationality", columns="year", values=["spend", "jpy_per", "spend_local"])
ch = pd.DataFrame({"spend_yen_pct": (w["spend"][2025] / w["spend"][2019] - 1) * 100,
                   "fx_pct": (w["jpy_per"][2025] / w["jpy_per"][2019] - 1) * 100,
                   "spend_local_pct": (w["spend_local"][2025] / w["spend_local"][2019] - 1) * 100,
                   "currency": d.drop_duplicates("nationality").set_index("nationality").currency}).round(1).sort_values("fx_pct")
ch.to_csv(RES / "change_2019_2025.csv"); print(ch)
print("corr", np.corrcoef(np.log1p(ch.fx_pct / 100), np.log1p(ch.spend_yen_pct / 100))[0, 1])
c2 = ch.copy(); c2["l_fx"] = np.log1p(c2.fx_pct / 100); c2["l_sp"] = np.log1p(c2.spend_yen_pct / 100)
lm = smf.ols("l_sp ~ l_fx", c2).fit(cov_type="HC1"); print(lm.params, lm.bse)
pd.DataFrame({"coef": lm.params, "se": lm.bse, "p": lm.pvalues}).round(3).to_csv(RES / "cross_section_2019_2025.csv")

# 図1 2019→2025：為替の変化と円建て支出の変化
fig, ax = plt.subplots(figsize=(8.5, 6))
ax.scatter(ch.fx_pct, ch.spend_yen_pct, s=60, color=BLUE, zorder=3)
for n, r in ch.iterrows():
    ax.annotate(n, (r.fx_pct, r.spend_yen_pct), xytext=(5, 3), textcoords="offset points", fontsize=8.5)
xs = np.linspace(ch.fx_pct.min() - 3, ch.fx_pct.max() + 3, 50)
ax.plot(xs, ((1 + xs / 100) - 1) * 100 + 0, color=GRAY, ls="--", lw=1)
ax.text(xs[-1], xs[-1] - 4, "円安と同じだけ増える線", fontsize=8, color=GRAY, ha="right")
ax.plot(xs, (np.exp(lm.params["Intercept"] + lm.params["l_fx"] * np.log1p(xs / 100)) - 1) * 100, color=ORANGE, lw=1.6)
ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("現地通貨1単位あたりの円の変化（%、2019→2025年、＋＝円安）")
ax.set_ylabel("1人当たり旅行消費単価（円）の変化（%）")
ax.set_title("2019→2025年：円安が進んだ通貨の国ほど、円で見た支出は増えたか", loc="left")
save(fig, "a226_change.png")

# 図2 国籍別の推移（円と現地通貨、2019=100）
sel = ["中国", "韓国", "台湾", "米国", "英国", "ドイツ"]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
pal = [ORANGE, GREEN, PURPLE, BLUE, "#1f4e9c", INK]
for ax, col, ttl in [(axs[0], "spend", "円で見た支出（2019年=100）"), (axs[1], "spend_local", "現地通貨で見た支出（2019年=100）")]:
    for n, c in zip(sel, pal):
        s = d[d.nationality == n].set_index("year")[col]; s = s / s[2019] * 100
        ax.plot(s.index, s.values, marker="o", color=c, lw=1.6, label=n)
    ax.axhline(100, color=GRAY, lw=0.8); ax.set_title(ttl, loc="left"); ax.set_xticks(YEARS)
axs[0].legend(frameon=False, fontsize=8.5, ncol=2)
axs[1].text(2019.1, 290, "2022年は入国制限が残り、\n回答者が少ない年", fontsize=8, color=GRAY)
save(fig, "a226_index.png")

# 図3 回帰の係数
fig, ax = plt.subplots(figsize=(8.5, 3.8))
for i, r in reg.iloc[::-1].reset_index(drop=True).iterrows():
    ax.plot([r.lo95, r.hi95], [i, i], color=BLUE, lw=2); ax.plot(r.beta, i, "o", color=BLUE)
    ax.text(r.hi95 + 0.05, i, f"{r.beta:.2f}（{r.lo95:.2f}〜{r.hi95:.2f}）", va="center", fontsize=8.5)
ax.set_yticks(range(len(reg))); ax.set_yticklabels(reg.model[::-1], fontsize=8.5)
ax.axvline(0, color=GRAY, lw=1); ax.axvline(1, color=ORANGE, lw=1, ls="--")
ax.text(1.03, -0.45, "1＝現地通貨では同じ額を使う", fontsize=8, color=ORANGE)
ax.set_xlabel("円安1%あたり、円で見た支出が何%増えるか（弾力性、95%信頼区間）", labelpad=8)
ax.set_ylim(-0.8, len(reg) - 0.5)
ax.set_title("国籍×年のパネル回帰（15か国・地域）", loc="left")
save(fig, "a226_coef.png", y=-0.07)
