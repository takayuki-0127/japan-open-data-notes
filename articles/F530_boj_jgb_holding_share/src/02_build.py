"""02 整形：API の JSON を、期×系列の表にする（億円）。
資金循環統計の四半期の日付 YYYY0Q（例 202602＝2026年4〜6月期）を「2026Q2」にする。
日本銀行勘定は月末の値なので、四半期末の月（3・6・9・12月）だけを残して同じ形にする。
系列の名前は、JSON の系列の名称（日本語）から部門の文字で付け、コードと名前の対応を data/series_names.csv に残す。
出力：data/ff_quarterly.csv（期×コード）、data/bs01_quarterly.csv、data/series_names.csv
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"


def main():
    ff = json.load(open(RAW / "boj_ff_jgb.json", encoding="utf-8"))
    rows, names = [], []
    for s in ff:
        names.append({"code": s["SERIES_CODE"], "name": s["NAME_OF_TIME_SERIES_J"], "unit": s["UNIT_J"]})
        for d, v in zip(s["VALUES"]["SURVEY_DATES"], s["VALUES"]["VALUES"]):
            y, q = divmod(int(d), 100)
            assert 1 <= q <= 4
            rows.append({"period": f"{y}Q{q}", "code": s["SERIES_CODE"], "value": v})
    t = pd.DataFrame(rows).pivot(index="period", columns="code", values="value").sort_index()
    t = t[sorted(t.columns)]
    t.to_csv(D / "ff_quarterly.csv")
    pd.DataFrame(names).sort_values("code").to_csv(D / "series_names.csv", index=False)

    bs = json.load(open(RAW / "boj_bs01_jgb.json", encoding="utf-8"))
    rows = []
    for s in bs:
        for d, v in zip(s["VALUES"]["SURVEY_DATES"], s["VALUES"]["VALUES"]):
            y, m = divmod(int(d), 100)
            if m in (3, 6, 9, 12) and v is not None:
                rows.append({"period": f"{y}Q{m // 3}", "code": s["SERIES_CODE"], "value": v})
    b = pd.DataFrame(rows).pivot(index="period", columns="code", values="value").sort_index()
    b.to_csv(D / "bs01_quarterly.csv")
    print(t.shape, t.index[0], t.index[-1], b.shape)


if __name__ == "__main__":
    main()
