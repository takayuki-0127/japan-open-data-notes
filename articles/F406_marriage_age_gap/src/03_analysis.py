"""年齢差の推移・分布・分解・頑健性・問い直し。結果を results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
YEARS = [1995, 2005, 2015, 2025]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def wgroup(a):
    return np.select([a <= 24, a <= 29, a <= 34, a <= 39], ["〜24歳", "25〜29歳", "30〜34歳", "35〜39歳"], "40歳以上")


GORDER = ["〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40歳以上"]


def shift_share(c, y0, y1, key="wife_age", flag="wife_older", trim=None):
    d = c[c.year.isin([y0, y1])].copy()
    if trim:
        d = d[(d.wife_age >= trim[0]) & (d.wife_age <= trim[1])]
    d["g"] = wgroup(d[key].values)
    t = d.groupby(["year", "g"]).apply(lambda x: pd.Series({"n": x.n.sum(), "k": (x.n * x[flag]).sum()}), include_groups=False)
    t = t.reset_index()
    t["share"] = t.n / t.groupby("year").n.transform("sum")
    t["rate"] = t.k / t.n
    a = t[t.year == y0].set_index("g").reindex(GORDER).fillna(0)
    b = t[t.year == y1].set_index("g").reindex(GORDER).fillna(0)
    tot0 = (a.share * a.rate).sum(); tot1 = (b.share * b.rate).sum()
    comp = ((b.share - a.share) * (a.rate + b.rate) / 2).sum()
    within = ((b.rate - a.rate) * (a.share + b.share) / 2).sum()
    return dict(y0=y0, y1=y1, key=key, p0=tot0 * 100, p1=tot1 * 100, change=(tot1 - tot0) * 100,
                composition=comp * 100, within=within * 100, within_share=within / (tot1 - tot0) * 100)


def main():
    g = pd.read_csv(DATA / "gap_dist.csv")
    m = pd.read_csv(DATA / "mean_age.csv").set_index("year")
    c = pd.read_csv(DATA / "cross_first.csv")
    c["d"] = c.husband_age - c.wife_age
    c["wife_older"] = (c.d < 0).astype(int)
    c["same"] = (c.d == 0).astype(int)
    c["h7"] = (c.d >= 7).astype(int)

    # 1) 第9.14表：区分別の割合
    tot = g[(g.parent == "総数")].set_index("year").n
    def part(parent, subs=None):
        x = g[g.parent == parent]
        x = x[x["sub"] == "計"] if subs is None else x[x["sub"].isin(subs)]
        return x.groupby("year").n.sum() / tot * 100
    dist = pd.DataFrame({
        "total": tot,
        "wife_older": part("妻年上"),
        "same": part("夫妻同年齢"),
        "h1_3": part("夫年上", ["1歳", "2歳", "3歳"]),
        "h4_6": part("夫年上", ["4歳", "5歳", "6歳"]),
        "h7p": part("夫年上", ["7歳以上"]),
        "w4p": part("妻年上", ["4歳以上"]),
    }).round(3)
    dist.index.name = "year"
    dist.to_csv(RES / "gap_dist_share.csv")

    # 2) 第9.11表：平均の年齢差（初婚）
    mm = m.loc[1947:, ["first_h", "first_w", "gap_first", "all_h", "all_w", "gap_all"]]
    mm.to_csv(RES / "mean_age_gap.csv")
    gmin_year = int(mm.gap_first.idxmin())

    # 3) 中巻：差の平均・中央値・標準偏差、妻の年齢別の割合
    stats = []
    for y in YEARS:
        x = c[c.year == y]
        w = x.n.values; d = x.d.values
        order = np.argsort(d, kind="stable"); cw = np.cumsum(w[order])
        med = d[order][np.searchsorted(cw, cw[-1] / 2)]
        mean = np.average(d, weights=w); sd = np.sqrt(np.average((d - mean) ** 2, weights=w))
        stats.append(dict(year=y, n=int(w.sum()), mean_diff=round(mean, 3), median_diff=int(med), sd_diff=round(sd, 3),
                          mean_h=round(np.average(x.husband_age, weights=w), 3), mean_w=round(np.average(x.wife_age, weights=w), 3),
                          wife_older=round((w * x.wife_older).sum() / w.sum() * 100, 3),
                          same=round((w * x.same).sum() / w.sum() * 100, 3), h7=round((w * x.h7).sum() / w.sum() * 100, 3)))
    stats = pd.DataFrame(stats)
    stats.to_csv(RES / "cross_stats.csv", index=False)

    c["g"] = wgroup(c.wife_age.values)
    by = c.groupby(["year", "g"]).apply(lambda x: pd.Series({
        "n": x.n.sum(), "wife_older": (x.n * x.wife_older).sum() / x.n.sum() * 100,
        "same": (x.n * x.same).sum() / x.n.sum() * 100, "h7": (x.n * x.h7).sum() / x.n.sum() * 100,
        "mean_diff": np.average(x.d, weights=x.n)}), include_groups=False).reset_index()
    by["share_of_year"] = by.n / by.groupby("year").n.transform("sum") * 100
    by["g"] = pd.Categorical(by.g, GORDER, ordered=True)
    by = by.sort_values(["year", "g"]).round(3)
    by.to_csv(RES / "by_wife_age.csv", index=False)

    # 4) 分解
    main_ss = shift_share(c, 1995, 2025)
    rob = [dict(check="0 主：1995→2025年、妻の年齢5区分", **main_ss)]
    rob.append(dict(check="1a 2005→2025年", **shift_share(c, 2005, 2025)))
    rob.append(dict(check="1b 1995→2015年", **shift_share(c, 1995, 2015)))
    rob.append(dict(check="2 区分を夫の年齢に", **shift_share(c, 1995, 2025, key="husband_age")))
    rob.append(dict(check="4 妻20〜44歳に限る", **shift_share(c, 1995, 2025, trim=(20, 44))))
    rob = pd.DataFrame(rob)
    rob[[k for k in rob.columns if k not in ("check", "key", "y0", "y1")]] = rob[[k for k in rob.columns if k not in ("check", "key", "y0", "y1")]].round(3)
    rob.to_csv(RES / "decomposition.csv", index=False)

    # 問い直し：夫7歳以上年上の分解（同じ方法）
    h7_ss = shift_share(c, 1995, 2025, flag="h7")

    b25 = by[by.year == 2025].set_index("g")
    seq = [b25.loc[k, "wife_older"] for k in GORDER[:4]]
    M = {
        "gap_first_1970": r(m.loc[1970, "gap_first"], 1), "gap_first_2025": r(m.loc[2025, "gap_first"], 1),
        "gap_first_1950": r(m.loc[1950, "gap_first"], 1), "gap_first_1990": r(m.loc[1990, "gap_first"], 1),
        "gap_first_2005": r(m.loc[2005, "gap_first"], 1), "gap_first_2015": r(m.loc[2015, "gap_first"], 1),
        "gap_first_min_year": gmin_year, "gap_first_min": r(mm.gap_first.min(), 1),
        "first_h_1970": r(m.loc[1970, "first_h"], 1), "first_w_1970": r(m.loc[1970, "first_w"], 1),
        "first_h_2025": r(m.loc[2025, "first_h"], 1), "first_w_2025": r(m.loc[2025, "first_w"], 1),
        "gap_all_1970": r(m.loc[1970, "gap_all"], 1), "gap_all_2025": r(m.loc[2025, "gap_all"], 1),
        "H1_shrink": r(m.loc[1970, "gap_first"] - m.loc[2025, "gap_first"], 1),
        "wife_older_1970": r(dist.loc[1970, "wife_older"], 1), "wife_older_1995": r(dist.loc[1995, "wife_older"], 1),
        "wife_older_2025": r(dist.loc[2025, "wife_older"], 1),
        "H2_ratio": r(dist.loc[2025, "wife_older"] / dist.loc[1970, "wife_older"], 2),
        "same_1970": r(dist.loc[1970, "same"], 1), "same_2025": r(dist.loc[2025, "same"], 1),
        "h7p_1970": r(dist.loc[1970, "h7p"], 1), "h7p_1975": r(dist.loc[1975, "h7p"], 1), "h7p_1985": r(dist.loc[1985, "h7p"], 1), "h7p_2015": r(dist.loc[2015, "h7p"], 1),
        "h7p_2025": r(dist.loc[2025, "h7p"], 1),
        "h1_3_1970": r(dist.loc[1970, "h1_3"], 1), "h1_3_2025": r(dist.loc[2025, "h1_3"], 1),
        "h4_6_1970": r(dist.loc[1970, "h4_6"], 1), "h4_6_2025": r(dist.loc[2025, "h4_6"], 1),
        "husband_older_1970": r(100 - dist.loc[1970, "wife_older"] - dist.loc[1970, "same"], 1),
        "husband_older_2025": r(100 - dist.loc[2025, "wife_older"] - dist.loc[2025, "same"], 1),
        "w4p_1970": r(dist.loc[1970, "w4p"], 1), "w4p_2025": r(dist.loc[2025, "w4p"], 1),
        "cross": stats.set_index("year").to_dict(orient="index"),
        "decomp_main": {k: (r(v, 2) if isinstance(v, float) else v) for k, v in main_ss.items()},
        "decomp_h7": {k: (r(v, 2) if isinstance(v, float) else v) for k, v in h7_ss.items()},
        "H3_within_share": r(main_ss["within_share"], 1),
        "wife_older_by_age_2025": {k: r(b25.loc[k, "wife_older"], 1) for k in GORDER},
        "wife_older_by_age_1995": {k: r(by[(by.year == 1995)].set_index("g").loc[k, "wife_older"], 1) for k in GORDER},
        "h7_by_age_2025": {k: r(b25.loc[k, "h7"], 1) for k in GORDER},
        "h7_by_age_1995": {k: r(by[(by.year == 1995)].set_index("g").loc[k, "h7"], 1) for k in GORDER},
        "share_age_1995": {k: r(by[(by.year == 1995)].set_index("g").loc[k, "share_of_year"], 1) for k in GORDER},
        "share_age_2025": {k: r(b25.loc[k, "share_of_year"], 1) for k in GORDER},
        "H4_monotone": bool(all(np.diff(seq) > 0)),
        "judge": {
            "H1": "支持" if m.loc[1970, "gap_first"] - m.loc[2025, "gap_first"] >= 1.0 else "外れ",
            "H2": "支持" if dist.loc[2025, "wife_older"] / dist.loc[1970, "wife_older"] >= 2 else "外れ",
            "H3": "支持" if main_ss["within_share"] >= 50 else "外れ",
            "H4": "支持" if all(np.diff(seq) > 0) else "外れ",
        },
    }
    (RES / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(M, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print(by.to_string())


if __name__ == "__main__":
    main()
