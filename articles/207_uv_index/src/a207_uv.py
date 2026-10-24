"""A207 UVインデックスは何月がピークで、どの地点が高いか"""
from common import *

d = load()
full = d.groupby(["site", "year"]).month.count().unstack(0)
# 札幌・那覇は2018年1月で観測終了 → 3地点がそろう2005〜2017年で平年の形を比べる
base = d[d.year.between(2005, 2017)]
clim = base.groupby(["site", "month"]).uvi.mean().unstack(0)[list(SITES)]
clim.round(2).to_csv(RES / "monthly_climatology_2005_2017.csv")
peak = base.loc[base.groupby(["site", "year"]).uvi.idxmax()].groupby("site").month.value_counts().unstack(fill_value=0)
peak.to_csv(RES / "peak_month_counts_2005_2017.csv")
cat = base.assign(c=pd.cut(base.uvi, [-1, 2.95, 5.95, 7.95, 10.95, 99], labels=["弱い(0-2)", "中程度(3-5)", "強い(6-7)", "非常に強い(8-10)", "極端に強い(11-)"]))
cats = cat.groupby("site").c.value_counts().unstack()[["弱い(0-2)", "中程度(3-5)", "強い(6-7)", "非常に強い(8-10)", "極端に強い(11-)"]]
cats.to_csv(RES / "month_category_counts_2005_2017.csv")
# つくばの長期（2005〜2025年の年平均と7〜8月平均）
tsu = d[(d.site == "tsu") & d.year.between(2005, 2025)]
ty = pd.DataFrame({"annual": tsu.groupby("year").uvi.mean(), "julaug": tsu[tsu.month.isin([7, 8])].groupby("year").uvi.mean()})
ty.round(3).to_csv(RES / "tsukuba_yearly.csv")
sl_a = np.polyfit(ty.index, ty.annual, 1)[0] * 10; sl_s = np.polyfit(ty.index, ty.julaug, 1)[0] * 10
with open(RES / "summary.txt", "w") as f:
    f.write("months per site-year:\n" + full.fillna(0).astype(int).T.to_string() + "\n\n")
    f.write("climatology 2005-2017:\n" + clim.round(2).to_string() + "\n\n")
    f.write("annual mean of monthly values 2005-2017: " + str(clim.mean().round(2).to_dict()) + "\n")
    f.write("max month: " + str({s: (int(clim[s].idxmax()), round(clim[s].max(), 2)) for s in SITES}) + "\n")
    f.write("min month: " + str({s: (int(clim[s].idxmin()), round(clim[s].min(), 2)) for s in SITES}) + "\n")
    f.write("naha/sapporo ratio by month: " + str((clim.nah / clim.sap).round(2).to_dict()) + "\n")
    f.write("naha/tsukuba annual: %.2f, tsukuba/sapporo annual: %.2f\n" % (clim.nah.mean() / clim.tsu.mean(), clim.tsu.mean() / clim.sap.mean()))
    f.write("peak month counts (n years):\n" + peak.to_string() + "\n\n")
    f.write("category counts (months):\n" + cats.to_string() + "\n\n")
    f.write(f"tsukuba annual slope {sl_a:+.3f}/decade, julaug slope {sl_s:+.3f}/decade\n")
    f.write(f"tsukuba julaug mean 2005-2014 {ty.julaug.loc[2005:2014].mean():.2f}, 2016-2025 {ty.julaug.loc[2016:2025].mean():.2f}\n")
    f.write(f"tsukuba annual mean 2005-2014 {ty.annual.loc[2005:2014].mean():.2f}, 2016-2025 {ty.annual.loc[2016:2025].mean():.2f}\n")
    f.write(ty.round(2).to_string() + "\n")
    f.write("tsukuba max monthly values: " + str(tsu.nlargest(5, "uvi")[["year", "month", "uvi"]].values.tolist()) + "\n")
    f.write("naha months >= 10: " + str(base[(base.site == "nah") & (base.uvi >= 10)][["year", "month", "uvi"]].values.tolist()) + "\n")

# fig1 seasonal cycle
fig, ax = plt.subplots(figsize=(8, 4.8))
for s, col in (("nah", ORANGE), ("tsu", BLUE), ("sap", GREEN), ("syo", GRAY)):
    ax.plot(range(1, 13), clim[s], color=col, marker="o", ls="--" if s == "syo" else "-", label=SITES[s])
    m = clim[s].idxmax(); ax.text(m, clim[s].max() + 0.3, f"{clim[s].max():.1f}", ha="center", fontsize=9, color=col)
for y0, y1, lab in ((8, 11, "非常に強い"), (6, 8, "強い"), (3, 6, "中程度")):
    ax.axhspan(y0, y1, color=GRAY, alpha=0.06 if lab != "強い" else 0.12); ax.text(12.6, (y0 + y1) / 2, lab, fontsize=8, color=GRAY, va="center")
ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)]); ax.set_xlim(0.5, 13.4); ax.set_ylim(0, 11)
ax.set_ylabel("日最大UVインデックスの月平均"); ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("月別のUVインデックス（2005〜2017年の平均）", loc="left")
save(fig, "a207_season.png")

# fig2 peak month counts
fig, ax = plt.subplots(figsize=(8, 4.2))
sites3 = ["nah", "tsu", "sap"]; w = 0.27
for i, (s, col) in enumerate(zip(sites3, (ORANGE, BLUE, GREEN))):
    v = peak.loc[s].reindex(range(1, 13), fill_value=0)
    ax.bar(np.arange(1, 13) + (i - 1) * w, v, width=w, color=col, label=SITES[s])
ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)]); ax.set_xlim(4.4, 9.6)
ax.set_ylabel("その月が年間最大だった年数"); ax.legend(frameon=False)
ax.set_title("1年で最もUVインデックスが高かった月（2005〜2017年の13年）", loc="left", fontsize=12)
save(fig, "a207_peak.png")

# fig3 tsukuba long-term
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(ty.index, ty.julaug, color=ORANGE, marker="o", label="7〜8月の平均")
ax.plot(ty.index, ty.annual, color=BLUE, marker="o", label="年平均（12か月の平均）")
for k, col in (("julaug", ORANGE), ("annual", BLUE)):
    b, a = np.polyfit(ty.index, ty[k], 1); ax.plot(ty.index, a + b * ty.index, color=col, lw=1, ls=":")
ax.set_ylim(0, 10); ax.set_xticks(range(2005, 2026, 4)); ax.set_ylabel("日最大UVインデックスの平均"); ax.legend(frameon=False, loc="upper left")
ax.set_title(f"つくばのUVインデックス（2005〜2025年、点線は直線の傾き）", loc="left")
save(fig, "a207_tsukuba.png")
print(open(RES / "summary.txt").read()[1500:5000])
