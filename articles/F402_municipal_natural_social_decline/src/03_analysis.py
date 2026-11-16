"""市区町村の人口減少を自然増減と社会増減に分け、results/ に書く（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
REGIONS = [("北海道", [1]), ("東北", range(2, 8)), ("関東", range(8, 15)), ("中部", range(15, 24)),
           ("近畿", range(24, 31)), ("中国", range(31, 36)), ("四国", range(36, 40)), ("九州・沖縄", range(40, 48))]
RNAME = [r for r, _ in REGIONS]
REG_OF = {p: r for r, ps in REGIONS for p in ps}
CODEMAP = {"044237": "042161", "403059": "402311"}   # 富谷町→富谷市（2016年）、那珂川町→那珂川市（2018年）
SIZE_BINS = [0, 5000, 10000, 30000, 100000, 300000, np.inf]
SIZE_LAB = ["5千人未満", "5千〜1万", "1万〜3万", "3万〜10万", "10万〜30万", "30万人以上"]


def r1(x):
    return round(float(x), 1)


def classify(df, nat="natural", soc="social", chg="change"):
    """人口が減った単位について、自然減と社会減のどちらが大きいか。"""
    d = df[df[chg] < 0].copy()
    d["nat_dom"] = (-d[nat]) > (-d[soc])   # 自然減のほうが大きい（社会増を含む）
    return d


def summary(df, nat="natural", soc="social", chg="change"):
    d = classify(df, nat, soc, chg)
    return dict(n_units=int(len(df)), n_decline=int(len(d)), share_decline=r1(100 * len(d) / len(df)),
                nat_dom_share=r1(100 * d.nat_dom.mean()),
                nat_part_of_decline=r1(100 * d[nat].sum() / d[chg].sum()),
                both_decline_share=r1(100 * ((d[nat] < 0) & (d[soc] < 0)).mean()),
                nat_dec_soc_inc_share=r1(100 * ((d[nat] < 0) & (d[soc] >= 0)).mean()),
                soc_dec_nat_inc_share=r1(100 * ((d[nat] >= 0) & (d[soc] < 0)).mean()))


def period(D, years, kind="total", ward=False):
    x = D[(D.kind == kind) & (D.year.isin(years)) & (D.ward == ward)].copy()
    x["code"] = x.code.replace(CODEMAP)
    first = x[x.year == min(years)].set_index("code")["pop"]
    g = x.groupby("code").agg(pref=("pref", "first"), name=("name", "last"), natural=("natural", "sum"), social=("social", "sum"),
                              change=("change", "sum"), mig=("mig", "sum"))
    g["pop0"] = first.reindex(g.index) - x[x.year == min(years)].set_index("code").change.reindex(g.index)   # 期首（前年1月1日）の人口
    g["region"] = g.pref.map(REG_OF)
    g["size"] = pd.cut(g.pop0, SIZE_BINS, labels=SIZE_LAB, right=False)
    return g


def main():
    RES.mkdir(exist_ok=True)
    D = pd.read_csv(ROOT / "data" / "muni.csv", dtype={"code": str})
    D["mig"] = D.in_dom + D.in_abr - D.out_dom - D.out_abr   # 転入 − 転出（その他を除く）
    out = {}
    # 年ごと
    yr = []
    for y in range(2014, 2026):
        s = summary(period(D, [y]))
        nat = D[(D.kind == "total") & (D.year == y) & (~D.ward)]
        yr.append(dict(year=y, nat_total=int(nat.natural.sum()), soc_total=int(nat.social.sum()), **s))
    Y = pd.DataFrame(yr)
    Y.to_csv(RES / "yearly.csv", index=False)
    out["yearly"] = yr
    # 主：2021〜2025年の5年合計
    P = period(D, list(range(2021, 2026)))
    P.to_csv(RES / "muni_2021_2025.csv")
    main_s = summary(P)
    out["main_2021_2025"] = main_s
    dP = classify(P)
    # 規模別・地方別
    rows = []
    for lab in SIZE_LAB:
        rows.append(dict(group="規模", key=lab, **summary(P[P["size"] == lab])))
    for reg in RNAME:
        rows.append(dict(group="地方", key=reg, **summary(P[P.region == reg])))
    G = pd.DataFrame(rows)
    G.to_csv(RES / "by_size_region_2021_2025.csv", index=False)
    out["by_group"] = rows
    small = dP[dP.pop0 < 10000]; large = dP[dP.pop0 >= 100000]
    soc_small = 100 * (~small.nat_dom).mean(); soc_large = 100 * (~large.nat_dom).mean()
    out["soc_dom_small_large"] = [r1(soc_small), r1(soc_large), int(len(small)), int(len(large))]
    # 日本人住民（2025年・2014年）
    Jt = summary(period(D, [2025])); Jj = summary(period(D, [2025], kind="japanese"))
    Jt14 = summary(period(D, [2014])); Jj14 = summary(period(D, [2014], kind="japanese"))
    out["japanese"] = {"2025_total": Jt, "2025_japanese": Jj, "2014_total": Jt14, "2014_japanese": Jj14}
    y14 = Y.set_index("year")
    h1 = main_s["nat_dom_share"]; h2 = (y14.nat_part_of_decline[2014], y14.nat_part_of_decline[2025])
    h4 = (100 - Jt["nat_dom_share"], 100 - Jj["nat_dom_share"])
    out["hypotheses"] = {
        "H1": dict(value=h1, verdict="支持" if h1 >= 60 else "外れ"),
        "H2": dict(value=[r1(h2[0]), r1(h2[1])], verdict="支持" if h2[1] > h2[0] else "外れ"),
        "H3": dict(value=[r1(soc_small), r1(soc_large)], verdict="支持" if soc_small > soc_large else "外れ"),
        "H4": dict(value=[r1(h4[0]), r1(h4[1])], verdict="支持" if h4[1] > h4[0] else "外れ"),
    }
    # 頑健性
    rb = [dict(check="0 主：2021〜2025年の5年合計", nat_dom_share=h1, nat_part=main_s["nat_part_of_decline"], n_decline=main_s["n_decline"])]
    for lab, yrs in [("1a 2023〜2025年の3年合計", [2023, 2024, 2025]), ("1b 2025年の1年", [2025])]:
        s = summary(period(D, yrs)); rb.append(dict(check=lab, nat_dom_share=s["nat_dom_share"], nat_part=s["nat_part_of_decline"], n_decline=s["n_decline"]))
    Pm = P.copy(); Pm["change2"] = Pm.natural + Pm.mig
    s = summary(Pm, soc="mig", chg="change2")
    rb.append(dict(check="2 社会増減を転入−転出だけに（その他を除く）", nat_dom_share=s["nat_dom_share"], nat_part=s["nat_part_of_decline"], n_decline=s["n_decline"]))
    # 浜松市は2024年に行政区を再編したので、行政区に分けず市全体のままにする
    W = period(D, list(range(2021, 2026)), ward=True)
    W = W[~W.index.str.startswith("2213")]
    seirei = ["011002", "041009", "111007", "121002", "141003", "141305", "141500", "151009", "221007", "231002",
              "261009", "271004", "271403", "281000", "331007", "341002", "401005", "401307", "431001"]
    Pw = pd.concat([P[~P.index.isin(seirei)], W])
    assert len(Pw) == len(P) - len(seirei) + len(W)
    s = summary(Pw)
    rb.append(dict(check="3 政令指定都市を行政区ごとに", nat_dom_share=s["nat_dom_share"], nat_part=s["nat_part_of_decline"], n_decline=s["n_decline"]))
    rb.append(dict(check="4a 2025年：総計", nat_dom_share=Jt["nat_dom_share"], nat_part=Jt["nat_part_of_decline"], n_decline=Jt["n_decline"]))
    rb.append(dict(check="4b 2025年：日本人住民", nat_dom_share=Jj["nat_dom_share"], nat_part=Jj["nat_part_of_decline"], n_decline=Jj["n_decline"]))
    rb.append(dict(check="4c 2014年：総計", nat_dom_share=Jt14["nat_dom_share"], nat_part=Jt14["nat_part_of_decline"], n_decline=Jt14["n_decline"]))
    rb.append(dict(check="4d 2014年：日本人住民", nat_dom_share=Jj14["nat_dom_share"], nat_part=Jj14["nat_part_of_decline"], n_decline=Jj14["n_decline"]))
    pw = dP.groupby("size", observed=False).apply(lambda d: 100 * d.natural.sum() / d.change.sum(), include_groups=False)
    rb.append(dict(check="5 人口の重み（減少の合計に占める自然減、規模別）", nat_dom_share=None, nat_part=None, n_decline=None,
                   note="、".join(f"{k} {v:.1f}%" for k, v in pw.items())))
    pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rb
    out["pw_by_size"] = {k: r1(v) for k, v in pw.items()}
    # 問い直し：自然減なのに社会増の市区町村の数
    rq = []
    for y in range(2014, 2026):
        x = period(D, [y])
        rq.append(dict(year=y, nat_dec=int((x.natural < 0).sum()), nat_dec_soc_inc=int(((x.natural < 0) & (x.social > 0)).sum()),
                       nat_dec_soc_inc_pop_inc=int(((x.natural < 0) & (x.social > 0) & (x.change >= 0)).sum()),
                       soc_dec=int((x.social < 0).sum()), increase=int((x.change >= 0).sum())))
    pd.DataFrame(rq).to_csv(RES / "requestion.csv", index=False)
    out["requestion"] = rq
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(Y[["year", "nat_total", "soc_total", "n_decline", "nat_dom_share", "nat_part_of_decline"]].to_string())
    print(main_s); print(G.to_string()); print(json.dumps(out["hypotheses"], ensure_ascii=False)); print(pd.DataFrame(rb).to_string()); print(pd.DataFrame(rq).to_string())


if __name__ == "__main__":
    main()
