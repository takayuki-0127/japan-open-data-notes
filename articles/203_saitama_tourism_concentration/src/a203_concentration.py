"""A203 観光客は、少数の市町村に集中しているか（埼玉県・市町村別観光入込客数）"""
from common import *

d = load()
w = d.pivot(index="muni", columns="year", values="total")
yrs = list(w.columns)
rows = []
for y in yrs:
    s = w[y].sort_values(ascending=False); tot = s.sum()
    sp = d[d.year == y]; 
    rows.append({"year": y, "total": tot, "spot": sp.spot.sum(), "event": sp.event.sum(),
                 "top1": s.index[0], "top1_share": s.iloc[0] / tot * 100,
                 "top5_share": s.head(5).sum() / tot * 100, "top10_share": s.head(10).sum() / tot * 100,
                 "gini": gini(s.values), "gini_ex_top1": gini(s.values[1:]),
                 "n_half": int((s.cumsum() / tot < 0.5).sum() + 1)})
c = pd.DataFrame(rows).set_index("year")
c.round(3).to_csv(RES / "concentration_by_year.csv")

s25 = w[2025].sort_values(ascending=False)
rk = pd.DataFrame({"total2025": s25, "share2025": s25 / s25.sum() * 100, "total2019": w[2019], "total2021": w[2021]})
rk = rk.loc[s25.index]
rk["chg19_25"] = (rk.total2025 / rk.total2019 - 1) * 100
rk.round(2).to_csv(RES / "muni_2025.csv")

# spot vs event, 2019 / 2021 / 2025
se = d[d.year.isin([2019, 2020, 2021, 2022, 2023, 2024, 2025])].groupby("year")[["spot", "event", "total"]].sum()
se.to_csv(RES / "spot_event_2019_2025.csv")

with open(RES / "summary.txt", "w") as f:
    f.write(c.round(3).to_string() + "\n\n")
    f.write("2025 top10:\n" + rk.head(10).round(2).to_string() + "\n\n")
    f.write(f"2025 bottom5: {[(k, int(v)) for k, v in s25.tail(5).items()]}\n")
    f.write(f"2025 median muni {s25.median():.0f}\n")
    f.write(f"munis below 2019 in 2025: {(rk.chg19_25 < 0).sum()} of {rk.chg19_25.notna().sum()}\n")
    for y in (2019, 2020, 2021, 2025):
        f.write(f"{y} spot {se.loc[y,'spot']:.0f} event {se.loc[y,'event']:.0f} total {se.loc[y,'total']:.0f}\n")
    f.write(f"event 2019->2021 {(se.loc[2021,'event']/se.loc[2019,'event']-1)*100:.1f}% ; ->2025 {(se.loc[2025,'event']/se.loc[2019,'event']-1)*100:.1f}%\n")
    f.write(f"spot 2019->2021 {(se.loc[2021,'spot']/se.loc[2019,'spot']-1)*100:.1f}% ; ->2025 {(se.loc[2025,'spot']/se.loc[2019,'spot']-1)*100:.1f}%\n")
    f.write(f"total 2019->2020 {(se.loc[2020,'total']/se.loc[2019,'total']-1)*100:.1f}% ->2025 {(se.loc[2025,'total']/se.loc[2019,'total']-1)*100:.1f}%\n")
    k = d[d.muni == "越谷市"].set_index("year")
    f.write("越谷市 spot share of its total: " + str((k.spot / k.total * 100).round(1).to_dict()) + "\n")
    sa = d[d.muni == "さいたま市"].set_index("year")
    f.write("さいたま市 event share: " + str((sa.event / sa.total * 100).round(1).to_dict()) + "\n")

# fig1: 2025 ranking top 20 + others
fig, ax = plt.subplots(figsize=(7.5, 7.5))
top = s25.head(20)[::-1] / 1e4
cols = [ORANGE if i >= 19 else (BLUE if i >= 15 else LIGHT) for i in range(20)]
ax.barh(top.index, top.values, color=cols)
for i, (k, v) in enumerate(top.items()):
    ax.text(v + 30, i, f"{v:,.0f}万（{s25[k]/s25.sum()*100:.1f}%）", va="center", fontsize=8)
ax.set_xlabel("観光入込客数（万人回、2025年）"); ax.set_xlim(0, top.max() * 1.3)
ax.set_title(f"埼玉県の観光入込客数 上位20市町村（2025年、計{s25.sum()/1e4:,.0f}万人回）", loc="left")
save(fig, "a203_ranking.png")

# fig2: concentration over time
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(c.index, c.top1_share, color=ORANGE, marker="o", label="1位（越谷市）の割合")
ax.plot(c.index, c.top5_share, color=BLUE, marker="o", label="上位5市町村の割合")
ax.plot(c.index, c.top10_share, color=GREEN, marker="o", label="上位10市町村の割合")
for col, dy in (("top1_share", 2), ("top5_share", 2), ("top10_share", 2)):
    ax.text(2025.2, c.loc[2025, col], f"{c.loc[2025, col]:.1f}%", va="center", fontsize=9)
    ax.text(2010.8, c.loc[2011, col], f"{c.loc[2011, col]:.1f}%", va="center", ha="right", fontsize=9)
ax.axvspan(2019.5, 2021.5, color=GRAY, alpha=0.15); ax.text(2020.5, 8, "コロナ禍", ha="center", fontsize=9, color=GRAY)
ax.set_ylim(0, 100); ax.set_xlim(2009.8, 2026.3); ax.set_ylabel("県全体に占める割合（%）")
ax.set_xticks(range(2011, 2026, 2)); ax.legend(loc="upper left", fontsize=9, frameon=False, ncol=3)
ax.set_title("63市町村のうち上位が占める割合", loc="left")
save(fig, "a203_share.png")

# fig3: spot vs event index (2019=100)
fig, ax = plt.subplots(figsize=(8, 4.6))
a = d.groupby("year")[["spot", "event"]].sum()
ax.plot(a.index, a.spot / 1e6, color=BLUE, marker="o", label="観光地点")
ax.plot(a.index, a.event / 1e6, color=ORANGE, marker="o", label="イベント")
for col in ("spot", "event"):
    for y in (2019, 2021, 2025):
        ax.text(y, a.loc[y, col] / 1e6 + 4, f"{a.loc[y, col]/1e6:.1f}", ha="center", fontsize=8.5)
ax.set_ylabel("観光入込客数（百万人回）"); ax.set_ylim(0, 160); ax.set_xticks(range(2011, 2026, 2))
ax.legend(frameon=False, loc="center left")
ax.set_title("観光地点とイベントの入込客数（川越市は内訳がなく含めていない）", loc="left", fontsize=12)
save(fig, "a203_spot_event.png")
print(open(RES / "summary.txt").read())
