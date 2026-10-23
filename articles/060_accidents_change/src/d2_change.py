"""D2：2019年と2025年で、人身事故はどこで・誰の事故が減ったのか。死亡事故はどこで起きているのか。
件数の変化を「第1当事者の年齢 × 事故の相手」に分解し、時間帯×曜日の分布と、死亡事故の地図（六角形の密度）を描く"""
from common import *

a, b = load(2019), load(2025)
tot = pd.Series({"2019": len(a), "2025": len(b)}); fat = pd.Series({"2019": a.fatal.sum(), "2025": b.fatal.sum()})
# 1) 第1当事者の年齢・事故の相手（第2当事者）別の件数変化
key = lambda d: d.ageA.where(d.ageA != "不明")
ch = pd.DataFrame({"2019": a.groupby("ageA").size(), "2025": b.groupby("ageA").size()}).drop("不明", errors="ignore")
ch["change"] = ch["2025"] - ch["2019"]; ch["pct"] = ch.change / ch["2019"] * 100; ch["share_of_total_change"] = ch.change / ch.change.sum() * 100
ch = ch.loc[["24歳以下", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65〜74歳", "75歳以上"]]; ch.round(2).to_csv(RES / "d2_by_age.csv", encoding="utf-8-sig"); print(ch.round(1))
pb = pd.DataFrame({"2019": a.groupby("partyB").size(), "2025": b.groupby("partyB").size()}).fillna(0)
pb["pct"] = (pb["2025"] / pb["2019"] - 1) * 100; pb.round(2).to_csv(RES / "d2_by_partyB.csv", encoding="utf-8-sig"); print(pb.round(1))
pa = pd.DataFrame({"2019": a.groupby("partyA").size(), "2025": b.groupby("partyA").size()}).fillna(0)
pa["pct"] = (pa["2025"] / pa["2019"] - 1) * 100; pa.round(2).to_csv(RES / "d2_by_partyA.csv", encoding="utf-8-sig"); print(pa.round(1))
# 2) 時間帯×曜日（2025年、全事故と死亡事故）
dows = ["日", "月", "火", "水", "木", "金", "土"]
hm = b.pivot_table(index="dow", columns="hour", values="fatal", aggfunc="size").reindex(range(1, 8)); hm.index = dows
hf = b[b.fatal == 1].pivot_table(index="dow", columns="hour", values="fatal", aggfunc="size").reindex(index=range(1, 8), columns=range(24)).fillna(0); hf.index = dows
hm.to_csv(RES / "d2_hour_dow_all.csv", encoding="utf-8-sig"); hf.to_csv(RES / "d2_hour_dow_fatal.csv", encoding="utf-8-sig")
by_hour = pd.DataFrame({"all": b.groupby("hour").size(), "fatal": b.groupby("hour").fatal.sum()}); by_hour["rate_pct"] = by_hour.fatal / by_hour["all"] * 100
by_hour.round(3).to_csv(RES / "d2_by_hour.csv", encoding="utf-8-sig")
# 3) 都道府県別の死亡事故の割合
pref = b.groupby("pref").agg(n=("fatal", "size"), fatal=("fatal", "sum")); pref["rate_pct"] = pref.fatal / pref.n * 100; pref.round(3).to_csv(RES / "d2_by_pref.csv", encoding="utf-8-sig")
s = {"total_2019": len(a), "total_2025": len(b), "total_pct": (len(b) / len(a) - 1) * 100, "fatal_2019": int(fat["2019"]), "fatal_2025": int(fat["2025"]),
     "fatal_pct": (fat["2025"] / fat["2019"] - 1) * 100, "dead_2025": int(b.dead.sum()),
     "age75_pct": ch.loc["75歳以上", "pct"], "age24_pct": ch.loc["24歳以下", "pct"], "age35_pct": ch.loc["35〜44歳", "pct"],
     "bike_partyA_pct": pa.loc["自転車等", "pct"], "car_partyA_pct": pa.loc["乗用車", "pct"],
     "peak_hour_all": int(by_hour["all"].idxmax()), "peak_rate_hour": int(by_hour.rate_pct.idxmax()), "peak_rate": by_hour.rate_pct.max(),
     "rate_pref_max": b.groupby("pref").fatal.mean().idxmax(), "rate_pref_max_v": pref.rate_pct.max(), "rate_pref_min_v": pref.rate_pct.min()}
pd.Series(s).to_csv(RES / "d2_summary.csv", header=["value"]); print(pd.Series(s))

note = "\n（警察庁の交通事故統計オープンデータの本票。人身事故の件数。第1当事者＝過失が重い側）"
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
x_ = np.arange(len(ch)); w_ = 0.38
axes[0].bar(x_ - w_ / 2, ch["2019"] / 1e3, w_, color=GRAY, label="2019年"); axes[0].bar(x_ + w_ / 2, ch["2025"] / 1e3, w_, color=BLUE, label="2025年")
for xi, p in zip(x_, ch.pct): axes[0].text(xi + w_ / 2, ch["2025"].iloc[xi] / 1e3 + 1, f"{p:+.0f}%", ha="center", fontsize=8.5)
axes[0].set_xticks(x_); axes[0].set_xticklabels(ch.index, fontsize=8.5, rotation=20); axes[0].set_ylabel("件数（千件）"); axes[0].legend(frameon=False)
axes[0].set_title("第1当事者の年齢別", fontsize=11)
pa2 = pa.loc[["乗用車", "貨物車", "自動二輪", "原付等", "自転車等", "歩行者"]]
axes[1].barh(range(len(pa2)), pa2.pct, color=[ORANGE if v > 0 else BLUE for v in pa2.pct]); axes[1].axvline(0, color=GRAY, lw=0.8)
for i, (v, n) in enumerate(zip(pa2.pct, pa2["2025"])): axes[1].text(v + (1 if v >= 0 else -1), i, f"{v:+.0f}%（{int(n):,}件）", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
axes[1].set_yticks(range(len(pa2))); axes[1].set_yticklabels(pa2.index); axes[1].invert_yaxis(); axes[1].set_xlabel("2019→2025年の変化率（%）"); axes[1].set_xlim(-60, 60)
axes[1].set_title("第1当事者の種別", fontsize=11)
fig.suptitle(f"人身事故は{s['total_2019']:,}件→{s['total_2025']:,}件（{s['total_pct']:+.0f}%）。75歳以上と自転車だけが増えた", y=1.03)
fig.text(0.01, -0.07, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "d2_change.png"); plt.close(fig)

fig, axes = plt.subplots(2, 1, figsize=(11, 6.4))
for ax, m_, t_, cm in [(axes[0], hm, "すべての人身事故（件数）", "Blues"), (axes[1], hf, "死亡事故（件数）", "Oranges")]:
    im = ax.imshow(m_.values, aspect="auto", cmap=cm); ax.set_yticks(range(7)); ax.set_yticklabels(m_.index); ax.set_xticks(range(0, 24, 2)); ax.set_xticklabels(range(0, 24, 2))
    ax.set_title(t_, fontsize=11); fig.colorbar(im, ax=ax, shrink=0.8)
axes[1].set_xlabel("時（発生時刻）")
fig.suptitle("事故は平日の朝8時台と夕方17時台に集中。死亡事故は時間帯のばらつきが小さい（2025年）", y=1.0)
fig.text(0.01, -0.03, SOURCE + note, fontsize=7, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "d2_heatmap.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 8.5))
g = b.dropna(subset=["lat", "lon"])
ax.hexbin(g.lon, g.lat, gridsize=160, bins="log", cmap="Greys", mincnt=1, linewidths=0)
f_ = g[g.fatal == 1]; ax.scatter(f_.lon, f_.lat, s=2.5, color=ORANGE, alpha=0.7, label=f"死亡事故（{len(f_):,}件）")
ax.set_xlim(128, 146); ax.set_ylim(30, 46); ax.set_aspect(1.2); ax.set_xlabel("経度"); ax.set_ylabel("緯度"); ax.legend(frameon=False, loc="lower right", markerscale=4)
ax.set_title("2025年の人身事故（灰色の濃さ）と死亡事故（橙の点）")
fig.text(0.01, -0.02, SOURCE + "\n（灰色は六角形ごとの人身事故の件数（対数）。沖縄・離島の一部は範囲外）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "d2_map.png"); plt.close(fig)
