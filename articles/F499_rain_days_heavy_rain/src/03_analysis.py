"""03 分析：雨の日（≧1.0mm）と強い雨の日（≧100mm）の変化（PLAN.md の H1〜H4 と頑健性）。
出力：results/yearly.csv, results/station_table.csv, results/region_table.csv, results/robustness.csv, results/main.json
"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
P1, P2 = (1901, 1930), (1996, 2025)
VARS = ["total", "d1", "d10", "d30", "d50", "d70", "d100"]
REGIONS = ["北日本", "東日本", "西日本", "沖縄奄美"]


def load(include_insufficient=False):
    d = pd.read_csv(DATA / "annual.csv")
    ok = {"ok", "quasi"} | ({"insufficient"} if include_insufficient else set())
    for v in VARS:
        d.loc[~d[f"{v}_flag"].isin(ok), v] = np.nan
    d["light"] = d["d1"] - d["d10"]  # 1〜10mm 未満の日（弱い雨の日）
    d["sdii"] = d["total"] / d["d1"]  # 雨の日1日あたりの雨量（年降水量÷≧1mm の日数）
    return d


def mean_series(d, v, anomaly=False):
    p = d.pivot(index="year", columns="station", values=v)
    if anomaly:
        base = p.loc[1991:2020].mean()
        return (p - base).mean(axis=1) + base.mean()
    return p.mean(axis=1)


def ols_nw(y, per=100):
    y = y.dropna()
    X = sm.add_constant(y.index.values.astype(float))
    f = sm.OLS(y.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    b, se = f.params[1] * per, f.bse[1] * per
    return float(b), float(b - 1.96 * se), float(b + 1.96 * se), float(f.pvalues[1])


def sen(y, per=100):
    y = y.dropna()
    return float(stats.theilslopes(y.values, y.index.values.astype(float))[0] * per)


def pmean(s, p):
    return float(s.loc[p[0]:p[1]].mean())


def poisson_rr(d, v="d100", y0=1901):
    x = d[(d.year >= y0)].dropna(subset=[v]).copy()
    x["t"] = (x.year - 2000) / 100.0
    f = smf.glm(f"{v} ~ C(station) + t", data=x, family=sm.families.Poisson()).fit(cov_type="cluster", cov_kwds={"groups": x["year"].values})
    b, se = f.params["t"], f.bse["t"]
    return float(np.exp(b)), float(np.exp(b - 1.96 * se)), float(np.exp(b + 1.96 * se))


def per_station(d, p1=P1, p2=P2):
    out = []
    for s, x in d.groupby("station", sort=False):
        x = x.set_index("year")
        r = {"station": s, "region": x.region.iloc[0]}
        for v in ["d1", "light", "d10", "d50", "d100", "total", "sdii"]:
            a, b = x.loc[p1[0]:p1[1], v].mean(), x.loc[p2[0]:p2[1], v].mean()
            r[f"{v}_p1"], r[f"{v}_p2"], r[f"{v}_diff"] = a, b, b - a
        r["d1_slope100"] = sen(x["d1"]) if x["d1"].notna().sum() > 30 else np.nan
        out.append(r)
    t = pd.DataFrame(out)
    t["pattern_both"] = (t.d1_diff < 0) & (t.d100_diff > 0)
    t["pattern_both_50"] = (t.d1_diff < 0) & (t.d50_diff > 0)
    return t


def main():
    d = load()
    ys = pd.DataFrame({v: mean_series(d, v) for v in ["total", "d1", "light", "d10", "d30", "d50", "d70", "d100", "sdii"]})
    ys["n_d1"] = d.pivot(index="year", columns="station", values="d1").notna().sum(axis=1)
    for v in ["d1", "d100", "total", "light", "d10", "sdii", "d50"]:
        ys[f"{v}_11yr"] = ys[v].rolling(11, center=True, min_periods=6).mean()
    ys.round(4).to_csv(RES / "yearly.csv")

    # H1
    b1, lo1, hi1, p1v = ols_nw(ys["d1"])
    # H2
    r100 = pmean(ys["d100"], P2) / pmean(ys["d100"], P1)
    b100, lo100, hi100, p100 = ols_nw(ys["d100"])
    rr, rrlo, rrhi = poisson_rr(d)
    # H3
    st = per_station(d)
    st.round(4).to_csv(RES / "station_table.csv", index=False)
    n_both = int(st.pattern_both.sum())
    # H4：地域
    reg = []
    for g in REGIONS:
        dd = d[d.region == g]
        rs = {v: mean_series(dd, v) for v in ["d1", "d100", "total", "light", "d10", "sdii"]}
        row = {"region": g, "n_stations": dd.station.nunique()}
        for v, s in rs.items():
            row[f"{v}_p1"], row[f"{v}_p2"] = pmean(s, P1), pmean(s, P2)
            row[f"{v}_diff"] = row[f"{v}_p2"] - row[f"{v}_p1"]
        row["d1_slope100_ols"] = ols_nw(rs["d1"])[0]
        row["d100_ratio"] = row["d100_p2"] / row["d100_p1"]
        row["pattern_both"] = bool(row["d1_diff"] < 0 and row["d100_diff"] > 0)
        row["n_station_pattern_both"] = int(st[st.region == g].pattern_both.sum())
        reg.append(row)
    reg = pd.DataFrame(reg)
    reg.round(4).to_csv(RES / "region_table.csv", index=False)

    # 年降水量
    bt, lot, hit, pt = ols_nw(ys["total"])

    # 頑健性
    rob = []
    def add(name, d1s, d100s, note=""):
        b = ols_nw(d1s)
        rob.append({"check": name, "d1_slope_per100y": round(b[0], 2), "d1_ci_lo": round(b[1], 2), "d1_ci_hi": round(b[2], 2),
                    "heavy_ratio_p2_p1": round(pmean(d100s, P2) / pmean(d100s, P1), 3) if d100s is not None else np.nan, "note": note})
    add("本線（1901〜2025年、≧1.0mm・≧100mm、最小二乗法）", ys["d1"], ys["d100"])
    add("期間 1931〜2025年", ys["d1"].loc[1931:], None, "強い雨は30年比較のため同じ値")
    add("期間 1961〜2025年", ys["d1"].loc[1961:], None)
    da = load()
    add("地点の平均を1991〜2020年平均との差で", mean_series(da, "d1", anomaly=True), mean_series(da, "d100", anomaly=True))
    di = load(include_insufficient=True)
    add("資料不足値「]」も含める", mean_series(di, "d1"), mean_series(di, "d100"))
    add("雨の日を ≧10mm に", ys["d10"], ys["d50"], "強い雨は ≧50mm に")
    rob = pd.DataFrame(rob)
    rob["d1_sen_per100y"] = [sen(ys["d1"]), sen(ys["d1"].loc[1931:]), sen(ys["d1"].loc[1961:]),
                             sen(mean_series(da, "d1", anomaly=True)), sen(mean_series(di, "d1")), sen(ys["d10"])]
    rob.to_csv(RES / "robustness.csv", index=False)
    rr61 = poisson_rr(d, y0=1961)
    rr50 = poisson_rr(d, v="d50")
    b50 = ols_nw(ys["d50"])

    res = {
        "n_stations": int(d.station.nunique()), "years": [1901, 2025],
        "H1_d1_slope_per100y": round(b1, 2), "H1_ci": [round(lo1, 2), round(hi1, 2)], "H1_p": p1v,
        "H1_support": bool(b1 <= -5 and hi1 < 0),
        "d1_mean_p1": round(pmean(ys["d1"], P1), 1), "d1_mean_p2": round(pmean(ys["d1"], P2), 1),
        "H2_d100_mean_p1": round(pmean(ys["d100"], P1), 3), "H2_d100_mean_p2": round(pmean(ys["d100"], P2), 3),
        "H2_ratio": round(r100, 3), "H2_support": bool(r100 >= 1.2),
        "d100_slope_per100y": round(b100, 3), "d100_ci": [round(lo100, 3), round(hi100, 3)],
        "d100_poisson_rr_per100y": round(rr, 3), "d100_poisson_rr_ci": [round(rrlo, 3), round(rrhi, 3)],
        "d100_poisson_rr_per100y_from1961": round(rr61[0], 3), "d100_poisson_rr_ci_from1961": [round(rr61[1], 3), round(rr61[2], 3)],
        "d50_poisson_rr_per100y": round(rr50[0], 3), "d50_poisson_rr_ci": [round(rr50[1], 3), round(rr50[2], 3)],
        "d50_ratio_p2_p1": round(pmean(ys["d50"], P2) / pmean(ys["d50"], P1), 3),
        "d100_total_days_51st_p1": round(pmean(ys["d100"], P1) * 51, 1), "d100_total_days_51st_p2": round(pmean(ys["d100"], P2) * 51, 1),
        "H3_n_both": n_both, "H3_share": round(n_both / len(st), 3), "H3_support": bool(n_both >= 26),
        "H3_n_d1_down": int((st.d1_diff < 0).sum()), "H3_n_d100_up": int((st.d100_diff > 0).sum()),
        "H3_n_d100_down": int((st.d100_diff < 0).sum()), "H3_n_d100_same": int((st.d100_diff == 0).sum()),
        "H3_n_both_with_d50": int(st.pattern_both_50.sum()),
        "H4_regions_pattern": {r.region: bool(r.pattern_both) for r in reg.itertuples()},
        "H4_support": bool(reg.pattern_both.all()),
        "total_slope_per100y": round(bt, 1), "total_ci": [round(lot, 1), round(hit, 1)], "total_p": pt,
        "total_mean_p1": round(pmean(ys["total"], P1), 1), "total_mean_p2": round(pmean(ys["total"], P2), 1),
        "jma_reference_dry_days_increase_per100y": 9.2,
    }
    (RES / "main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print(reg.round(2).to_string())


if __name__ == "__main__":
    main()
