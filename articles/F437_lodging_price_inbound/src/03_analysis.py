"""03 分析：宿泊料の年ごとの上がり方、訪日客との相関（前年同月比）、仮説、頑健性。
2020年1月〜2023年12月は Go To トラベル・全国旅行支援の割引とコロナの時期なので、その月と、その月を前年に持つ2024年の前年同月比は、相関・回帰から除く（2020年1月〜2024年12月を除く）。
出力：results/main.json, results/annual.csv, results/lag_corr.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def yoy(s, k=12):
    return (s / s.shift(k) - 1) * 100


def ok_period(idx, start=201301, end=209912):
    i = pd.Index(idx)
    return (i >= start) & (i <= end) & ~((i >= 202001) & (i <= 202412))


def corr(a, b):
    x = pd.concat([a, b], axis=1).dropna()
    return float(np.corrcoef(x.iloc[:, 0], x.iloc[:, 1])[0, 1]), int(len(x))


def main():
    m = pd.read_csv(D / "monthly.csv").set_index("ym")
    m["year"] = m.index // 100
    a = m[m.year <= 2025].groupby("year")[["lodging_z", "lodging_t", "all_z", "visitors"]].agg({"lodging_z": "mean", "lodging_t": "mean", "all_z": "mean", "visitors": "sum"})
    a.loc[a.visitors == 0, "visitors"] = np.nan
    a["real_lodging"] = a.lodging_z / a.all_z * 100
    a.round(4).to_csv(R / "annual.csv")
    same = bool((m.lodging_z.dropna() - m.lodging_t.reindex(m.lodging_z.dropna().index)).abs().max() < 1e-9)
    y = pd.DataFrame({"lodging": yoy(m.lodging_z), "all": yoy(m.all_z), "vis": yoy(m.visitors), "real": yoy(m.lodging_z / m.all_z)})
    keep = ok_period(y.index)
    lag = []
    for L in range(0, 7):
        r, n = corr(y.vis.shift(L)[keep], y.lodging[keep])
        r1, _ = corr(y.vis.shift(L)[ok_period(y.index, 201301, 201912)], y.lodging[ok_period(y.index, 201301, 201912)])
        lag.append(dict(lead_months=L, corr_all=r, corr_2013_2019=r1, n=n))
    lag = pd.DataFrame(lag); lag.round(4).to_csv(R / "lag_corr.csv", index=False)
    k19 = ok_period(y.index, 201301, 201912)
    r_h3, n_h3 = corr(y.vis[k19], y.lodging[k19])
    x = pd.concat([y.vis[keep], y.lodging[keep]], axis=1).dropna()
    b = np.polyfit(x.vis, x.lodging, 1)
    p2425 = (y.index >= 202401) & (y.index <= 202512)
    main = dict(lodging_z_equals_kubu_all_months=same,
                lodging_2012=float(a.lodging_z[2012]), lodging_2019=float(a.lodging_z[2019]), lodging_2025=float(a.lodging_z[2025]),
                lodging_2012_2019_pct=float((a.lodging_z[2019] / a.lodging_z[2012] - 1) * 100),
                lodging_2019_2025_pct=float((a.lodging_z[2025] / a.lodging_z[2019] - 1) * 100),
                all_2012_2019_pct=float((a.all_z[2019] / a.all_z[2012] - 1) * 100), all_2019_2025_pct=float((a.all_z[2025] / a.all_z[2019] - 1) * 100),
                visitors_2012=float(a.visitors[2012] / 1e6), visitors_2019=float(a.visitors[2019] / 1e6), visitors_2025=float(a.visitors[2025] / 1e6),
                corr_vis_lodging_2013_2019=r_h3, n_2013_2019=n_h3,
                corr_vis_lodging_all=corr(y.vis[keep], y.lodging[keep])[0], n_all=int(len(x)),
                slope_pt_per_10pt_visitors=float(b[0] * 10), best_lead=int(lag.loc[lag.corr_all.idxmax(), "lead_months"]), best_lead_corr=float(lag.corr_all.max()),
                lodging_yoy_2024_2025=float(y.lodging[p2425].mean()), all_yoy_2024_2025=float(y["all"][p2425].mean()),
                lodging_yoy_2024=float(y.lodging[(y.index >= 202401) & (y.index <= 202412)].mean()), lodging_yoy_2025=float(y.lodging[(y.index >= 202501) & (y.index <= 202512)].mean()),
                lodging_yoy_2026_to_sep=float(y.lodging[(y.index >= 202601) & (y.index <= 202609)].mean()),
                vis_yoy_2026_to_sep=float(y.vis[(y.index >= 202601) & (y.index <= 202609)].mean()))
    main["H1"] = "判定できない（全国と東京都区部の宿泊料が全月で同じ値）" if same else ("支持" if a.lodging_t[2025] / a.lodging_t[2019] > a.lodging_z[2025] / a.lodging_z[2019] else "外れ")
    main["H2"] = "支持" if main["lodging_2012_2019_pct"] >= 10 else "外れ"
    main["H3"] = "支持" if r_h3 >= 0.3 else "外れ"
    main["H4"] = "支持" if main["lodging_yoy_2024_2025"] >= 2 * main["all_yoy_2024_2025"] else "外れ"
    # 頑健性
    rob = []
    k24 = ok_period(y.index, 202501, 209912)
    rob.append(dict(check="相関（前年同月比）2025年1月〜2026年9月", value=corr(y.vis[k24], y.lodging[k24])[0], n=corr(y.vis[k24], y.lodging[k24])[1]))
    k10 = ok_period(y.index, 201001, 201912)
    rob.append(dict(check="相関（前年同月比）2010〜2019年", value=corr(y.vis[k10], y.lodging[k10])[0], n=corr(y.vis[k10], y.lodging[k10])[1]))
    rob.append(dict(check="相関（実質の宿泊料＝宿泊料÷総合の前年同月比）2013〜2019年＋2025年〜", value=corr(y.vis[keep], y.real[keep])[0], n=corr(y.vis[keep], y.real[keep])[1]))
    ma = m[["lodging_z", "visitors"]].rolling(12).mean()
    y12 = pd.DataFrame({"l": yoy(ma.lodging_z), "v": yoy(ma.visitors)})
    k12 = ok_period(y12.index, 201301, 201912)
    rob.append(dict(check="相関（12か月平均の前年比）2013〜2019年", value=corr(y12.v[k12], y12.l[k12])[0], n=corr(y12.v[k12], y12.l[k12])[1]))
    ky = [yy for yy in range(2004, 2020)]
    ay = a.loc[ky]; ry = np.corrcoef(np.diff(np.log(ay.visitors)), np.diff(np.log(ay.lodging_z)))[0, 1]
    rob.append(dict(check="相関（年平均の対数差）2004〜2019年", value=float(ry), n=len(ky) - 1))
    k2 = (y.index >= 202401) & (y.index <= 202412)
    rob.append(dict(check="参考：相関（前年同月比）2024年（前年が割引の時期）", value=corr(y.vis[k2], y.lodging[k2])[0], n=corr(y.vis[k2], y.lodging[k2])[1]))
    rob.append(dict(check="実質の宿泊料（宿泊料÷総合）2019→2025年（%）", value=float((a.real_lodging[2025] / a.real_lodging[2019] - 1) * 100), n=None))
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    y.round(4).to_csv(R / "yoy.csv")
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(lag.round(3).to_string()); print(pd.DataFrame(rob).to_string())
    print(a.loc[2003:].round(1).to_string())


if __name__ == "__main__":
    main()
