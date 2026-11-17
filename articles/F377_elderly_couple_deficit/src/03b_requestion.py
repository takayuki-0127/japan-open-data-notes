"""03b_requestion.py : 問い直し（結果を見てから足した）。
2018年1月の家計簿の改正（口座への入金の欄ができた）の前後で、公的年金給付と預貯金に段差があるか。
段差を記入のしかたの変化とみなした場合、2019年以降の不足分は旧い家計簿の物差しでどのくらいになるか（試算）。
出力：results/requestion.csv, results/requestion.json
"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"

GROUPS = ["couple_6560", "couple_65", "head65_nojob", "elder_nojob"]


def main():
    df = pd.read_csv(DATA / "kakei_elderly_long.csv")
    w = df.pivot_table(index=["group", "year"], columns="item", values="value").reset_index()
    w["deficit"] = w["実支出"] - w["実収入"]
    out = {}
    rows = []
    for g in GROUPS:
        s = w[w["group"] == g].set_index("year").sort_index()
        pen = s["公的年金給付"]
        yoy = pen.pct_change() * 100
        base = yoy.loc[2001:2017]
        step2 = (pen.loc[2019] / pen.loc[2017] - 1) * 100
        dep = s["預貯金"]
        dep_yoy = dep.pct_change() * 100
        rec = {
            "pension_yoy_2001_2017_median": round(float(base.median()), 2),
            "pension_yoy_2001_2017_min": round(float(base.min()), 2),
            "pension_yoy_2001_2017_max": round(float(base.max()), 2),
            "pension_yoy_2018": round(float(yoy.loc[2018]), 2),
            "pension_yoy_2019": round(float(yoy.loc[2019]), 2),
            "pension_change_2017_2019_pct": round(float(step2), 2),
            "pension_change_2017_2019_yen": int(round(float(pen.loc[2019] - pen.loc[2017]))),
            "deposit_yoy_2001_2017_max": round(float(dep_yoy.loc[2001:2017].max()), 2),
            "deposit_change_2017_2019_pct": round(float((dep.loc[2019] / dep.loc[2017] - 1) * 100), 2),
            "consumption_change_2017_2019_pct": round(float((s.loc[2019, "消費支出"] / s.loc[2017, "消費支出"] - 1) * 100), 2),
        }
        # 試算：2017→2019年の年金の伸びのうち、2001〜2017年の中央値の伸び（2年分）を超える部分を「記入のしかたの段差」とみなす
        typical = (1 + base.median() / 100) ** 2
        step_yen = float(pen.loc[2019] - pen.loc[2017] * typical)
        step_ratio = float(pen.loc[2019] / (pen.loc[2017] * typical))
        rec["assumed_step_yen_2019"] = int(round(step_yen))
        rec["assumed_step_ratio"] = round(step_ratio, 4)
        # 2019年以降の年金を step_ratio で割って旧い物差しに戻した不足分（2018年は半分の世帯が新しい家計簿なので半分の段差）
        adj = s["deficit"].copy()
        for y in s.index:
            if y >= 2019:
                adj.loc[y] = s.loc[y, "deficit"] + pen.loc[y] * (1 - 1 / step_ratio)
            elif y == 2018:
                adj.loc[y] = s.loc[y, "deficit"] + pen.loc[y] * (1 - 1 / np.sqrt(step_ratio))
        rec["deficit_mean_2021_2025"] = int(round(float(s.loc[2021:2025, "deficit"].mean())))
        rec["deficit_mean_2021_2025_oldbook"] = int(round(float(adj.loc[2021:2025].mean())))
        rec["deficit_2025_oldbook"] = int(round(float(adj.loc[2025])))
        rec["deficit_2017"] = int(round(float(s.loc[2017, "deficit"])))
        rec["deficit_drop_2017_2019"] = int(round(float(s.loc[2017, "deficit"] - s.loc[2019, "deficit"])))
        rec["h1_diff_2017_minus_oldbook_mean"] = rec["deficit_2017"] - rec["deficit_mean_2021_2025_oldbook"]
        rec["deficit_mean_2013_2017"] = int(round(float(s.loc[2013:2017, "deficit"].mean())))
        rec["deficit_mean_2000_2004"] = int(round(float(s.loc[2000:2004, "deficit"].mean())))
        out[g] = rec
        for y in s.index:
            rows.append((g, int(y), float(pen.loc[y]), float(yoy.loc[y]) if y > 2000 else np.nan,
                         float(dep.loc[y]), float(s.loc[y, "deficit"]), float(adj.loc[y])))
    pd.DataFrame(rows, columns=["group", "year", "pension", "pension_yoy_pct", "deposit", "deficit",
                                "deficit_oldbook_trial"]).to_csv(RES / "requestion.csv", index=False,
                                                                 float_format="%.2f")
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
