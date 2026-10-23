"""W2：ブリ類は北で獲れるようになったか（1956〜2024年）
都道府県別ぶり類漁獲量の地域別割合、漁獲量で重みをつけた県庁所在地の緯度の平均（重心緯度）、
日本近海の海面水温（気象庁）との相関（水準と前年差）"""
from common import *


def main():
    d = pref()
    d["region"] = d.pref.map(REGION)
    d["lat"] = d.pref.map(LAT)
    w = d.pivot_table(index="year", columns="pref", values="ぶり類", aggfunc="sum")
    tot = w.sum(axis=1, min_count=1)
    nat = national()["ぶり類"]
    reg = d.pivot_table(index="year", columns="region", values="ぶり類", aggfunc="sum")[REGIONS]
    share = reg.div(reg.sum(axis=1), axis=0)
    cen = (w * pd.Series(LAT)).sum(axis=1) / w.sum(axis=1)
    out = pd.DataFrame({"national_t": nat, "pref_sum_t": tot, "centroid_lat": cen})
    out = out.join(share.add_prefix("share_")).join(reg.add_prefix("t_"))
    out.to_csv(RES / "w2_buri_by_year.csv")

    # 期間平均
    per = {"1956-1965": (1956, 1965), "1966-1975": (1966, 1975), "1976-1985": (1976, 1985), "1986-1995": (1986, 1995),
           "1996-2005": (1996, 2005), "2006-2015": (2006, 2015), "2016-2024": (2016, 2024)}
    rows = []
    for k, (a, b) in per.items():
        s = out.loc[a:b]
        rows.append({"period": k, "national_t_mean": s.national_t.mean(), "centroid_lat_mean": s.centroid_lat.mean(),
                     **{f"share_{r}": reg.loc[a:b, r].sum() / reg.loc[a:b].sum().sum() for r in REGIONS}})
    pr = pd.DataFrame(rows)
    pr.to_csv(RES / "w2_buri_periods.csv", index=False)

    # 都道府県：1956〜65年平均と2015〜24年平均の上位
    a = w.loc[1956:1965].mean(); b = w.loc[2015:2024].mean()
    pt = pd.DataFrame({"t_1956_65": a, "t_2015_24": b, "share_1956_65": a / a.sum(), "share_2015_24": b / b.sum(),
                       "ratio": b / a}).sort_values("t_2015_24", ascending=False)
    pt.to_csv(RES / "w2_buri_pref.csv")

    # 傾き（10年あたり）
    def slope(s):
        s = s.dropna(); x = s.index.values.astype(float)
        bb = np.polyfit(x, s.values, 1)[0]
        return bb * 10
    # 海面水温との相関
    sst_ = sst()
    j = out.join(sst_, how="inner").loc[1956:2024]
    hok = j["share_北海道"]
    cr = []
    for area in ["日本近海平均", "日本海中部", "日本海北東部", "三陸沖"]:
        for name, s in [("centroid_lat", j.centroid_lat), ("share_北海道", hok),
                        ("share_北海道+東北", j["share_北海道"] + j["share_東北"])]:
            m = s.notna() & j[area].notna()
            r_lvl = np.corrcoef(s[m], j[area][m])[0, 1]
            ds, dt = s.diff(), j[area].diff()
            m2 = ds.notna() & dt.notna()
            r_dif = np.corrcoef(ds[m2], dt[m2])[0, 1]
            # 直線トレンドを除いた残差の相関
            x = s.index.values.astype(float)
            rs = s[m] - np.polyval(np.polyfit(x[m], s[m], 1), x[m])
            rt = j[area][m] - np.polyval(np.polyfit(x[m], j[area][m], 1), x[m])
            cr.append({"sst_area": area, "series": name, "n": int(m.sum()), "r_level": r_lvl, "r_diff": r_dif,
                       "r_detrended": np.corrcoef(rs, rt)[0, 1]})
    cr = pd.DataFrame(cr)
    cr.to_csv(RES / "w2_buri_sst_corr.csv", index=False)
    sl = {"centroid_lat_per10y_1956_2024": slope(out.centroid_lat.loc[1956:2024]),
          "centroid_lat_per10y_1990_2024": slope(out.centroid_lat.loc[1990:2024]),
          "share_hokkaido_per10y_1990_2024": slope(out["share_北海道"].loc[1990:2024]),
          "sst_japan_per10y_1956_2024": slope(sst_["日本近海平均"].loc[1956:2024])}
    pd.Series(sl).to_csv(RES / "w2_slopes.csv", header=["value"])

    # 図1：地域別の割合（積み上げ）と全国漁獲量
    fig, ax = plt.subplots(figsize=(9, 4.8))
    cols = [BLUE, LIGHT, GREEN, PURPLE, GRAY, ORANGE]
    ax.stackplot(share.index, *(share[r] * 100 for r in REGIONS), colors=cols, labels=REGIONS, alpha=0.9)
    ax.set_ylim(0, 100); ax.set_xlim(1956, 2024)
    ax.set_ylabel("ぶり類漁獲量に占める割合（%）")
    ax.set_title("ブリ類の漁獲量：どの地域で獲れているか（1956〜2024年）", loc="left")
    ax.legend(loc="upper left", fontsize=9, frameon=False, ncol=6, bbox_to_anchor=(0, -0.08))
    save(fig, "w2_share.png")

    # 図2：重心緯度と全国漁獲量
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(out.index, out.centroid_lat, color=BLUE, lw=1.6, label="重心の緯度（左軸）")
    ax.set_ylabel("北緯（度）")
    ax2 = ax.twinx()
    ax2.bar(out.index, out.national_t / 1e4, color=GRAY, alpha=0.35, width=0.8, label="全国の漁獲量（右軸）")
    ax2.set_ylabel("万トン"); ax2.spines["top"].set_visible(False)
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    ax.set_title("ブリ類の漁獲量で重みをつけた「重心」の緯度", loc="left")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9)
    save(fig, "w2_centroid.png")

    # 図3：海面水温と北海道の割合
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax = axes[0]
    ax.plot(j.index, j["日本近海平均"], color=ORANGE, lw=1.4)
    ax.set_ylabel("海面水温の平年差（℃）", color=ORANGE)
    ax.set_title("日本近海の海面水温と、北海道の割合", loc="left", fontsize=12)
    a2 = ax.twinx(); a2.plot(j.index, hok * 100, color=BLUE, lw=1.4); a2.set_ylabel("北海道の割合（%）", color=BLUE)
    a2.spines["top"].set_visible(False)
    ax = axes[1]
    ds, dt = hok.diff() * 100, j["日本近海平均"].diff()
    ax.scatter(dt, ds, s=14, color=BLUE, alpha=0.7)
    r = cr[(cr.sst_area == "日本近海平均") & (cr.series == "share_北海道")].iloc[0]
    ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
    ax.set_xlabel("海面水温の前年差（℃）"); ax.set_ylabel("北海道の割合の前年差（ポイント）")
    ax.set_title(f"前年差どうし：相関 {r.r_diff:.2f}", loc="left", fontsize=12)
    fig.tight_layout()
    save(fig, "w2_sst.png")

    print(out.loc[[1956, 1965, 1975, 1985, 1995, 2005, 2010, 2011, 2012, 2013, 2014, 2015, 2020, 2024]].round(3).to_string())
    print(pr.round(3).to_string()); print(pt.head(12).round(3).to_string()); print(cr.round(3).to_string()); print(sl)
    print("pref_sum vs national max abs diff:", (out.national_t - out.pref_sum_t).abs().sort_values().tail(5))


if __name__ == "__main__":
    main()
