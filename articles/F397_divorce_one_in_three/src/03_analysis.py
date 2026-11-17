"""見かけの比、期間の合計離婚率、結婚した年ごとの累積の割合、頑健性、問い直し。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
SINGLE = ["0", "1", "2", "3", "4"]
BUCKETS = {"5-10": (5, 10), "10-15": (10, 15), "15-20": (15, 20), "20-25": (20, 25), "25-30": (25, 30), "30-35": (30, 35), "35+": (35, 40)}
FRONT = np.array([0.3, 0.25, 0.2, 0.15, 0.1])


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def main():
    div = pd.read_csv(DATA / "divorce_by_duration.csv")
    M = pd.read_csv(DATA / "marriages.csv").set_index("year").marriages
    # 1966年より前は5年おきなので、年の値を直線でつなぐ（35年以上の区分で2000年代前半に使うだけ）
    M = M.reindex(range(M.index.min(), M.index.max() + 1)).interpolate()
    D = div.pivot(index="year", columns="duration", values="n")
    years = [y for y in D.index if y >= 2000]

    def scaled(y, drop_unknown=False):
        row = D.loc[y].copy()
        known = row["総数"] - row["不詳"]
        f = 1.0 if drop_unknown else row["総数"] / known
        return row * f

    def ptdr(y, single_year=False, drop_unknown=False):
        row = scaled(y, drop_unknown)
        tot = 0.0
        for d in SINGLE:
            k = int(d)
            m = M.loc[y - k] if single_year else (M.loc[y - k] + M.loc[y - k - 1]) / 2
            tot += row[d] / m
        for b, (a, z) in BUCKETS.items():
            if single_year:
                tot += sum(row[b] / 5 / M.loc[y - k] for k in range(a, z))
            else:
                tot += row[b] / M.loc[y - z + 1:y - a].mean()
        return 100 * tot

    tab = pd.DataFrame({"year": years, "divorces": [D.loc[y, "総数"] for y in years], "marriages": [M.loc[y] for y in years]})
    tab["crude_ratio"] = 100 * tab.divorces / tab.marriages
    tab["ptdr"] = [ptdr(y) for y in years]
    tab["ptdr_single"] = [ptdr(y, single_year=True) for y in years]
    tab["ptdr_drop_unknown"] = [ptdr(y, drop_unknown=True) for y in years]
    tab["share_20plus"] = [100 * (D.loc[y, ["20-25", "25-30", "30-35", "35+"]].sum()) / (D.loc[y, "総数"] - D.loc[y, "不詳"]) for y in years]
    tab["share_under5"] = [100 * D.loc[y, "5年未満"] / (D.loc[y, "総数"] - D.loc[y, "不詳"]) for y in years]
    tab.round(4).to_csv(RES / "yearly_ratios.csv", index=False)

    # 結婚した年ごとの累積
    def d_of(y, k, front=False):
        row = scaled(y)
        if k < 5:
            return row[str(k)]
        for b, (a, z) in BUCKETS.items():
            if a <= k < z:
                return row[b] * (FRONT[k - a] if front else 0.2)
        return 0.0

    coh = []
    for m0 in (2000, 2005, 2010, 2015):
        cum = 0.0; cum_f = 0.0
        for k in range(0, 2025 - m0 + 1):
            y = m0 + k
            cum += d_of(y, k) / M.loc[m0]
            cum_f += d_of(y, k, front=True) / M.loc[m0]
            coh.append(dict(cohort=m0, years_married=k + 1, cum_pct=100 * cum, cum_pct_front=100 * cum_f))
    coh = pd.DataFrame(coh)
    coh.round(4).to_csv(RES / "cohort_cumulative.csv", index=False)
    C = coh.set_index(["cohort", "years_married"])

    out = {}
    T = tab.set_index("year")
    out["yearly"] = {int(y): dict(crude=r(x.crude_ratio, 1), ptdr=r(x.ptdr, 1), share_20plus=r(x.share_20plus, 1), share_under5=r(x.share_under5, 1)) for y, x in T.iterrows()}
    out["cohort"] = {int(c): {f"{k}年目": r(C.loc[(c, k), "cum_pct"], 1) for k in (5, 10, 15, 20, 25) if (c, k) in C.index} for c in (2000, 2005, 2010, 2015)}
    out["cohort_last"] = {int(c): dict(years=int(g.years_married.max()), cum=r(g.cum_pct.iloc[-1], 1)) for c, g in coh.groupby("cohort")}
    pre = T.loc[2015:2019]
    rob = pd.DataFrame([
        dict(check="0 主（2025年）", crude=r(T.loc[2025, "crude_ratio"], 1), ptdr=r(T.loc[2025, "ptdr"], 1), cohort2000_25=r(C.loc[(2000, 26), "cum_pct"], 1) if (2000, 26) in C.index else None),
        dict(check="1 婚姻件数を d 年前の1年だけで割る（2025年）", crude=None, ptdr=r(T.loc[2025, "ptdr_single"], 1), cohort2000_25=None),
        dict(check="2 同居期間不詳を配らずに除く（2025年）", crude=None, ptdr=r(T.loc[2025, "ptdr_drop_unknown"], 1), cohort2000_25=None),
        dict(check="3 5年刻みを前に多く配る（2000年に結婚、2025年まで）", crude=None, ptdr=None, cohort2000_25=r(C.loc[(2000, 26), "cum_pct_front"], 1)),
        dict(check="4 2015〜2019年の平均", crude=r(pre.crude_ratio.mean(), 1), ptdr=r(pre.ptdr.mean(), 1), cohort2000_25=None),
    ])
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.astype(object).where(rob.notna(), None).to_dict(orient="records")
    c00_25 = C.loc[(2000, 26), "cum_pct"]  # 2000〜2025年の26年分（同居期間0〜25年）
    out["cohort2000_through2025"] = r(c00_25, 1)
    out["hypotheses"] = {
        "H1": dict(value=r(T.loc[2025, "crude_ratio"], 1), verdict="支持" if T.loc[2025, "crude_ratio"] >= 33 else "外れ"),
        "H2": dict(value=[r(T.loc[2025, "crude_ratio"], 1), r(T.loc[2025, "ptdr"], 1)], verdict="支持" if T.loc[2025, "crude_ratio"] - T.loc[2025, "ptdr"] >= 3 else "外れ"),
        "H3": dict(value=r(c00_25, 1), verdict="支持" if c00_25 < 30 else "外れ"),
        "H4": dict(value=[r(C.loc[(2000, 10), "cum_pct"], 1), r(C.loc[(2010, 10), "cum_pct"], 1)], verdict="支持" if C.loc[(2010, 10), "cum_pct"] < C.loc[(2000, 10), "cum_pct"] else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(tab.round(1).to_string()); print(json.dumps({k: out[k] for k in ["cohort", "cohort_last", "robustness", "hypotheses"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
