"""03 分析：階層ごとの増減と寄与、更新の周期（自己相関）、1業者あたりの業種数、頑健性。
出力：results/main.json, results/contrib.csv, results/acf.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def contrib(cap, y0, y1):
    w = cap.pivot(index="year", columns="cls", values="firms")
    tot = cap.drop_duplicates("year").set_index("year").total
    dt = tot[y1] - tot[y0]
    out = []
    for c in w.columns:
        d = w.loc[y1, c] - w.loc[y0, c]
        out.append(dict(y0=y0, y1=y1, cls=c, firms0=int(w.loc[y0, c]), firms1=int(w.loc[y1, c]), change=int(d),
                        pct=(w.loc[y1, c] / w.loc[y0, c] - 1) * 100, share_of_net=d / dt * 100))
    return pd.DataFrame(out), int(dt)


def acf(x, lags):
    x = np.asarray(x, float) - np.mean(x)
    den = (x ** 2).sum()
    return {k: float((x[k:] * x[:-k]).sum() / den) for k in lags}


def main():
    cap = pd.read_csv(D / "capital_long.csv")
    tot = pd.read_csv(D / "total.csv").set_index("year")
    tpf = pd.read_csv(D / "types_per_firm.csv").set_index("year")
    lab = cap.drop_duplicates("cls").set_index("cls").label
    c, dt = contrib(cap, 2000, 2025)
    c["label"] = c.cls.map(lab)
    c.round(3).to_csv(R / "contrib.csv", index=False)
    two = c[c.cls.isin(["individual", "10m_50m"])].change.sum()
    # 会社法の後
    w = cap.pivot(index="year", columns="cls", values="firms")
    lt2m_inc = int(w.loc[2025, "lt2m"] - w.loc[2006, "lt2m"])
    ind_dec = int(w.loc[2006, "individual"] - w.loc[2025, "individual"])
    # 自己相関（1996〜2025年の前年比）
    yo = tot.loc[1996:2025, "yoy_pct"]
    a = acf(yo.values, range(1, 8))
    pd.DataFrame({"lag": list(a), "acf": list(a.values())}).round(4).to_csv(R / "acf.csv", index=False)
    # 減少の年
    dec_years = [int(y) for y in yo[yo < -1].index]
    main = dict(
        total_2000=int(tot.loc[2000, "total"]), total_2025=int(tot.loc[2025, "total"]), net_change=dt,
        net_pct=(tot.loc[2025, "total"] / tot.loc[2000, "total"] - 1) * 100,
        **{f"chg_{r.cls}": int(r.change) for r in c.itertuples()},
        **{f"pct_{r.cls}": float(r.pct) for r in c.itertuples()},
        **{f"share_{r.cls}": float(r.share_of_net) for r in c.itertuples()},
        two_class_share=float(two / dt * 100),
        individual_share_2000=float(w.loc[2000, "individual"] / tot.loc[2000, "total"] * 100),
        individual_share_2025=float(w.loc[2025, "individual"] / tot.loc[2025, "total"] * 100),
        lt2m_2006=int(w.loc[2006, "lt2m"]), lt2m_2025=int(w.loc[2025, "lt2m"]), lt2m_inc_2006_2025=lt2m_inc,
        individual_dec_2006_2025=ind_dec, lt2m_vs_individual=lt2m_inc / ind_dec,
        acf_lag5=a[5], acf_lag1=a[1], acf_max_lag=int(max(a, key=lambda k: a[k])),
        decline_years_lt_minus1=dec_years,
        types_per_firm_2000=float(tpf.loc[2000, "types_per_firm"]), types_per_firm_2025=float(tpf.loc[2025, "types_per_firm"]),
        types_per_firm_ex_demo_2025=float(tpf.loc[2025, "types_per_firm_ex_demolition"]),
        permits_2000=int(tpf.loc[2000, "permits"]), permits_2025=int(tpf.loc[2025, "permits"]),
    )
    main["types_per_firm_inc"] = main["types_per_firm_2025"] - main["types_per_firm_2000"]
    main["H1"] = "支持" if main["two_class_share"] >= 90 else "外れ"
    main["H2"] = "支持" if main["lt2m_vs_individual"] < 0.5 else "外れ"
    main["H3"] = "支持" if main["acf_lag5"] >= 0.3 else "外れ"
    main["H4"] = "支持" if main["types_per_firm_inc"] >= 1 else "外れ"
    # 頑健性
    rob = []
    for y0 in (1993, 2000, 2005, 2010):
        cc, d0 = contrib(cap, y0, 2025)
        g = cc.set_index("cls")
        small = g.loc[["lt2m", "2m_5m", "5m_10m"]].change.sum()
        rob.append(dict(check=f"起点 {y0}年", net=d0, individual=int(g.loc["individual", "change"]),
                        corp_lt10m=int(small), corp_10m_50m=int(g.loc["10m_50m", "change"]),
                        corp_ge50m=int(g.loc[["50m_100m", "100m_1b", "ge1b"]].change.sum()),
                        two_class_share=float((g.loc["individual", "change"] + g.loc["10m_50m", "change"]) / d0 * 100)))
    rob = pd.DataFrame(rob)
    acf_rows = []
    for lab_, y0, y1 in [("1996〜2025年（本線）", 1996, 2025), ("2001〜2025年", 2001, 2025), ("1996〜2019年", 1996, 2019)]:
        aa = acf(tot.loc[y0:y1, "yoy_pct"].values, range(1, 8))
        acf_rows.append(dict(check=lab_, acf_lag1=aa[1], acf_lag5=aa[5], max_lag=int(max(aa, key=lambda k: aa[k]))))
    pd.concat([rob, pd.DataFrame(acf_rows)], ignore_index=True).round(4).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()},
              open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string()); print(a)


if __name__ == "__main__":
    main()
