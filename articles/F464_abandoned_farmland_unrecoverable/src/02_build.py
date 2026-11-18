"""data/kouhai_pref_raw.csv（01b_extract.py が PDF から抜き出したもの）を確かめ、分析用の data/panel.csv を作る。
確かめ：47都道府県の合計と全国の行の差が各列で±10ha 以内、A+B と面積計の差が±5ha 以内。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
REGION = {1: "北海道", **{c: "東北" for c in range(2, 8)}, **{c: "関東・東山" for c in list(range(8, 15)) + [19, 20]},
          **{c: "北陸" for c in range(15, 19)}, **{c: "東海" for c in range(21, 25)}, **{c: "近畿" for c in range(25, 31)},
          **{c: "中国" for c in range(31, 36)}, **{c: "四国" for c in range(36, 40)}, **{c: "九州" for c in range(40, 47)}, 47: "沖縄"}


def main():
    df = pd.read_csv(D / "kouhai_pref_raw.csv")
    checks = []
    for y, g in df.groupby("year", sort=True):
        nat = g[g.pref_code == 0].iloc[0]
        pr = g[g.pref_code > 0]
        assert len(pr) == 47
        for c in ["total", "A", "B", "reclaimed", "new", "total_n", "A_n", "B_n"]:
            if pd.isna(nat[c]):
                continue
            diff = int(pr[c].sum() - nat[c])
            assert abs(diff) <= 10, (y, c, diff)
            checks.append({"year": int(y), "col": c, "national": int(nat[c]), "sum47_minus_national": diff})
        gap = (g.A + g.B - g.total).abs().max()
        assert gap <= 5, (y, gap)
    pd.DataFrame(checks).to_csv(R / "build_checks.csv", index=False)
    pan = df[df.pref_code > 0].copy()
    pan["region"] = pan.pref_code.map(REGION)
    pan["regime"] = (pan.year >= 2021).map({False: "2011-2020", True: "2021-"})
    pan = pan.sort_values(["year", "pref_code"]).reset_index(drop=True)
    pan.to_csv(D / "panel.csv", index=False)
    print("panel", pan.shape)


if __name__ == "__main__":
    main()
