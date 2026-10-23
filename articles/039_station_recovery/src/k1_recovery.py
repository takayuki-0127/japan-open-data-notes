"""K1：コロナ前（2019年度）と比べて、2024年度に乗降客数が戻った駅・戻っていない駅。全国の推移、事業者の種類、首都圏の東京駅からの距離、駅の大きさで比べる"""
from common import *
import statsmodels.formula.api as smf
d = load(); d = d.join(flag_breaks(d))
d.loc[d.n_break > 0, ["name", "op", "line", "break_years", "max_abs_resid"] + [f"p{y}" for y in YEARS]].to_csv(RES / "k1_flagged_breaks.csv", index=False, encoding="utf-8-sig")
raw_x = d[(d.p2019 >= 1000) & (d.p2024 > 0)]
n_flag = int((raw_x.n_break > 0).sum())
d = d[d.n_break == 0]
# 1) 全国：2015〜2024年度の毎年データがある駅だけで合計（入れ替わりの影響を除く）
yrs = list(range(2015, 2025))
bal = d.dropna(subset=[f"p{y}" for y in yrs]); bal = bal[(bal[[f"p{y}" for y in yrs]] > 0).all(1)]
tot = bal[[f"p{y}" for y in yrs]].sum(); tot.index = yrs; idx = tot / tot[2019] * 100
by_type = pd.DataFrame({t: (g[[f"p{y}" for y in yrs]].sum().values / g["p2019"].sum() * 100) for t, g in bal.groupby("optype") if len(g) > 50}, index=yrs)
pd.concat([idx.rename("全国"), by_type], axis=1).round(2).to_csv(RES / "k1_index.csv", encoding="utf-8-sig"); print(idx.round(1)); print(by_type.round(1))
# 2) 駅ごとの戻り方（2024年度 ÷ 2019年度）
x = d[(d.p2019 >= 1000) & (d.p2024 > 0)].copy(); x["rec"] = x.p2024 / x.p2019 * 100
x["size"] = pd.cut(x.p2019, [999, 5000, 20000, 50000, 100000, 1e8], labels=["1千〜5千", "5千〜2万", "2万〜5万", "5万〜10万", "10万以上"])
size = x.groupby("size").agg(n=("rec", "size"), median=("rec", "median"), weighted=("p2024", "sum")); size["weighted"] = size.weighted / x.groupby("size").p2019.sum() * 100
size.round(1).to_csv(RES / "k1_by_size.csv", encoding="utf-8-sig"); print(size.round(1))
# 3) 首都圏（東京駅から60km以内）：距離との関係
m = x[x.km_tokyo <= 60].copy(); m["dist_bin"] = pd.cut(m.km_tokyo, [-0.1, 5, 10, 20, 30, 40, 50, 60], labels=["0-5", "5-10", "10-20", "20-30", "30-40", "40-50", "50-60"])
dist = m.groupby("dist_bin").agg(n=("rec", "size"), median=("rec", "median"), q25=("rec", lambda s: s.quantile(0.25)), q75=("rec", lambda s: s.quantile(0.75)), p2019=("p2019", "sum"), p2024=("p2024", "sum"))
dist["weighted"] = dist.p2024 / dist.p2019 * 100; dist.round(1).to_csv(RES / "k1_tokyo_distance.csv", encoding="utf-8-sig"); print(dist.round(1))
r = smf.wls("rec ~ np.log(km_tokyo + 1) + np.log(p2019) + C(optype)", m, weights=np.sqrt(m.p2019)).fit(cov_type="HC3"); print(r.params.round(2), r.pvalues.round(3))
# 大阪（大阪駅から40km以内）でも
o = x[x.km_osaka <= 40].copy(); o["dist_bin"] = pd.cut(o.km_osaka, [-0.1, 5, 10, 20, 30, 40], labels=["0-5", "5-10", "10-20", "20-30", "30-40"])
odist = o.groupby("dist_bin").agg(n=("rec", "size"), median=("rec", "median"), p2019=("p2019", "sum"), p2024=("p2024", "sum")); odist["weighted"] = odist.p2024 / odist.p2019 * 100
odist.round(1).to_csv(RES / "k1_osaka_distance.csv", encoding="utf-8-sig"); print(odist.round(1))
# 4) 大きな駅（2019年度に5万人以上）の戻った駅・戻っていない駅
big = x[x.p2019 >= 50000].sort_values("rec")
cols = ["name", "op", "line", "p2019", "p2024", "rec", "km_tokyo"]
big[cols].round(1).to_csv(RES / "k1_big_stations.csv", index=False, encoding="utf-8-sig")
print(big[cols].head(12).round(1).to_string()); print(big[cols].tail(12).round(1).to_string())
s = {"n_flagged_breaks": n_flag, "n_before_flag": len(raw_x), "n_balanced": len(bal), "nat_2020": idx[2020], "nat_2021": idx[2021], "nat_2023": idx[2023], "nat_2024": idx[2024], "n_stations_rec": len(x), "rec_median": x.rec.median(),
     "share_recovered_100": (x.rec >= 100).mean() * 100, "tokyo_0_5_weighted": dist.loc["0-5", "weighted"], "tokyo_30_40_weighted": dist.loc["30-40", "weighted"], "tokyo_50_60_weighted": dist.loc["50-60", "weighted"],
     "tokyo_0_5_median": dist.loc["0-5", "median"], "tokyo_50_60_median": dist.loc["50-60", "median"], "b_logdist": r.params["np.log(km_tokyo + 1)"], "p_logdist": r.pvalues["np.log(km_tokyo + 1)"], "n_metro": len(m),
     "osaka_0_5_weighted": odist.loc["0-5", "weighted"], "osaka_20_30_weighted": odist.loc["20-30", "weighted"], "n_big": len(big)}
