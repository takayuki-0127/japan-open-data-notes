"""A194 大きな都市ほど自動車を使う割合は低いのか（全国都市交通特性調査 R3、70都市）"""
from common import *
m = load("modal_share_r3.csv"); p = load("population.csv", ) if False else pd.read_csv(DATA / "population.csv", dtype={"code": str})
m["code5"] = m.code.astype(str).str.zfill(5)
d = m.merge(p, left_on="code5", right_on="code", suffixes=("", "_p"))
d["car"] = d.car_drive + d.car_pass; d["hol_car"] = d.hol_car_drive + d.hol_car_pass
d["lpop"] = np.log10(d.pop2020); d["ldens"] = np.log10(d.pop2020 / d.area_km2)
d["metro"] = d.seg == "三大都市圏"
def ols(x, y):
    X = np.column_stack([np.ones(len(x)), x]); b, *_ = np.linalg.lstsq(X, y, rcond=None); r = y - X @ b
    r2 = 1 - (r ** 2).sum() / ((y - y.mean()) ** 2).sum(); return b, r2
res = []
for name, sub in [("全70都市", d), ("三大都市圏", d[d.metro]), ("地方都市圏", d[~d.metro])]:
    for xv, xl in [("lpop", "log10人口"), ("ldens", "log10人口密度")]:
        b, r2 = ols(sub[xv].values, sub.car.values); res.append([name, xl, len(sub), round(b[1], 2), round(r2, 3), round(np.corrcoef(sub[xv], sub.car)[0, 1], 3)])
reg = pd.DataFrame(res, columns=["group", "x", "n", "slope_pt_per_10x", "r2", "corr"]); reg.to_csv(RES / "a194_regression.csv", index=False)
# 多変量：人口と密度と三大都市圏
X = np.column_stack([np.ones(len(d)), d.lpop, d.ldens, d.metro.astype(float)]); b, *_ = np.linalg.lstsq(X, d.car.values, rcond=None)
rr = d.car.values - X @ b; r2m = 1 - (rr ** 2).sum() / ((d.car - d.car.mean()) ** 2).sum()
d[["city", "seg", "seg2", "pop2020", "area_km2", "car", "car_drive", "car_pass", "rail", "bus", "bike", "walk_other", "hol_car"]].sort_values("car").to_csv(RES / "a194_city_table.csv", index=False)
big = d[d.pop2020 >= 1_000_000].sort_values("car")
ts = load("car_rail_timeseries.csv"); yrs = ["1987", "1992", "1999", "2005", "2010", "2015", "2021"]
ts["grp"] = np.where(ts.seg == "三大都市圏", np.where(ts.seg2 == "中心都市", "三大都市圏の中心都市", "三大都市圏の周辺都市"), np.where(ts.seg2 == "中心都市", "地方都市圏の中心都市", "地方都市圏の周辺・その他"))
full = ts.dropna(subset=[f"car{y}" for y in yrs])
tsm = full.groupby("grp")[[f"car{y}" for y in yrs]].mean().round(1); tsm["n"] = full.groupby("grp").size(); tsm.to_csv(RES / "a194_car_by_group_7yrs.csv")
with open(RES / "a194_summary.txt", "w") as f:
    f.write(reg.to_string(index=False) + f"\n\n重回帰（自動車分担率 ~ log10人口 + log10密度 + 三大都市圏）係数 {np.round(b,2)} R2={r2m:.3f}\n\n")
    f.write("100万人以上:\n" + big[["city", "pop2020", "car", "rail", "bus", "bike", "walk_other"]].to_string(index=False) + "\n\n")
    f.write("自動車分担率 上位5:\n" + d.nlargest(5, "car")[["city", "pop2020", "car"]].to_string(index=False) + "\n下位5:\n" + d.nsmallest(5, "car")[["city", "pop2020", "car"]].to_string(index=False) + "\n\n")
    f.write("地方都市圏で人口30万以上:\n" + d[(~d.metro) & (d.pop2020 >= 300000)].sort_values("car")[["city", "pop2020", "car", "rail", "bus"]].to_string(index=False) + "\n\n")
    f.write("7時点そろう都市のグループ平均:\n" + tsm.to_string() + "\n\n")
    f.write(f"休日の自動車分担率 平均 {d.hol_car.mean():.1f} 平日 {d.car.mean():.1f}; 休日>平日の都市 {(d.hol_car > d.car).sum()}/{len(d)}\n")
    f.write(f"自動車分担率 中央値 {d.car.median():.1f}; 50%以上の都市 {(d.car >= 50).sum()}\n")
