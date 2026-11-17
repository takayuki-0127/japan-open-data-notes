"""実質化、新築との比、工事目的の割合、頑健性、問い直し（非住宅の用途）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
E0, E1 = (2016, 2018), (2023, 2025)
P0 = (2017, 2019)  # 工事目的の早い期間（2016年度の表2-3-3は外れ値処理の前の値のため除く）


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def avg(df, col, span):
    s = df.set_index("fiscal_year")[col]
    return float(s.loc[span[0]:span[1]].mean())


def main():
    tot = pd.read_csv(DATA / "reform_total.csv")
    st = pd.read_csv(DATA / "starts.csv")
    de = pd.read_csv(DATA / "deflator.csv")
    pur = pd.read_csv(DATA / "reform_purpose.csv")
    use = pd.read_csv(DATA / "reform_nonres_use.csv")
    out = {}

    t = tot.merge(de, on="fiscal_year", how="left").merge(st, on="fiscal_year", how="left")
    t["real_total"] = t.total / (t.defl_repair / 100)
    t["real_housing"] = t.housing / (t.defl_repair / 100)
    t["real_nonres"] = t.nonres / (t.defl_repair / 100)
    t["real_housing_alt"] = t.housing / (t.defl_housing / 100)
    t["real_nonres_alt"] = t.nonres / (t.defl_nonres / 100)
    t["real_total_alt"] = t.real_housing_alt + t.real_nonres_alt
    t["ratio_housing"] = t.housing / t.starts_housing
    t["ratio_nonres"] = t.nonres / t.starts_nonres
    t["ratio_total"] = t.total / t.starts_total
    t.round(4).to_csv(RES / "annual_table.csv", index=False)
    m = t[t.fiscal_year >= 2016]

    def growth(col, a=E0, b=E1, df=m, excl=None):
        d = df if excl is None else df[~df.fiscal_year.isin(excl)]
        return 100 * (avg(d, col, b) / avg(d, col, a) - 1)

    out["levels"] = {int(x.fiscal_year): dict(total=r(x.total, 0), housing=r(x.housing, 0), nonres=r(x.nonres, 0),
                                               real_total=r(x.real_total, 0), ratio_housing=r(x.ratio_housing, 3),
                                               ratio_nonres=r(x.ratio_nonres, 3), defl_repair=r(x.defl_repair, 1))
                     for _, x in m.iterrows()}
    out["growth_main"] = dict(nominal_total=r(growth("total")), real_total=r(growth("real_total")),
                              real_housing=r(growth("real_housing")), real_nonres=r(growth("real_nonres")),
                              nominal_housing=r(growth("housing")), nominal_nonres=r(growth("nonres")),
                              starts_housing=r(growth("starts_housing")), starts_nonres=r(growth("starts_nonres")),
                              defl_repair=r(growth("defl_repair")))
    rh0, rh1 = avg(m, "ratio_housing", E0), avg(m, "ratio_housing", E1)
    rn0, rn1 = avg(m, "ratio_nonres", E0), avg(m, "ratio_nonres", E1)
    out["ratio"] = dict(housing0=r(rh0, 3), housing1=r(rh1, 3), nonres0=r(rn0, 3), nonres1=r(rn1, 3),
                        total0=r(avg(m, "ratio_total", E0), 3), total1=r(avg(m, "ratio_total", E1), 3))
    # 2011年度からの参考（2016年度以降の公表資料の表1-1にある値）
    out["since2011"] = {int(x.fiscal_year): dict(total=r(x.total, 0), real_total=r(x.real_total, 0)) for _, x in t.iterrows()}

    # 工事目的の割合
    pv = pur.pivot_table(index=["fiscal_year", "group"], columns="purpose", values="value").reset_index()
    purposes = [c for c in pv.columns if c not in ("fiscal_year", "group", "計", "不明")]
    pv["known"] = pv["計"] - pv["不明"].fillna(0)
    for c in purposes:
        pv["share_" + c] = 100 * pv[c] / pv["known"]
        pv["shareall_" + c] = 100 * pv[c] / pv["計"]
    pv["unknown_share"] = 100 * pv["不明"].fillna(0) / pv["計"]
    pv.round(4).to_csv(RES / "purpose_shares.csv", index=False)
    H = pv[pv.group == "住宅"]; N = pv[pv.group == "非住宅"]
    sh = {}
    for g, df in (("住宅", H), ("非住宅", N)):
        sh[g] = {c: dict(early=r(avg(df, "share_" + c, P0)), late=r(avg(df, "share_" + c, E1))) for c in purposes}
        sh[g]["_unknown"] = {int(y): r(v, 1) for y, v in zip(df.fiscal_year, df.unknown_share)}
    out["purpose_share"] = sh
    min_deg = float(H[H.fiscal_year >= 2017]["share_劣化や壊れた部位の更新･修繕"].min())
    min_deg_all = float(H["share_劣化や壊れた部位の更新･修繕"].min())
    out["housing_degradation_share_by_year"] = {int(y): r(v, 1) for y, v in zip(H.fiscal_year, H["share_劣化や壊れた部位の更新･修繕"])}
    out["housing_energy_share_by_year"] = {int(y): r(v, 2) for y, v in zip(H.fiscal_year, H["share_省エネルギー対策"])}
    out["housing_energy_amount"] = {int(y): r(v, 0) for y, v in zip(H.fiscal_year, H["省エネルギー対策"])}

    # 頑健性
    rob = []
    def addrow(name, real, rh, rn, es):
        rob.append(dict(check=name, real_total_growth=r(real, 1), ratio_housing=rh, ratio_nonres=rn, energy_share_change=r(es, 2)))
    es_main = sh["住宅"]["省エネルギー対策"]["late"] - sh["住宅"]["省エネルギー対策"]["early"]
    addrow("0 主（建築補修デフレーター、2016-18→2023-25、目的は2017-19→2023-25）", growth("real_total"),
           f"{rh0:.3f}→{rh1:.3f}", f"{rn0:.3f}→{rn1:.3f}", es_main)
    addrow("1 デフレーターを住宅総合・非住宅総合に替える", growth("real_total_alt"), "（同じ）", "（同じ）", None)
    one = lambda c, a, b: 100 * (float(m.set_index("fiscal_year").loc[b, c]) / float(m.set_index("fiscal_year").loc[a, c]) - 1)
    mi = m.set_index("fiscal_year")
    es_single = float(H.set_index("fiscal_year").loc[2025, "share_省エネルギー対策"] - H.set_index("fiscal_year").loc[2017, "share_省エネルギー対策"])
    addrow("2 単年（2016→2025年度、目的は2017→2025年度）", one("real_total", 2016, 2025),
           f"{mi.loc[2016,'ratio_housing']:.3f}→{mi.loc[2025,'ratio_housing']:.3f}", f"{mi.loc[2016,'ratio_nonres']:.3f}→{mi.loc[2025,'ratio_nonres']:.3f}", es_single)
    d2 = m[m.fiscal_year != 2020]
    addrow("3a 2020年度を除く（2016-19 と 2023-25 の平均）", 100 * (avg(d2, "real_total", E1) / avg(d2, "real_total", (2016, 2019)) - 1),
           f"{avg(d2,'ratio_housing',(2016,2019)):.3f}→{rh1:.3f}", f"{avg(d2,'ratio_nonres',(2016,2019)):.3f}→{rn1:.3f}", None)
    d3 = m[m.fiscal_year != 2025]
    Hx = H[H.fiscal_year != 2025]
    addrow("3b 2025年度を除く（2016-18 と 2022-24 の平均）", 100 * (avg(d3, "real_total", (2022, 2024)) / avg(d3, "real_total", E0) - 1),
           f"{rh0:.3f}→{avg(d3,'ratio_housing',(2022,2024)):.3f}", f"{rn0:.3f}→{avg(d3,'ratio_nonres',(2022,2024)):.3f}",
           avg(Hx, "share_省エネルギー対策", (2022, 2024)) - avg(Hx, "share_省エネルギー対策", P0))
    addrow("4 目的の割合の分母に不明を入れる", None, "—", "—",
           avg(H, "shareall_省エネルギー対策", E1) - avg(H, "shareall_省エネルギー対策", P0))
    addrow("4b 目的の早い期間に2016年度を入れる（2016-18→2023-25）", None, "—", "—",
           avg(H, "share_省エネルギー対策", E1) - avg(H, "share_省エネルギー対策", E0))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.where(rob.notna(), None).to_dict(orient="records")

    # 問い直し：非住宅の用途別
    u = use[use.use != "不明"].merge(de[["fiscal_year", "defl_nonres"]], on="fiscal_year")
    u["real"] = u.value / (u.defl_nonres / 100)
    g = []
    for name, df in u.groupby("use", sort=False):
        a, b = avg(df, "real", P0), avg(df, "real", E1)
        g.append(dict(use=name, real_early=a, real_late=b, growth=100 * (b / a - 1), late_nominal=avg(df, "value", E1)))
    g = pd.DataFrame(g)
    g["real_change"] = g.real_late - g.real_early
    g.round(3).to_csv(RES / "requestion_nonres_use.csv", index=False)
    out["requestion_nonres_use"] = {x.use: dict(growth=r(x.growth, 1), real_change=r(x.real_change, 0), late_nominal=r(x.late_nominal, 0)) for _, x in g.iterrows()}
    out["requestion_nonres_total_growth"] = r(100 * (g.real_late.sum() / g.real_early.sum() - 1), 1)

    out["hypotheses"] = {
        "H1": dict(value=out["growth_main"]["real_total"], verdict="支持" if growth("real_total") >= 10 else "外れ"),
        "H2": dict(value=[out["ratio"]["housing0"], out["ratio"]["housing1"], out["ratio"]["nonres0"], out["ratio"]["nonres1"]],
                   verdict="支持" if (rh1 > rh0 and rn1 > rn0) else "外れ"),
        "H3": dict(value=r(es_main, 2), verdict="支持" if es_main >= 1 else "外れ"),
        "H4": dict(value=r(min_deg, 1), value_incl2016=r(min_deg_all, 1), verdict="支持" if min_deg_all >= 70 else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ["growth_main", "ratio", "hypotheses", "purpose_share", "housing_degradation_share_by_year", "housing_energy_share_by_year", "requestion_nonres_use", "requestion_nonres_total_growth"]}, ensure_ascii=False, indent=0))
    print(rob.to_string())


if __name__ == "__main__":
    main()
