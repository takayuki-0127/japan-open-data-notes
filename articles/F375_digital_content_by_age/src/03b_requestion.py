"""03b_requestion.py : 問い直し（結果を見てから足した）。
～34歳の世帯が多く使うのは、ひとり暮らし（単身世帯）が多いからか。総世帯 = 単身世帯と二人以上の世帯の混ざりとみて、
単身の割合を世帯人員から求め、65～74歳と同じ単身の割合だったら ～34歳の額はいくらか、を計算する（オフライン）。"""
import json
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def main():
    a = pd.read_csv(ROOT / "data" / "age_items.csv")
    w = a[a.table == "t1_2"].pivot_table(index=["year", "hh", "age"], columns="item", values="value")
    w["D"] = w["ebook"] + w["download"]
    rows = []
    for y in range(2015, 2026):
        g = lambda hh, age, c: w.loc[(y, hh, age), c]
        out = {"year": y}
        for lab, age, sage in [("young", "A:-34", "S:-34"), ("old", "A:65-74", "S:60-")]:
            n_tot, n_two = g("total", age, "hh_size"), g("two_plus", age, "hh_size")
            p = (n_two - n_tot) / (n_two - 1.0)                     # 単身の割合（世帯人員から）
            d_s, d_t, d_tot = g("single", sage, "D"), g("two_plus", age, "D"), g("total", age, "D")
            out.update({f"p_single_{lab}": p, f"D_single_{lab}": d_s, f"D_two_{lab}": d_t, f"D_total_{lab}": d_tot,
                        f"D_mix_{lab}": p * d_s + (1 - p) * d_t})
        out["D_young_cf"] = out["p_single_old"] * out["D_single_young"] + (1 - out["p_single_old"]) * out["D_two_young"]
        out["ratio_actual"] = out["D_total_young"] / out["D_total_old"]
        out["ratio_cf"] = out["D_young_cf"] / out["D_mix_old"]
        out["ratio_two_plus"] = out["D_two_young"] / out["D_two_old"]
        rows.append(out)
    d = pd.DataFrame(rows).round(4)
    d.to_csv(RES / "single_mix.csv", index=False)
    r25 = d[d.year == 2025].iloc[0]
    Q = {k: (int(v) if k == "year" else round(float(v), 4)) for k, v in r25.items()}
    Q["mix_fit_max_abs_rel_err_young"] = round(float(((d.D_mix_young - d.D_total_young) / d.D_total_young).abs().max()), 4)
    Q["log_share_explained_by_single_mix_2025"] = round(float(1 - np.log(r25.ratio_cf) / np.log(r25.D_mix_young / r25.D_mix_old)), 4)
    Q["ratio_cf_2015_2017"] = round(float(d[d.year <= 2017].ratio_cf.mean()), 3)
    Q["ratio_cf_2023_2025"] = round(float(d[d.year >= 2023].ratio_cf.mean()), 3)
    (RES / "requestion.json").write_text(json.dumps(Q, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(Q, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
