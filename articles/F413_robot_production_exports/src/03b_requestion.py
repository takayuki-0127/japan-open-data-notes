"""問い直し：金額で見た輸出の割合（約4割）と、台数で見た割合（約7〜8割）が大きく違う。
輸出1台あたりの額は、国内で作るロボット1台あたりの額より安いのか。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def r6(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 6)


def main():
    t = pd.read_csv(R / "annual_panel.csv", index_col=0)
    e = pd.read_csv(D / "exports_by_country.csv", dtype={"hs": str})
    u = pd.DataFrame(index=t.index)
    u["prod_unit_value_man"] = t["prod_value_pb_nc_oku"] / t["prod_units_pb_nc"] * 1e4  # 万円／台
    u["exp_unit_value_man"] = t["exp_oku"] / t["exp_units"] * 1e4
    u["exp_over_prod_unit_value"] = u["exp_unit_value_man"] / u["prod_unit_value_man"]
    # 国別の1台あたりの額（2025年、輸出額の上位）
    z = e[e["year"] == 2025].groupby("country")[["value_kyen", "units"]].sum()
    z["unit_value_man"] = z["value_kyen"] / z["units"] / 10  # 千円 → 万円
    z = z.sort_values("value_kyen", ascending=False).head(6)
    u.to_csv(R / "requestion_unit_value.csv", float_format="%.6f")
    rq = {"prod_unit_value_2009": r6(u.loc[2009, "prod_unit_value_man"]), "prod_unit_value_2025": r6(u.loc[2025, "prod_unit_value_man"]),
          "exp_unit_value_2009": r6(u.loc[2009, "exp_unit_value_man"]), "exp_unit_value_2025": r6(u.loc[2025, "exp_unit_value_man"]),
          "ratio_unit_value_2009": r6(u.loc[2009, "exp_over_prod_unit_value"]), "ratio_unit_value_2025": r6(u.loc[2025, "exp_over_prod_unit_value"]),
          "ratio_unit_value_mean": r6(u["exp_over_prod_unit_value"].mean()), "ratio_unit_value_min": r6(u["exp_over_prod_unit_value"].min()),
          "ratio_unit_value_max": r6(u["exp_over_prod_unit_value"].max()),
          "exp_unit_value_growth_2009_2025": r6(u.loc[2025, "exp_unit_value_man"] / u.loc[2009, "exp_unit_value_man"]),
          "prod_unit_value_growth_2009_2025": r6(u.loc[2025, "prod_unit_value_man"] / u.loc[2009, "prod_unit_value_man"]),
          "unit_value_by_country_2025": {str(int(k)): r6(v) for k, v in z["unit_value_man"].items()}}
    (R / "requestion.json").write_text(json.dumps(rq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(u.round(2).to_string()); print(rq)


if __name__ == "__main__":
    main()