s.update({f"type_{k}_2024": v for k, v in by_type.loc[2024].items()})
pd.Series(s).to_csv(RES / "k1_summary.csv", header=["value"]); print(pd.Series(s))

fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(yrs, idx, color=INK, lw=2.4, marker="o", label="全国（毎年データがある駅の合計）")
for (t, col) in zip(by_type.columns, [BLUE, ORANGE, GREEN, PURPLE, GRAY]): ax.plot(yrs, by_type[t], color=col, lw=1.2, marker=".", label=t)
ax.axhline(100, color=INK, lw=0.6, ls=":"); ax.set_ylabel("2019年度＝100"); ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower left")
ax.set_title(f"駅の利用者は2020年度に{idx[2020]:.0f}まで落ち、2024年度は{idx[2024]:.0f}", loc="left")
fig.text(0.01, -0.04, SOURCE + f"（2015〜2024年度に毎年データがある{len(bal):,}駅×路線）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "k1_index.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.2)); xx = np.arange(len(dist))
ax.bar(xx - 0.2, dist.weighted, 0.4, color=BLUE, label="東京（東京駅からの距離）")
ax.bar(xx + 0.2, odist.reindex(dist.index).weighted, 0.4, color=ORANGE, label="大阪（大阪駅からの距離）")
for i, v in enumerate(dist.weighted): ax.text(i - 0.2, v + 0.5, f"{v:.0f}", ha="center", fontsize=8.5)
for i, v in enumerate(odist.reindex(dist.index).weighted):
    if pd.notna(v): ax.text(i + 0.2, v + 0.5, f"{v:.0f}", ha="center", fontsize=8.5)
ax.axhline(100, color=INK, lw=0.6, ls=":"); ax.set_ylim(70, 105); ax.set_xticks(xx, dist.index); ax.set_xlabel("東京駅（大阪駅）からの距離（km）"); ax.set_ylabel("2024年度 ÷ 2019年度（%）")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("都心に近い駅ほど、利用者が戻りきっていない", loc="left")
fig.text(0.01, -0.04, SOURCE + "（2019年度に1日1,000人以上の駅×路線。数字の定義が変わったとみられる段差のある駅は除く）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "k1_distance.png"); plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.6))
for ax, t, col, ttl in [(axs[0], big.head(12), BLUE, "戻っていない大きな駅"), (axs[1], big.tail(12).iloc[::-1], ORANGE, "戻った・増えた大きな駅")]:
    lab = (t.name + "（" + t.op.str.replace("旅客鉄道", "").str.replace("東京地下鉄", "東京メトロ").str.replace("株式会社", "") + "）").values
    yy = np.arange(len(t)); ax.barh(yy, t.rec, color=col); ax.set_yticks(yy, lab, fontsize=8); ax.invert_yaxis(); ax.axvline(100, color=INK, lw=0.6)
    for i, v in enumerate(t.rec): ax.text(v + 1, i, f"{v:.0f}", va="center", fontsize=8)
    ax.set_title(ttl, loc="left", fontsize=11); ax.set_xlim(0, max(140, t.rec.max() + 15))
fig.suptitle("2024年度 ÷ 2019年度（%）：2019年度に1日5万人以上の駅×路線", x=0.01, ha="left", fontsize=12)
fig.text(0.01, -0.03, SOURCE, fontsize=7, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "k1_big.png"); plt.close(fig)
