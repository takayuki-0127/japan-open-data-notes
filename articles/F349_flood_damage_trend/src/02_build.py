"""data/raw から年ごとの表 data/flood_damage.csv を作る（オフライン）。
単位：被害額は億円（名目・平成27年価格）、国民所得は億円（名目・実質）。人的被害の列は読まない。"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def year_of(x):
    s = str(x).strip()
    return int(s[:4]) if s[:4].isdigit() and s.endswith("年") else None


def main():
    a = pd.read_excel(RAW / "suigai_hyo44_damage_1875_2023.xlsx", header=None)
    b = pd.read_excel(RAW / "suigai_hyo45_damage_vs_income_1879_2023.xlsx", header=None)
    assert str(a.iat[3, 6]).strip() == "名目額" and "平成２７年価格" in str(a.iat[3, 7])
    assert "実質（Ａ）" in str(b.iat[4, 3]) and "実質（Ｂ）" in str(b.iat[4, 5])
    rows = {}
    for i in range(5, len(a)):
        y = year_of(a.iat[i, 0])
        if y is None:
            continue
        nom = num(a.iat[i, 6])
        # 名目額の単位：1945年までは千円、1946年以降は百万円 → 億円にそろえる
        nom_oku = nom / 1e5 if y <= 1945 else nom / 1e2
        rows[y] = dict(year=y, damage_nominal_oku=nom_oku, damage_real2015_oku=num(a.iat[i, 7]))
    for i in range(6, len(b)):
        y = year_of(b.iat[i, 0])
        if y is None or y not in rows:
            continue
        ni = num(b.iat[i, 2])
        rows[y].update(ni_nominal_oku=ni / 1e2 if y <= 1942 else ni, ni_real2015_oku=num(b.iat[i, 3]), damage_ratio_pct_table=num(b.iat[i, 6]))
    df = pd.DataFrame(list(rows.values())).sort_values("year")
    df["source_period"] = np.where(df.year >= 1961, "水害統計（1961〜）", np.where(df.year >= 1946, "戦後水害被害額推計（1946〜60）", "内務省統計年報（〜1945）"))
    df.to_csv(ROOT / "data" / "flood_damage.csv", index=False)
    print(df.shape, df.dropna().year.min(), df.year.max())
    print(df[df.year.isin([1961, 1990, 2018, 2019, 2023])].to_string())


if __name__ == "__main__":
    main()
