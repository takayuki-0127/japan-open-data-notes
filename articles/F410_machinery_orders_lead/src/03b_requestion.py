"""問い直し（結果を見てから足した）：先取りの長さは、期間によって変わったのか。
(1) 8年（32四半期）の窓をずらしながら、相関が最大になるずれを求める。
(2) 設備投資（名目）に対する機械受注（船舶・電力を除く民需）の大きさの比の推移。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
W = 32


def main():
    q = pd.read_csv(R / "quarterly_panel.csv").set_index("t")
    y = np.log(q["capex_nominal"] / q["capex_nominal"].shift(4)) * 100
    x = np.log(q["core"] / q["core"].shift(4)) * 100
    valid = pd.concat([y, x], axis=1).dropna().index
    rows = []
    for end in valid:
        win = [t for t in valid if end - W < t <= end]
        if len(win) < W:
            continue
        cs = {}
        for k in range(0, 5):
            z = pd.concat([y, x.shift(k)], axis=1).loc[win].dropna()
            cs[k] = float(z.iloc[:, 0].corr(z.iloc[:, 1]))
        kb = max(cs, key=cs.get)
        rows.append({"end_label": q.loc[end, "label"], "best_lag_q": kb, "best_corr": round(cs[kb], 4), **{f"corr_lag{k}": round(v, 4) for k, v in cs.items()}})
    rw = pd.DataFrame(rows); rw.to_csv(R / "requestion_rolling_lag.csv", index=False)
    # 比：受注（四半期の合計、百万円）を年率に（×4）して兆円、設備投資（年率、10億円）を兆円に
    q["year"] = q["label"].str[:4].astype(int)
    a = q.dropna(subset=["core"]).groupby("year").agg(core=("core", "sum"), capex=("capex_nominal", "mean"), n=("core", "size"))
    a = a[a["n"] == 4]
    a["orders_tn"] = a["core"] / 1e6
    a["capex_tn"] = a["capex"] / 1e3
    a["ratio_pct"] = a["orders_tn"] / a["capex_tn"] * 100
    a[["orders_tn", "capex_tn", "ratio_pct"]].round(3).to_csv(R / "requestion_coverage.csv")
    out = {
        "window_quarters": W, "n_windows": int(len(rw)),
        "first_window_end": rw["end_label"].iloc[0], "last_window_end": rw["end_label"].iloc[-1],
        "first_window_best_lag": int(rw["best_lag_q"].iloc[0]), "first_window_best_corr": float(rw["best_corr"].iloc[0]),
        "last_window_best_lag": int(rw["best_lag_q"].iloc[-1]), "last_window_best_corr": float(rw["best_corr"].iloc[-1]),
        "last_window_corr_lag0": float(rw["corr_lag0"].iloc[-1]), "last_window_corr_lag1": float(rw["corr_lag1"].iloc[-1]),
        "last_window_corr_lag2": float(rw["corr_lag2"].iloc[-1]),
        "share_windows_lag0": round(float((rw["best_lag_q"] == 0).mean() * 100), 1),
        "share_windows_lag1to3": round(float(rw["best_lag_q"].between(1, 3).mean() * 100), 1),
        "first_window_lag0_label": str(rw.loc[rw["best_lag_q"] == 0, "end_label"].iloc[0]) if (rw["best_lag_q"] == 0).any() else None,
        "ratio_2006": round(float(a.loc[2006, "ratio_pct"]), 2), "ratio_2019": round(float(a.loc[2019, "ratio_pct"]), 2),
        "ratio_2025": round(float(a.loc[2025, "ratio_pct"]), 2),
        "orders_2006_tn": round(float(a.loc[2006, "orders_tn"]), 2), "orders_2025_tn": round(float(a.loc[2025, "orders_tn"]), 2),
        "capex_2006_tn": round(float(a.loc[2006, "capex_tn"]), 2), "capex_2025_tn": round(float(a.loc[2025, "capex_tn"]), 2),
    }
    (R / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(out); print(rw.iloc[::8].to_string()); print(a.round(2).to_string())


if __name__ == "__main__":
    main()
