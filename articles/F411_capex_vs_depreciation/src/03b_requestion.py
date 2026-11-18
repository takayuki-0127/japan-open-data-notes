"""問い直し：比が1を超えていても、帳簿の上の設備（土地を除く有形固定資産＋建設仮勘定）は増えてきたのか。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def r6(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 6)


def main():
    fy = pd.read_csv(D / "fiscal_year.csv")
    out, rq = [], {}
    for ind in ["all", "mfg", "nonmfg"]:
        for size in ["A", "B", "D"]:
            z = fy[(fy["ind"] == ind) & (fy["size"] == size)].set_index("fy").copy()
            z["stock"] = z["tangible_exland"] + z["cip"]
            z["stock_growth_pct"] = (z["stock"] / z["stock"].shift(1) - 1) * 100
            z["net_exsw"] = z["capex_exsw"] - z["dep"]
            z["net_over_stock_pct"] = z["net_exsw"] / z["stock"].shift(1) * 100
            for y, r in z.iterrows():
                out.append({"ind": ind, "size": size, "fy": int(y), "stock_oku": r6(r["stock"]),
                            "stock_growth_pct": r6(r["stock_growth_pct"]), "net_exsw_oku": r6(r["net_exsw"]),
                            "net_over_stock_pct": r6(r["net_over_stock_pct"])})
            key = f"{ind}_{size}"
            g = {}
            for a, b in [(1974, 1990), (1991, 2001), (2002, 2012), (2013, 2025)]:
                s = z.loc[a:b]
                g[f"{a}_{b}"] = {"stock_growth_pct_mean": r6(s["stock_growth_pct"].mean()),
                                 "net_over_stock_pct_mean": r6(s["net_over_stock_pct"].mean())}
            s0, s1 = z.loc[2002, "stock"], z.loc[2025, "stock"]
            cum_net = z.loc[2003:2025, "net_exsw"].sum()
            for yy in (1990, 1998, 2012):
                g[f"stock_{yy}_tril"] = r6(z.loc[yy, "stock"] / 1e4)
            g["stock_peak_fy"] = int(z["stock"].idxmax()); g["stock_peak_tril"] = r6(z["stock"].max() / 1e4)
            pk = int(z["stock"].idxmax()); after = z.loc[pk:, "stock"]
            g["stock_min_after_peak_fy"] = int(after.idxmin()); g["stock_min_after_peak_tril"] = r6(after.min() / 1e4)
            g["stock_2002_tril"] = r6(s0 / 1e4); g["stock_2025_tril"] = r6(s1 / 1e4)
            g["stock_change_2002_2025_tril"] = r6((s1 - s0) / 1e4)
            g["cum_net_exsw_2003_2025_tril"] = r6(cum_net / 1e4)
            g["stock_growth_2002_2025_pct"] = r6((s1 / s0 - 1) * 100)
            g["n_years_stock_down_2002_2025"] = int((z.loc[2003:2025, "stock_growth_pct"] < 0).sum())
            rq[key] = g
    pd.DataFrame(out).to_csv(R / "requestion_stock.csv", index=False)
    (R / "requestion.json").write_text(json.dumps(rq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rq["all_A"], ensure_ascii=False, indent=1))
    for k in ["mfg_A", "nonmfg_A", "all_B", "all_D"]:
        print(k, rq[k]["stock_growth_2002_2025_pct"], rq[k]["2013_2025"])


if __name__ == "__main__":
    main()