# fig1 scatter
fig, ax = plt.subplots(figsize=(8, 5.2))
for g, col, lab in [(True, BLUE, "三大都市圏"), (False, ORANGE, "地方都市圏")]:
    s = d[d.metro == g]; ax.scatter(s.pop2020, s.car, color=col, s=36, alpha=0.85, label=lab, edgecolor="white", lw=0.5)
xx = np.linspace(d.lpop.min(), d.lpop.max(), 50)
for sub, col in [(d[d.metro], BLUE), (d[~d.metro], ORANGE)]:
    bb, _ = ols(sub.lpop.values, sub.car.values); xs = np.linspace(sub.lpop.min(), sub.lpop.max(), 30); ax.plot(10 ** xs, bb[0] + bb[1] * xs, color=col, lw=1.4)
for _, r in d.iterrows():
    if r.city in ["東京２３区", "大阪市", "横浜市", "名古屋市", "札幌市", "福岡市", "広島市", "小矢部市", "湯沢市", "鹿児島市", "宇都宮市", "京都市", "北九州市", "仙台市"]:
        ax.annotate(r.city.replace("東京２３区", "東京23区"), (r.pop2020, r.car), xytext=(4, 3), textcoords="offset points", fontsize=8)
ax.set_xscale("log"); ax.set_xlabel("人口（2020年、対数目盛）"); ax.set_ylabel("自動車の分担率（平日、運転＋同乗、%）"); ax.set_title("都市の人口と自動車の分担率（70都市、2021年度）")
ax.legend(frameon=False); ax.set_ylim(0, 92)
save(fig, "a194_scatter.png")
# fig2 big cities stacked
modes = [("rail", "鉄道", BLUE), ("bus", "バス", LIGHT), ("car", "自動車", ORANGE), ("bike", "自転車", GREEN), ("walk_other", "徒歩・その他", GRAY)]
b2 = d[(d.pop2020 >= 500000)].sort_values("car", ascending=False)
fig, ax = plt.subplots(figsize=(8, 5.6)); left = np.zeros(len(b2))
for c, l, col in modes:
    ax.barh(b2.city.str.replace("東京２３区", "東京23区"), b2[c], left=left, color=col, label=l); left += b2[c].values
for y, v in enumerate(b2.car): ax.text(b2.rail.iloc[y] + b2.bus.iloc[y] + v / 2, y, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white")
ax.set_xlabel("代表交通手段の構成比（平日、%。自動二輪は省略）"); ax.set_title("人口50万人以上の都市の交通手段", pad=26); ax.legend(frameon=False, ncol=5, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.45, 0.995)); ax.set_xlim(0, 100)
save(fig, "a194_big_cities.png")
# fig3 time series
fig, ax = plt.subplots(figsize=(8, 4.8)); xs = [int(y) for y in yrs]
for (g, row), col in zip(tsm.iterrows(), [BLUE, LIGHT, ORANGE, "#f2a37f"]):
    ax.plot(xs, row[[f"car{y}" for y in yrs]].values, marker="o", color=col, lw=2, label=f"{g}（{int(row.n)}都市）")
    ax.annotate(f"{row[f'car2021']:.0f}", (2021, row["car2021"]), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9, color=col)
ax.set_xticks(xs); ax.set_ylabel("自動車の分担率（平日、%）"); ax.set_title("自動車の分担率の推移（7回とも調査した都市の平均）"); ax.legend(frameon=False, fontsize=8.5); ax.set_ylim(0, 80)
save(fig, "a194_trend.png")
