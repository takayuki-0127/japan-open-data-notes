"""I2：都道府県で動画サイトの利用率は違うのか。標本の誤差の範囲（ファンネルプロット）と、高齢化・所得で説明できる部分"""
from common import *
import statsmodels.formula.api as smf
V = "動画投稿・共有サイトの利用（ＹｏｕＴｕｂｅ、ニコニコ動画など）"
s = read_table("構15表")
raw = pd.read_excel(RAW / "r7_kosein.xls", sheet_name="構15表", header=None)
lab = raw[2].astype(str).str.replace("　", "").str.strip()
p = s[s.section == "都道府県"][["label", V, "オンラインゲームの利用"]].copy()
p["n"] = [int(raw.loc[lab[lab == l].index.min(), 3]) for l in p.label]
p["pref"] = p.label.str[2:]; p = p.rename(columns={V: "video", "オンラインゲームの利用": "game"})
nat = float(s[s.label == "男女計："][V].iloc[0])

# 標本の誤差の範囲（単純無作為抽出とみなした近似。比重調整があるので実際はもう少し広い）
p["se"] = np.sqrt(nat * (100 - nat) / p.n); p["z"] = (p.video - nat) / p.se

# 都道府県の特徴（SSDSE-E）
h = pd.read_csv(RAW / "SSDSE-E-2026.csv", encoding="cp932", header=None, nrows=1).iloc[0]
e = pd.read_csv(RAW / "SSDSE-E-2026.csv", encoding="cp932", header=None, skiprows=3); e.columns = list(h)
e = e.rename(columns={"Prefecture": "pref"})
e["old"] = e.A1303 / e.A1101 * 100; e["inc"] = e.C122101 / 1000; e["single"] = e.A810105 / e.A710101 * 100
p = p.merge(e[["pref", "old", "inc", "single"]], on="pref", how="left"); assert p.old.notna().all()
m1 = smf.ols("video ~ old", p).fit(cov_type="HC3"); m2 = smf.ols("video ~ old + inc", p).fit(cov_type="HC3")
p["resid"] = m2.resid
print(m1.summary().tables[1]); print(m2.summary().tables[1], "R2", round(m1.rsquared, 3), round(m2.rsquared, 3))
out = {"national": nat, "n_min": p.n.min(), "n_max": p.n.max(), "n_median": p.n.median(), "sd_obs": p.video.std(), "sd_expected_sampling": np.sqrt((p.se ** 2).mean()),
       "outside_95": int((p.z.abs() > 1.96).sum()), "outside_998": int((p.z.abs() > 3.09).sum()),
       "b_old": m1.params.old, "p_old": m1.pvalues.old, "r2_old": m1.rsquared, "b_old_m2": m2.params.old, "b_inc_m2": m2.params.inc, "p_inc_m2": m2.pvalues.inc, "r2_m2": m2.rsquared,
       "corr_video_game": p[["video", "game"]].corr().iloc[0, 1]}
pd.Series(out).round(3).to_csv(RES / "i2_summary.csv", header=["value"]); print(pd.Series(out).round(3))
p.sort_values("z").round(2).to_csv(RES / "i2_pref.csv", index=False, encoding="utf-8-sig")
print(p.sort_values("z")[["pref", "video", "n", "z", "old", "inc", "resid"]].round(2).to_string())

# 図1：ファンネルプロット
fig, ax = plt.subplots(figsize=(9, 4.8)); nn = np.linspace(p.n.min() * 0.9, p.n.max() * 1.05, 200); se = np.sqrt(nat * (100 - nat) / nn)
for k, ls, lb in [(1.96, "--", "95%の範囲"), (3.09, ":", "99.8%の範囲")]:
    ax.plot(nn, nat + k * se, color=GRAY, ls=ls, lw=1, label=lb); ax.plot(nn, nat - k * se, color=GRAY, ls=ls, lw=1)
ax.axhline(nat, color=INK, lw=0.8); ax.set_xscale("log")
from matplotlib.ticker import FixedLocator, NullLocator, FixedFormatter
ax.xaxis.set_major_locator(FixedLocator([400, 500, 600, 700, 800, 1000])); ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_major_formatter(FixedFormatter(["400", "500", "600", "700", "800", "1000"]))
out_ = p.z.abs() > 1.96
ax.scatter(p.n[~out_], p.video[~out_], s=22, color=LIGHT, edgecolor=BLUE, lw=0.6, zorder=3)
ax.scatter(p.n[out_], p.video[out_], s=34, color=ORANGE, zorder=4)
for _, r in p[p.pref.isin(["東京都", "栃木県", "山形県", "山梨県", "福岡県"])].iterrows():
    ax.annotate(r.pref, (r.n, r.video), xytext=(5, 2), textcoords="offset points", fontsize=8.5)
ax.set_xlabel("回答した人数（対数目盛）"); ax.set_ylabel("ネット利用者のうち動画サイトを使った人（%）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("都道府県の差は、回答者数から見込まれる誤差より大きい", loc="left")
fig.text(0.01, -0.04, SOURCE + "（線は全国値と、単純無作為抽出とみなした近似の範囲）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "i2_funnel.png"); plt.close(fig)

# 図2：高齢化との関係
fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.scatter(p.old, p.video, s=24, color=LIGHT, edgecolor=BLUE, lw=0.6)
xx = np.linspace(p.old.min(), p.old.max(), 50); ax.plot(xx, m1.params.Intercept + m1.params.old * xx, color=ORANGE)
for _, r in p[p.pref.isin(["東京都", "沖縄県", "秋田県", "栃木県", "山形県"])].iterrows():
    ax.annotate(r.pref, (r.old, r.video), xytext=(4, 2), textcoords="offset points", fontsize=8.5)
ax.set_xlabel("65歳以上の割合（%、2024年）"); ax.set_ylabel("動画サイトを使った人（%、ネット利用者のうち）")
ax.set_title(f"高齢化が1ポイント進んだ県ほど、利用率は約{-m1.params.old:.1f}ポイント低い", loc="left")
fig.text(0.01, -0.04, SOURCE + "、独立行政法人統計センター「SSDSE-E-2026」をもとに作成者が加工して作成", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "i2_old.png"); plt.close(fig)

# 図3：世帯年収別（全国）
inc = s[s.section == "所属世帯年収"][["label", V]]
fig, ax = plt.subplots(figsize=(8.5, 3.8)); ax.bar(inc.label.str.replace("^200万円未満", "〜200", regex=True).str.replace("～", "〜").str.replace("万円未満", "").str.replace("万円以上", "+"), inc[V], color=BLUE)
for i, v in enumerate(inc[V]): ax.text(i, v + 1, f"{v:.0f}", ha="center", fontsize=9)
ax.set_ylim(0, 90); ax.set_xlabel("世帯年収（万円）"); ax.set_ylabel("動画サイトを使った人（%）"); ax.tick_params(axis="x", labelsize=8.5)
ax.set_title("世帯年収が高いほど使う人が多い……ただし年齢の違いが混ざっている", loc="left")
fig.text(0.01, -0.06, SOURCE + "（ネット利用者のうち）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "i2_income.png"); plt.close(fig)
