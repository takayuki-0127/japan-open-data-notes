"""黄砂の観測日数は、2000年代から減ったのか（気象庁 黄砂のデータ集、11地点、1967〜2023年）"""
from common import *

d = load("kosa_days_monthly.csv").set_index("year").loc[1967:2023]   # 2024年は3月26日で観測終了のため除く
n = load("kosa_station_days_monthly.csv").set_index("year").loc[1967:2023]
s = load("station_days_by_year.csv").set_index("year").loc[1967:2023]
ST = ["札幌", "仙台", "新潟", "東京", "名古屋", "大阪", "広島", "高松", "福岡", "鹿児島", "那覇"]
P = {"1967-79": (1967, 1979), "1980-89": (1980, 1989), "1990-99": (1990, 1999), "2000-10": (2000, 2010), "2011-23": (2011, 2023)}
L = []
rows = []
for k, (a, b) in P.items():
    r = dict(period=k, days=d.loc[a:b, "total"].mean(), station_days=n.loc[a:b, "total"].mean(),
             spring_share=d.loc[a:b, ["m3", "m4", "m5"]].sum().sum() / d.loc[a:b, "total"].sum())
    rows.append(r)
    L.append(f"{k}: 年平均 {r['days']:.1f}日 のべ {r['station_days']:.1f}日 3〜5月の割合 {r['spring_share']:.0%}")
pr = pd.DataFrame(rows); pr.to_csv(RES / "a150_period_means.csv", index=False, encoding="utf-8")
top = d.total.sort_values(ascending=False).head(8)
L.append("多かった年: " + ", ".join(f"{y} {v}日" for y, v in top.items()))
L.append(f"20日以上の年: 2000-10 {(d.loc[2000:2010,'total']>=20).sum()}/11年, 2011-23 {(d.loc[2011:2023,'total']>=20).sum()}/13年, 1967-99 {(d.loc[1967:1999,'total']>=20).sum()}/33年")
L.append(f"平年値（1991-2020）15.8日。2011-23で平年値を上回った年: {(d.loc[2011:2023,'total']>15.8).sum()}年（{list(d.loc[2011:2023][d.loc[2011:2023,'total']>15.8].index)}）")
# 地点別：年平均観測日数
a1, a2 = s.loc[2000:2010, ST].mean(), s.loc[2011:2023, ST].mean()
a0 = s.loc[1967:1999, ST].mean()
st = pd.DataFrame({"1967-99": a0, "2000-10": a1, "2011-23": a2}).round(2)
st["change_2000_10_to_2011_23"] = (a2 / a1 - 1).round(3)
st.to_csv(RES / "a150_station_means.csv", encoding="utf-8")
for k in ST:
    L.append(f"{k}: 1967-99 {a0[k]:.1f} / 2000-10 {a1[k]:.1f} / 2011-23 {a2[k]:.1f} 日/年")
(RES / "a150_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1 年ごとの観測日数
fig, ax = plt.subplots(figsize=(9.5, 4.6))
cols = [ORANGE if 2000 <= y <= 2010 else BLUE for y in d.index]
ax.bar(d.index, d.total, color=cols, width=0.8)
ax.plot(d.index, d.total.rolling(5, center=True).mean(), color=INK, lw=1.6, label="5年移動平均")
ax.axhline(15.8, color=GRAY, lw=1, ls="--"); ax.text(1967, 16.6, "平年値 15.8日（1991〜2020年）", color=GRAY, fontsize=9)
for y in [2001, 2002, 2010]:
    ax.text(y, d.loc[y, "total"] + 0.6, f"{d.loc[y,'total']}", ha="center", fontsize=8.5, color=ORANGE)
ax.set_ylabel("黄砂観測日数（日）"); ax.set_xlabel("年"); ax.set_xlim(1965.5, 2024)
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 0.93), fontsize=9)
ax.set_title("黄砂を観測した日数（11地点のどこかで観測した日）")
save(fig, "a150_days.png")

# 図2 期間ごとの年平均（観測日数とのべ日数）
fig, ax = plt.subplots(figsize=(9.5, 4.4))
x = np.arange(len(pr)); w = 0.38
b1 = ax.bar(x - w/2, pr.days, w, color=BLUE, label="観測日数（どこかで観測した日）")
b2 = ax.bar(x + w/2, pr.station_days, w, color=LIGHT, label="のべ日数（地点ごとの日数の合計）")
for xi, v in zip(x - w/2, pr.days): ax.text(xi, v + 1, f"{v:.1f}", ha="center", fontsize=9)
for xi, v in zip(x + w/2, pr.station_days): ax.text(xi, v + 1, f"{v:.1f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([k.replace("-", "〜") + "年" for k in pr.period])
ax.set_ylabel("1年あたりの日数（年平均）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("期間ごとの年平均：2000〜2010年が多く、2011年以降は1990年代を下回る")
save(fig, "a150_periods.png")

# 図3 地点別
fig, ax = plt.subplots(figsize=(9.5, 4.6))
x = np.arange(len(ST)); w = 0.27
ax.bar(x - w, a0, w, color=GRAY, label="1967〜1999年")
ax.bar(x, a1, w, color=ORANGE, label="2000〜2010年")
ax.bar(x + w, a2, w, color=BLUE, label="2011〜2023年")
ax.set_xticks(x); ax.set_xticklabels(ST)
ax.set_ylabel("1年あたりの観測日数（年平均）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("地点別の年平均観測日数：西日本ほど多く、2011年以降は多くの地点で1999年以前の水準に")
save(fig, "a150_stations.png")
