"""03 分析：「何年ぶり」、ピークからの分解（名目と相対物価）、旧系列との照合、頑健性。
出力：results/main.json, results/decomp.csv, results/robustness.csv, results/annual.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def last_as_low(s, v, before):
    x = s[(s <= v) & (s.index < before)]
    return int(x.index[-1]) if len(x) else None


def decomp(e, a, b, cols=("reer", "neer", "relprice")):
    r, n, p = cols
    lr = np.log(e.loc[b, r] / e.loc[a, r]); ln_ = np.log(e.loc[b, n] / e.loc[a, n]); lp = np.log(e.loc[b, p] / e.loc[a, p])
    return dict(start=a, end=b, real_pct=float((np.exp(lr) - 1) * 100), nominal_pct=float((np.exp(ln_) - 1) * 100), relprice_pct=float((np.exp(lp) - 1) * 100),
                nominal_share=float(ln_ / lr * 100), relprice_share=float(lp / lr * 100))


def main():
    e = pd.read_csv(D / "monthly.csv").set_index("ym")
    last = int(e.index[-1]); v = float(e.loc[last, "reer"])
    yr = e.index // 100
    ann = e.groupby(yr)[["neer", "reer", "relprice", "usdjpy", "neer_old", "reer_old", "relprice_old"]].mean()
    ann.index.name = "year"; ann.round(4).to_csv(R / "annual.csv")
    low_m = last_as_low(e.reer, v, 202001)
    # 12か月平均
    r12 = e.reer.rolling(12).mean()
    v12 = float(r12.iloc[-1]); low12 = last_as_low(r12.dropna(), v12, 202001)
    peak = int(e.reer.idxmax()); min_m = int(e.reer.idxmin())
    rows = [decomp(e, peak, last), decomp(e, 199501, last), decomp(e, 201201, last), decomp(e, 197001, last)]
    dd = pd.DataFrame(rows); dd.round(4).to_csv(R / "decomp.csv", index=False)
    # 相対物価の年率（期間別）
    def rate(a, b):
        return float(((ann.loc[b, "relprice"] / ann.loc[a, "relprice"]) ** (1 / (b - a)) - 1) * 100)
    main = dict(latest_month=last, reer_latest=v, neer_latest=float(e.loc[last, "neer"]), usdjpy_latest=float(e.loc[last, "usdjpy"]),
                last_month_as_low_before_2020=low_m, reer_min_month=min_m, reer_min=float(e.reer.min()),
                reer_12m_latest=v12, last_month_as_low_12m=low12,
                reer_peak_month=peak, reer_peak=float(e.reer.max()), reer_1970_01=float(e.loc[197001, "reer"]),
                peak_real_pct=rows[0]["real_pct"], peak_nominal_share=rows[0]["nominal_share"], peak_relprice_share=rows[0]["relprice_share"],
                peak_nominal_pct=rows[0]["nominal_pct"], peak_relprice_pct=rows[0]["relprice_pct"],
                y2012_real_pct=rows[2]["real_pct"], y2012_nominal_share=rows[2]["nominal_share"], y2012_relprice_share=rows[2]["relprice_share"],
                y2012_nominal_pct=rows[2]["nominal_pct"], y2012_relprice_pct=rows[2]["relprice_pct"],
                relprice_rate_1995_2012=rate(1995, 2012), relprice_rate_2012_2021=rate(2012, 2021), relprice_rate_2021_2025=rate(2021, 2025),
                neer_vs_1995=float(e.loc[last, "neer"] / ann.loc[1995, "neer"] * 100 - 100))
    # 旧系列の照合
    old = e.loc[:201001]
    peak_old = int(old.reer_old.idxmax())
    ratio_new = ann.loc[1995, "reer"] / ann.loc[2007, "reer"]; ratio_old = ann.loc[1995, "reer_old"] / ann.loc[2007, "reer_old"]
    main.update(peak_old_month=peak_old, ratio_1995_2007_new=float(ratio_new), ratio_1995_2007_old=float(ratio_old),
                ratio_gap_pct=float((ratio_old / ratio_new - 1) * 100))
    main["H1"] = "支持" if (low_m is None or low_m < 197601) else "外れ"
    main["H2"] = "支持" if main["peak_relprice_share"] > 50 else "外れ"
    main["H3"] = "支持" if main["y2012_nominal_share"] > main["y2012_relprice_share"] else "外れ"
    main["H4"] = "支持" if (peak_old // 100 == peak // 100 and abs(main["ratio_gap_pct"]) < 5) else "外れ"
    rob = [dict(check="単月：最新の値以下の月が最後にあった時点（2020年より前）", value=low_m),
           dict(check="12か月平均：同上", value=low12),
           dict(check="1995年1月→最新：相対物価の寄与（%）", value=round(rows[1]["relprice_share"], 2)),
           dict(check="ピーク→最新：相対物価の寄与（%）", value=round(rows[0]["relprice_share"], 2))]
    do = decomp(old, 199501, 200701, ("reer_old", "neer_old", "relprice_old")); dn = decomp(e, 199501, 200701)
    rob.append(dict(check="1995年1月→2007年1月 相対物価の寄与（旧系列）", value=round(do["relprice_share"], 2)))
    rob.append(dict(check="1995年1月→2007年1月 相対物価の寄与（新系列）", value=round(dn["relprice_share"], 2)))
    c = np.corrcoef(np.log(ann.loc[1980:2025, "usdjpy"]).diff().dropna(), np.log(ann.loc[1980:2025, "neer"]).diff().dropna())[0, 1]
    rob.append(dict(check="ドル円と名目実効の前年比の相関（1981〜2025年、ドル円は円安で上がるので負が自然）", value=round(float(c), 3)))
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
    main["corr_usdjpy_neer"] = float(c)
    main["old_relprice_share_95_07"] = do["relprice_share"]; main["new_relprice_share_95_07"] = dn["relprice_share"]
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(dd.round(2)); print(pd.read_csv(R / "robustness.csv"))


if __name__ == "__main__":
    main()
