"""03 分析：旅行消費額＝延べ旅行者数×旅行単価、延べ旅行者数＝人口×平均回数 を対数で分ける"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)


def load():
    d = pd.read_csv(ROOT / "data" / "series.csv")
    d = d[d.year >= 2010]
    return d.pivot_table(index=["kind", "purpose", "year"], columns="indicator", values="value")


def spend_decomp(T, kind, purp, y0, y1):
    a, b = T.loc[(kind, purp, y0)], T.loc[(kind, purp, y1)]
    ls = np.log(b["旅行消費額"] / a["旅行消費額"]); ln = np.log(b["延べ旅行者数"] / a["延べ旅行者数"]); lu = np.log(b["旅行単価"] / a["旅行単価"])
    return dict(kind=kind, purpose=purp, y0=y0, y1=y1,
                spend_chg=float(100 * (np.exp(ls) - 1)), trips_chg=float(100 * (np.exp(ln) - 1)), unit_chg=float(100 * (np.exp(lu) - 1)),
                unit_share=float(lu / ls) if ls != 0 else np.nan, resid=float(ls - ln - lu))


def trips_decomp(T, kind, purp, y0, y1):
    a, b = T.loc[(kind, purp, y0)], T.loc[(kind, purp, y1)]
    pa, pb = a["延べ旅行者数"] / a["旅行平均回数"], b["延べ旅行者数"] / b["旅行平均回数"]
    ln = np.log(b["延べ旅行者数"] / a["延べ旅行者数"]); lp = np.log(pb / pa); lf = np.log(b["旅行平均回数"] / a["旅行平均回数"])
    return dict(kind=kind, purpose=purp, y0=y0, y1=y1, trips_chg=float(100 * (np.exp(ln) - 1)),
                pop_chg=float(100 * (np.exp(lp) - 1)), freq_chg=float(100 * (np.exp(lf) - 1)),
                pop_share=float(lp / ln) if ln != 0 else np.nan)


def main():
    T = load()
    S = []
    for (y0, y1) in [(2010, 2019), (2019, 2025), (2010, 2025)]:
        for k in ["全体", "宿泊", "日帰り"]:
            for p in ["計", "観光", "帰省", "出張"]:
                S.append(spend_decomp(T, k, p, y0, y1))
    S = pd.DataFrame(S); S.round(4).to_csv(RES / "spend_decomp.csv", index=False)
    F = []
    for (y0, y1) in [(2010, 2019), (2019, 2025), (2010, 2025)]:
        for k in ["宿泊", "日帰り"]:
            for p in ["計", "観光", "帰省", "出張"]:
                F.append(trips_decomp(T, k, p, y0, y1))
    F = pd.DataFrame(F); F.round(4).to_csv(RES / "trips_decomp.csv", index=False)
    yr = T.reset_index()
    yr = yr[yr.purpose == "計"][["kind", "year", "延べ旅行者数", "旅行消費額", "旅行単価", "旅行平均回数"]]
    yr.round(4).to_csv(RES / "yearly.csv", index=False)
    pur = T.reset_index(); pur = pur[(pur.kind == "全体") & (pur.purpose != "計")][["purpose", "year", "延べ旅行者数", "旅行消費額"]]
    pur.round(4).to_csv(RES / "purpose_yearly.csv", index=False)

    g = lambda df, **kw: df[np.logical_and.reduce([df[k] == v for k, v in kw.items()])].iloc[0]
    m = dict(
        trips_2010=float(T.loc[("全体", "計", 2010)]["延べ旅行者数"]), trips_2019=float(T.loc[("全体", "計", 2019)]["延べ旅行者数"]),
        trips_2025=float(T.loc[("全体", "計", 2025)]["延べ旅行者数"]),
        spend_2010=float(T.loc[("全体", "計", 2010)]["旅行消費額"]), spend_2019=float(T.loc[("全体", "計", 2019)]["旅行消費額"]),
        spend_2025=float(T.loc[("全体", "計", 2025)]["旅行消費額"]),
        h1_trips_19_25=float(g(S, kind="全体", purpose="計", y0=2019, y1=2025).trips_chg),
        h2_trips_10_19=float(g(S, kind="全体", purpose="計", y0=2010, y1=2019).trips_chg),
        h3_unit_share_19_25=float(g(S, kind="全体", purpose="計", y0=2019, y1=2025).unit_share),
        h3_spend_19_25=float(g(S, kind="全体", purpose="計", y0=2019, y1=2025).spend_chg),
        h3_unit_19_25=float(g(S, kind="全体", purpose="計", y0=2019, y1=2025).unit_chg),
        h4_day_10_25=float(g(S, kind="日帰り", purpose="計", y0=2010, y1=2025).trips_chg),
        h4_stay_10_25=float(g(S, kind="宿泊", purpose="計", y0=2010, y1=2025).trips_chg),
        h5=S[(S.kind == "全体") & (S.purpose != "計") & (S.y0 == 2019) & (S.y1 == 2025)][["purpose", "trips_chg", "spend_chg", "unit_chg"]].round(2).values.tolist())
    # 頑健性
    rob = []
    for (y0, y1, lab) in [(2010, 2019, "基本 2010→2019"), (2011, 2019, "2011→2019"), (2012, 2019, "2012→2019"),
                          (2019, 2025, "基本 2019→2025"), (2018, 2025, "2018→2025"), (2019, 2024, "2019→2024"), (2018, 2024, "2018→2024")]:
        r = spend_decomp(T, "全体", "計", y0, y1); r["label"] = lab
        s = spend_decomp(T, "宿泊", "計", y0, y1)
        r["stay_unit_share"] = s["unit_share"]; r["stay_trips_chg"] = s["trips_chg"]
        f1, f2 = trips_decomp(T, "宿泊", "計", y0, y1), trips_decomp(T, "日帰り", "計", y0, y1)
        r["stay_freq_chg"] = f1["freq_chg"]; r["day_freq_chg"] = f2["freq_chg"]
        rob.append(r)
    R = pd.DataFrame(rob); R.round(4).to_csv(RES / "robustness.csv", index=False)
    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print(json.dumps(m, ensure_ascii=False, indent=1))
    print(R.round(2).to_string())
    print(F.round(2).to_string())
    print(S[S.purpose != "計"].round(2).to_string())


if __name__ == "__main__":
    main()
