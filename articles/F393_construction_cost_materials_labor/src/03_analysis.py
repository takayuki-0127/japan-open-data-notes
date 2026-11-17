"""非負の最小二乗で重みを推定し、期間ごとに資材と人件費の寄与に分ける。頑健性・問い直し（資材の内訳）。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy.optimize import nnls

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
MAT = ["wood", "ceramic", "steel", "metalprod", "nonferrous", "petro", "plastic"]
MAT_J = {"wood": "木材・木製品", "ceramic": "窯業・土石製品", "steel": "鉄鋼", "metalprod": "金属製品", "nonferrous": "非鉄金属",
         "petro": "石油・石炭製品", "plastic": "プラスチック製品"}
TARGETS = {"d_wood_house": "木造住宅", "d_nonwood_house": "非木造住宅", "d_housing": "住宅総合", "d_nonres": "非住宅総合"}
PERIODS = {"2013→2019": (2013, 2019), "2020→2025": (2020, 2025)}


def r(x, k=3):
    return None if x is None or pd.isna(x) else round(float(x), k)


def fit(P, target, wage="wage", start=1991, end=2025, mat_suffix="", fixed_labor=None):
    L = np.log(P)
    dl = L.diff().loc[start:end]
    mats = [m + mat_suffix for m in MAT]
    X = dl[mats + [wage]].dropna()
    y = dl.loc[X.index, target]
    ok = y.notna()
    X, y = X[ok], y[ok]
    if fixed_labor is None:
        w, _ = nnls(X.values, y.values)
    else:
        wm, _ = nnls(X[mats].values, (y - fixed_labor * X[wage]).values)
        w = np.append(wm, fixed_labor)
    fitted = X.values @ w
    r2 = 1 - ((y - fitted) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return dict(zip(mats + [wage], w)), float(r2), len(y)


def contrib(P, target, wts, period, wage="wage", mat_suffix=""):
    a, b = period
    L = np.log(P)
    d = L.loc[b] - L.loc[a]
    mats = [m + mat_suffix for m in MAT]
    cm = {m: wts[m] * d[m] for m in mats}
    cl = wts[wage] * d[wage]
    actual = d[target]
    return dict(actual=100 * actual, material=100 * sum(cm.values()), labor=100 * cl,
                other=100 * (actual - sum(cm.values()) - cl), by_material={m.replace(mat_suffix, ""): 100 * v for m, v in cm.items()})


def main():
    P = pd.read_csv(DATA / "fy_panel.csv", index_col=0)
    lw = pd.read_csv(DATA / "labor_weights.csv").set_index("deflator").labor_weight
    out = {"weights": {}, "contrib": {}}
    rows = []
    for t, tj in TARGETS.items():
        w, r2, n = fit(P, t)
        out["weights"][tj] = dict(**{MAT_J[k]: r(v) for k, v in w.items() if k in MAT}, 賃金=r(w["wage"]), 資材の合計=r(sum(w[m] for m in MAT)), r2=r(r2), n=n)
        for pn, per in PERIODS.items():
            c = contrib(P, t, w, per)
            out["contrib"].setdefault(tj, {})[pn] = {k: (r(v, 2) if not isinstance(v, dict) else {MAT_J[m]: r(x, 2) for m, x in v.items()}) for k, v in c.items()}
            rows.append(dict(target=tj, period=pn, actual=c["actual"], material=c["material"], labor=c["labor"], other=c["other"]))
    pd.DataFrame(rows).round(3).to_csv(RES / "contributions.csv", index=False)
    pd.DataFrame(out["weights"]).to_csv(RES / "weights.csv")

    # 当てはまり（木造住宅、年度ごとの前年度比：実際と推定）
    w, _, _ = fit(P, "d_wood_house")
    L = np.log(P).diff().loc[1991:2025]
    fitted = sum(w[k] * L[k] for k in w)
    fl = pd.DataFrame({"actual": 100 * L["d_wood_house"], "fitted": 100 * fitted,
                       "material": 100 * sum(w[m] * L[m] for m in MAT), "labor": 100 * w["wage"] * L["wage"]})
    fl.round(4).to_csv(RES / "fit_wood_house.csv")

    # 頑健性（木造住宅）
    T = "d_wood_house"
    rob = []
    def addrob(name, w, r2, wage="wage", suffix=""):
        c1 = contrib(P, T, w, PERIODS["2020→2025"], wage, suffix)
        c0 = contrib(P, T, w, PERIODS["2013→2019"], wage, suffix)
        rob.append(dict(check=name, labor_weight=r(w[wage]), material_weight=r(sum(w[m + suffix] for m in MAT)), r2=r(r2),
                        mat_2020_25=r(c1["material"], 2), lab_2020_25=r(c1["labor"], 2), mat_2013_19=r(c0["material"], 2), lab_2013_19=r(c0["labor"], 2)))
    w, r2, _ = fit(P, T); addrob("0 主（1991〜2025年度、1人当たり賃金）", w, r2)
    w, r2, _ = fit(P, T, wage="wage_hourly"); addrob("1 賃金を1時間当たりに", w, r2, wage="wage_hourly")
    w, r2, _ = fit(P, T, start=2000); addrob("2 推定期間を2000〜2025年度に", w, r2)
    w, r2, _ = fit(P, T, fixed_labor=float(lw["住宅建築（木造）"])); addrob("3 労務の重みを公表値（41.5%）に固定", w, r2)
    w, r2, _ = fit(P, T, mat_suffix="_lag6"); addrob("4 資材の指数を半年前にずらす", w, r2, suffix="_lag6")
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.to_dict(orient="records")
    out["official_labor_weight"] = {k: r(v, 4) for k, v in lw.items()}

    # 指数そのものの変化（参考）
    lv = {}
    for pn, (a, b) in PERIODS.items():
        lv[pn] = {c: r(100 * (P.loc[b, c] / P.loc[a, c] - 1), 1) for c in ["d_wood_house", "d_nonwood_house", "d_housing", "d_nonres", "wage", "wage_hourly", "hours"] + MAT}
    out["index_change_pct"] = lv
    P.round(4).to_csv(RES / "fy_panel_used.csv")

    cw = out["contrib"]["木造住宅"]; cn = out["contrib"]["非木造住宅"]
    out["hypotheses"] = {
        "H1": dict(value=[cw["2020→2025"]["material"], cw["2020→2025"]["labor"]], verdict="支持" if cw["2020→2025"]["material"] > cw["2020→2025"]["labor"] else "外れ"),
        "H2": dict(value=[cw["2013→2019"]["material"], cw["2013→2019"]["labor"]], verdict="支持" if cw["2013→2019"]["labor"] > cw["2013→2019"]["material"] else "外れ"),
        "H3": dict(value=[out["weights"]["木造住宅"]["賃金"], r(lw["住宅建築（木造）"])], verdict="支持" if abs(out["weights"]["木造住宅"]["賃金"] - lw["住宅建築（木造）"]) <= 0.15 else "外れ"),
        "H4": dict(value=[cn["2020→2025"]["material"], cn["2020→2025"]["labor"]], verdict="支持" if cn["2020→2025"]["material"] > cn["2020→2025"]["labor"] else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ["weights", "contrib", "hypotheses", "index_change_pct"]}, ensure_ascii=False, indent=0))
    print(rob.to_string())


if __name__ == "__main__":
    main()
