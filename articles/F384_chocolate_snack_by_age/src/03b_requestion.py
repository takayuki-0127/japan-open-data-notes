"""03b 問い直し（結果を見てから足した）：同じ生まれ年の世帯を10年ごとに追う。
世帯主の年齢の10歳きざみと10年の間隔をそろえ、ある年に年齢 g だった世帯の層が、10年後に年齢 g+1 の層としてどれだけ買っているか（実質）を見る。
窓：2005〜07年 → 2015〜17年、2013〜15年 → 2023〜25年。
比べるもの：(a) 同じ層を10年追った変化、(b) 始めの年の「1つ上の年齢との差」（年齢の差だけなら、10年後はこの差のとおりに動くはず）
出力：results/requestion.json, results/cohort.csv"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
WINDOWS = {"2005-07→2015-17": ([2005, 2006, 2007], [2015, 2016, 2017]), "2013-15→2023-25": ([2013, 2014, 2015], [2023, 2024, 2025])}


def main():
    b = pd.read_csv(RES / "by_year.csv")
    # レビューで追加：チョコを菓子類の指数で割った実質（物価の指数の選び方で結果が変わるかを見る）
    b["choco_real_sweetscpi"] = b["choco"] * 100.0 / b["cpi_sweets"]
    b["snack_real_sweetscpi"] = b["snack"] * 100.0 / b["cpi_sweets"]
    rows = []
    for item in ["choco_real", "snack_real", "choco_real_sweetscpi", "snack_real_sweetscpi"]:
        for wname, (s, e) in WINDOWS.items():
            a = b[b.year.isin(s)].groupby("group")[item].mean()
            z = b[b.year.isin(e)].groupby("group")[item].mean()
            for i in range(len(AGES) - 2):  # 70歳以上は幅が広いので、行き先は60代まで
                g0, g1 = AGES[i], AGES[i + 1]
                rows.append({"item": item, "window": wname, "from_age": g0, "to_age": g1,
                             "start": round(a[g0], 1), "cohort_end": round(z[g1], 1),
                             "cohort_pct": round(100 * (z[g1] / a[g0] - 1), 1),
                             "age_gap_pct_at_start": round(100 * (a[g1] / a[g0] - 1), 1),
                             "same_age_pct": round(100 * (z[g1] / a[g1] - 1), 1)})
    d = pd.DataFrame(rows)
    d.to_csv(RES / "cohort.csv", index=False)
    out = {}
    for (item, wname), g in d.groupby(["item", "window"], sort=True):
        out.setdefault(item, {})[wname] = {r.from_age + "→" + r.to_age: {"cohort_pct": r.cohort_pct, "age_gap_pct_at_start": r.age_gap_pct_at_start,
                                                                       "same_age_pct": r.same_age_pct} for r in g.itertuples()}
        out[item][wname]["n_cohort_above_gap"] = int((g.cohort_pct > g.age_gap_pct_at_start).sum())
        out[item][wname]["n"] = int(len(g))
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(d.to_string())


if __name__ == "__main__":
    main()
