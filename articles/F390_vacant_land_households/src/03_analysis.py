"""全国の推移、地方別の空き地の割合、相続の割合との相関、政令市とそれ以外、頑健性、問い直し。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
REGIONS = [("北海道", [1]), ("東北", range(2, 8)), ("関東", range(8, 15)), ("中部", range(15, 24)),
           ("近畿", range(24, 31)), ("中国", range(31, 36)), ("四国", range(36, 40)), ("九州・沖縄", range(40, 48))]
VACANT, WILD, TOTAL, INH = "13_利用していない（空き地）", "2_その他（原野など）", "0_総数", "4_相続・贈与で取得"


def r(x, k=3):
    return None if x is None or pd.isna(x) else round(float(x), k)


def main():
    use = pd.read_csv(DATA / "pref_use.csv", dtype={"code": str})
    acq = pd.read_csv(DATA / "pref_acq.csv", dtype={"code": str})
    jp = pd.read_csv(DATA / "japan_long.csv")
    out = {}

    # 1. 全国の推移（空き地＋原野などで定義をそろえる）
    nat = []
    for y in (2008, 2013, 2018, 2023):
        s = jp[jp.year == y].set_index("category")
        tot = s.loc["総数", "lots_total"]
        if y <= 2013:
            un = s.loc["利用していない（空き地・原野など）", "lots_total"]
            va = np.nan
        else:
            va = s.loc["利用していない（空き地）", "lots_total"]
            un = va + s.loc["その他（原野など）", "lots_total"]
        nat.append(dict(year=y, lots_total=tot, unused_lots=un, unused_share=100 * un / tot, vacant_lots=va,
                        vacant_share=100 * va / tot if not pd.isna(va) else np.nan))
    nat = pd.DataFrame(nat)
    nat.to_csv(RES / "japan_trend.csv", index=False)
    out["japan"] = {int(x.year): {k: r(x[k], 2) for k in ["lots_total", "unused_lots", "unused_share", "vacant_lots", "vacant_share"]} for _, x in nat.iterrows()}

    # 2. 都道府県の表（件数）
    pref = use[(use.level == "pref") & (use.code != "00000")].copy()
    pref["pno"] = pref.code.str[:2].astype(int)
    piv = pref.pivot_table(index=["year", "pno", "region"], columns="category", values="lots_total").reset_index()
    pivh = pref.pivot_table(index=["year", "pno"], columns="category", values="hh_total").reset_index()
    aq = acq[(acq.level == "pref") & (acq.code != "00000")].copy()
    aq["pno"] = aq.code.str[:2].astype(int)
    aqp = aq.pivot_table(index=["year", "pno"], columns="category", values="lots_total").reset_index()
    P = piv[["year", "pno", "region", TOTAL, VACANT, WILD]].rename(columns={TOTAL: "lots", VACANT: "vacant", WILD: "wild"})
    P = P.merge(pivh[["year", "pno", TOTAL, VACANT]].rename(columns={TOTAL: "hh", VACANT: "hh_vacant"}), on=["year", "pno"])
    P = P.merge(aqp[["year", "pno", TOTAL, INH]].rename(columns={TOTAL: "lots_acq", INH: "inh"}), on=["year", "pno"])
    P["vacant_share"] = 100 * P.vacant / P.lots
    P["unused_share"] = 100 * (P.vacant + P.wild) / P.lots
    P["hh_vacant_share"] = 100 * P.hh_vacant / P.hh
    P["inh_share"] = 100 * P.inh / P.lots_acq
    P = P.sort_values(["year", "pno"]).reset_index(drop=True)
    P.round(4).to_csv(RES / "prefecture_table.csv", index=False)

    # 3. 地方別（H2）
    reg = []
    for name, nos in REGIONS:
        for y in (2018, 2023):
            s = P[(P.year == y) & (P.pno.isin(list(nos)))]
            reg.append(dict(area=name, year=y, lots=s.lots.sum(), vacant=s.vacant.sum(), wild=s.wild.sum(),
                            hh=s.hh.sum(), hh_vacant=s.hh_vacant.sum(), inh=s.inh.sum(), lots_acq=s.lots_acq.sum()))
    reg = pd.DataFrame(reg)
    reg["vacant_share"] = 100 * reg.vacant / reg.lots
    reg["unused_share"] = 100 * (reg.vacant + reg.wild) / reg.lots
    reg["hh_vacant_share"] = 100 * reg.hh_vacant / reg.hh
    reg["inh_share"] = 100 * reg.inh / reg.lots_acq
    reg.round(4).to_csv(RES / "region_table.csv", index=False)
    rw = reg.pivot(index="area", columns="year", values=["vacant_share", "unused_share", "hh_vacant_share", "vacant", "inh_share"])
    order = [n for n, _ in REGIONS]
    rw = rw.loc[order]
    d_vs = rw[("vacant_share", 2023)] - rw[("vacant_share", 2018)]
    d_us = rw[("unused_share", 2023)] - rw[("unused_share", 2018)]
    d_hs = rw[("hh_vacant_share", 2023)] - rw[("hh_vacant_share", 2018)]
    out["regions"] = {a: dict(vacant_share_2018=r(rw.loc[a, ("vacant_share", 2018)], 2), vacant_share_2023=r(rw.loc[a, ("vacant_share", 2023)], 2),
                              vacant_2018=r(rw.loc[a, ("vacant", 2018)], 0), vacant_2023=r(rw.loc[a, ("vacant", 2023)], 0),
                              inh_share_2023=r(rw.loc[a, ("inh_share", 2023)], 2), d_vacant_share=r(d_vs[a], 2)) for a in order}
    n_down = int((d_vs < 0).sum())

    # 4. 相続の割合との相関（H3）
    def corr(y, excl=None, method="pearson", col="vacant_share"):
        s = P[P.year == y]
        if excl:
            s = s[~s.pno.isin(excl)]
        f = stats.pearsonr if method == "pearson" else stats.spearmanr
        c, p = f(s.inh_share, s[col])
        return float(c), float(p), len(s)
    c23, p23, n23 = corr(2023)
    s23 = P[P.year == 2023]
    slope = np.polyfit(s23.inh_share, s23.vacant_share, 1)
    out["corr_2023"] = dict(r=r(c23), p=r(p23, 4), n=n23, slope=r(slope[0], 3))

    # 5. 政令市とそれ以外（H4）
    cities = use[(use.level == "city")]
    def city_vs_rest(y, col="lots_total"):
        c = cities[cities.year == y]
        cp = c.code.str[:2].unique()
        pr = use[(use.level == "pref") & (use.year == y) & (use.code.str[:2].isin(cp)) & (use.code.str[2:] == "000")]
        ct = c.groupby("category")[col].sum()
        pt = pr.groupby("category")[col].sum()
        rest = pt - ct
        return 100 * ct[VACANT] / ct[TOTAL], 100 * rest[VACANT] / rest[TOTAL], 100 * (ct[VACANT] + ct[WILD]) / ct[TOTAL], 100 * (rest[VACANT] + rest[WILD]) / rest[TOTAL]
    cv = {y: city_vs_rest(y) for y in (2018, 2023)}
    cvh = {y: city_vs_rest(y, "hh_total") for y in (2018, 2023)}
    out["city_vs_rest"] = {str(y): dict(city_vacant_share=r(cv[y][0], 2), rest_vacant_share=r(cv[y][1], 2),
                                         city_unused_share=r(cv[y][2], 2), rest_unused_share=r(cv[y][3], 2),
                                         city_hh_vacant_share=r(cvh[y][0], 2), rest_hh_vacant_share=r(cvh[y][1], 2)) for y in cv}

    # 頑健性
    rob = []
    rob.append(dict(check="0 主：2023年、ピアソン、47都道府県、件数", value=r(c23), note=f"p={p23:.4f}"))
    c, p, _ = corr(2018); rob.append(dict(check="1 2018年で計算", value=r(c), note=f"p={p:.4f}"))
    c, p, _ = corr(2023, method="spearman"); rob.append(dict(check="2a スピアマンの順位相関（2023年）", value=r(c), note=f"p={p:.4f}"))
    c, p, n = corr(2023, excl=[1]); rob.append(dict(check="2b 北海道を除く（2023年、46都府県）", value=r(c), note=f"p={p:.4f}"))
    c, p, _ = corr(2023, col="hh_vacant_share"); rob.append(dict(check="3a 割合を世帯数で（2023年）", value=r(c), note=f"p={p:.4f}"))
    c, p, _ = corr(2023, col="unused_share"); rob.append(dict(check="4a 空き地＋原野などの割合（2023年）", value=r(c), note=f"p={p:.4f}"))
    rob.append(dict(check="3b H2 を世帯数の割合で：下がった地方の数", value=int((d_hs < 0).sum()), note="8地方のうち"))
    rob.append(dict(check="4b H2 を空き地＋原野などで：下がった地方の数", value=int((d_us < 0).sum()), note="8地方のうち"))
    rob.append(dict(check="3c H4 を世帯数の割合で（2023年）：政令市／政令市以外", value=f"{cvh[2023][0]:.2f}／{cvh[2023][1]:.2f}", note=""))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.to_dict(orient="records")

    # 問い直し：持ち家に住む世帯と借家に住む世帯
    j = jp[jp.year.isin([2018, 2023])].set_index(["year", "category"])
    rq = {}
    for y in (2018, 2023):
        tot = j.loc[(y, "総数")]; va = j.loc[(y, "利用していない（空き地）")]
        rq[str(y)] = dict(own_vacant_share=r(100 * va.lots_own / tot.lots_own, 2), rent_vacant_share=r(100 * va.lots_rent / tot.lots_rent, 2),
                          own_lots=r(tot.lots_own, 0), rent_lots=r(tot.lots_rent, 0), own_vacant=r(va.lots_own, 0), rent_vacant=r(va.lots_rent, 0),
                          vacant_area_per_lot=r(va.area_total, 0))
    out["requestion_tenure"] = rq
    # 空き地の面積（件数×1件当たり面積、km2）
    out["vacant_area_km2"] = {str(y): r(j.loc[(y, "利用していない（空き地）")].lots_total * j.loc[(y, "利用していない（空き地）")].area_total / 1e6, 1) for y in (2018, 2023)}
    pd.DataFrame([dict(year=int(y), **v) for y, v in rq.items()]).to_csv(RES / "requestion_tenure.csv", index=False)

    # 問い直し2：県の差は5年で続くか（2018年と2023年の空き地の割合）
    a = P[P.year == 2018].set_index("pno"); b = P[P.year == 2023].set_index("pno")
    st = pd.DataFrame({"region": a.region, "vacant_share_2018": a.vacant_share, "vacant_share_2023": b.vacant_share})
    st["change"] = st.vacant_share_2023 - st.vacant_share_2018
    st.round(4).to_csv(RES / "requestion_stability.csv")
    c1, p1 = stats.pearsonr(st.vacant_share_2018, st.vacant_share_2023)
    c2, p2 = stats.pearsonr(st.vacant_share_2018, st.change)
    out["requestion_stability"] = dict(r_2018_2023=r(c1), p1=r(p1, 6), r_level_change=r(c2), p2=r(p2, 4),
                                       n_down=int((st.change < 0).sum()), median_change=r(st.change.median(), 2),
                                       min_change=r(st.change.min(), 2), max_change=r(st.change.max(), 2))

    j0 = out["japan"]
    out["hypotheses"] = {
        "H1": dict(value=[j0[2013]["unused_lots"], j0[2023]["unused_lots"]], verdict="支持" if j0[2023]["unused_lots"] < j0[2013]["unused_lots"] else "外れ"),
        "H2": dict(value=n_down, verdict="支持" if n_down >= 5 else "外れ"),
        "H3": dict(value=r(c23), verdict="支持" if c23 > 0.3 else "外れ"),
        "H4": dict(value=[r(cv[2023][0], 2), r(cv[2023][1], 2)], verdict="支持" if cv[2023][0] < cv[2023][1] else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
