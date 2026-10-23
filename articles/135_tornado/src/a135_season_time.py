"""竜巻は何月の何時ごろに多いのか（2007〜2025年、陸上で確認された竜巻）"""
from common import *

d = load()
d.to_csv(DATA / "events.csv", index=False)
Y0, Y1 = 2007, 2025
all_t = tornado(d, land_only=False)
t = tornado(d)
tp = t[(t.year >= Y0) & (t.year <= Y1)]
allp = all_t[(all_t.year >= Y0) & (all_t.year <= Y1)]
sea = allp[allp.place == 3]
n_years = Y1 - Y0 + 1

# --- 年別の確認数（1961〜2025）：統計方法が変わった年に線を引く
yr = pd.DataFrame({"陸上など": t[t.year <= Y1].groupby("year").size(),
                   "水上（上陸せず）": all_t[(all_t.place == 3) & (all_t.year <= Y1)].groupby("year").size()}).fillna(0).astype(int)
yr = yr.reindex(range(1961, Y1 + 1), fill_value=0)
yr.to_csv(RES / "a135_yearly.csv")

# --- 月別・時刻別
mon = pd.DataFrame({"陸上など": tp.groupby("month").size(), "水上（上陸せず）": sea.groupby("month").size()}).reindex(range(1, 13), fill_value=0).fillna(0).astype(int)
mon["陸上など_年平均"] = (mon["陸上など"] / n_years).round(2)
mon.to_csv(RES / "a135_monthly.csv")
hr = tp.dropna(subset=["hour"]).groupby("hour").size().reindex(range(24), fill_value=0)
hr.to_csv(RES / "a135_hourly.csv", header=["件数"])
bins = [0, 3, 6, 9, 12, 15, 18, 21, 24]
labels = ["0-2時", "3-5時", "6-8時", "9-11時", "12-14時", "15-17時", "18-20時", "21-23時"]
h = tp.dropna(subset=["hour", "month"]).copy()
h["slot"] = pd.cut(h.hour, bins, right=False, labels=labels)
hm = h.pivot_table(index="month", columns="slot", values="id", aggfunc="count", observed=False).reindex(range(1, 13)).fillna(0).astype(int)
hm.to_csv(RES / "a135_month_x_time.csv")

# --- 季節ごとの時刻の違い（8〜10月 と それ以外）
h["season"] = np.where(h.month.isin([8, 9, 10]), "8〜10月", "それ以外")
day_share = h.assign(day=h.hour.between(9, 17)).groupby("season")["day"].mean()

lines = []
lines.append(f"期間 {Y0}〜{Y1}年（{n_years}年）陸上などの竜巻 {len(tp)}件（年平均 {len(tp)/n_years:.1f}件）、水上で上陸せず {len(sea)}件")
lines.append("月別（陸上など）: " + ", ".join(f"{m}月{v}" for m, v in mon["陸上など"].items()))
aug_oct = mon.loc[[8, 9, 10], "陸上など"].sum() / mon["陸上など"].sum()
lines.append(f"8〜10月の割合 {aug_oct:.1%}、7〜11月 {mon.loc[7:11,'陸上など'].sum()/mon['陸上など'].sum():.1%}")
lines.append("時刻別: " + ", ".join(f"{k}時{v}" for k, v in hr.items()))
lines.append(f"9〜17時台の割合 {tp.hour.between(9,17).sum()/tp.hour.notna().sum():.1%}、12〜17時台 {tp.hour.between(12,17).sum()/tp.hour.notna().sum():.1%}")
lines.append("季節別 9〜17時台の割合: " + ", ".join(f"{k} {v:.1%}" for k, v in day_share.items()))
lines.append("水上（上陸せず）月別: " + ", ".join(f"{m}月{v}" for m, v in mon["水上（上陸せず）"].items()))
lines.append(f"1991〜2006年 陸上など年平均 {yr.loc[1991:2006,'陸上など'].mean():.1f}、2007〜2025年 {yr.loc[2007:2025,'陸上など'].mean():.1f}；1961〜1990年 {yr.loc[1961:1990,'陸上など'].mean():.1f}")
lines.append(f"2008年 陸上など {yr.loc[2008,'陸上など']}、水上 {yr.loc[2008,'水上（上陸せず）']}")
(RES / "a135_summary.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))

# 図1：月×時間帯のヒートマップ
fig, ax = plt.subplots(figsize=(8.2, 5.2))
im = ax.imshow(hm.values, cmap="Blues", aspect="auto")
ax.set_xticks(range(len(labels)), labels, fontsize=9)
ax.set_yticks(range(12), [f"{m}月" for m in range(1, 13)])
for i in range(12):
    for j in range(len(labels)):
        v = hm.values[i, j]
        if v:
            ax.text(j, i, v, ha="center", va="center", fontsize=8.5, color="white" if v >= hm.values.max() * 0.55 else INK)
ax.set_title(f"竜巻は8〜10月の昼過ぎに多い（{Y0}〜{Y1}年、陸上などの竜巻 {len(tp)}件）", loc="left")
ax.spines[:].set_visible(False)
fig.colorbar(im, ax=ax, shrink=0.7, label="件数")
save(fig, "a135_heatmap.png")

# 図2：月別（陸上など・水上）と時刻別
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
x = np.arange(1, 13)
ax.bar(x - 0.2, mon["陸上など"], 0.4, color=BLUE, label="陸上など")
ax.bar(x + 0.2, mon["水上（上陸せず）"], 0.4, color=LIGHT, label="水上で発生し上陸せず")
ax.set_xticks(x, [f"{m}" for m in x]); ax.set_xlabel("月"); ax.set_ylabel("件数（19年の合計）")
ax.set_title("月別：陸上は9月、海上は9〜10月が最多", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9)
ax = axes[1]
ax.bar(hr.index, hr.values, color=BLUE)
ax.set_xticks(range(0, 24, 3)); ax.set_xlabel("発生した時刻（時台）"); ax.set_ylabel("件数（19年の合計）")
ax.set_title("時刻別：11〜17時台に多い", loc="left", fontsize=12)
save(fig, "a135_month_hour.png")

# 図3：年別の確認数と統計方法の変更
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.bar(yr.index, yr["陸上など"], color=BLUE, label="陸上など")
ax.bar(yr.index, yr["水上（上陸せず）"], bottom=yr["陸上など"], color=LIGHT, label="水上で発生し上陸せず")
for y, txt in [(1991, "1991年 調査体制を強化"), (2007, "2007年 さらに強化")]:
    ax.axvline(y - 0.5, color=ORANGE, lw=1.2, ls="--")
    ax.text(y - 0.3, ax.get_ylim()[1] * 0.92, txt, color=ORANGE, fontsize=9)
ax.set_ylabel("竜巻の確認数（件）")
ax.set_title("2007年から確認数が増えたのは主に海上の竜巻（調べ方が変わったので、年の増減は比べられない）", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a135_yearly.png")
