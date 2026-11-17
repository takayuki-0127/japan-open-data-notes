"""02_build.py : data/raw の家計調査 第3-2表・第3-11表（2000〜2025年）と消費者物価指数から、分析用の CSV を作る（オフライン）。
出力：data/kakei_pocket_long.csv（年・世帯の種類・項目・値）、data/cpi_annual.csv
"""
import pathlib
import re

import pandas as pd

import kakei

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
YEARS = list(range(2000, 2026))

ITEMS = ["集計世帯数", "世帯数分布(抽出率調整)", "世帯人員", "有業人員", "世帯主の年齢",
         "実収入", "可処分所得", "消費支出", "こづかい(使途不明)", "交際費", "贈与金"]
AGE_BINS = {"age_u29": r"～29歳", "age_30s": r"30～39", "age_40s": r"40～49", "age_50s": r"50～59", "age_60s": r"60～69"}


def raw_file(table, y):
    for ext in (".xlsx", ".xls"):
        p = RAW / f"kakei_{table}_{y}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError((table, y))


def find_col(heads, pat):
    ks = [k for k, h in heads.items() if re.search(pat, h)]
    assert len(ks) == 1, (pat, ks, heads)
    return ks[0]


def main():
    recs = []
    for y in YEARS:
        # 第3-2表 勤労者世帯：平均と10歳きざみ
        rows, heads = kakei.read_book(raw_file("3-2", y), r"全国・勤労|^勤労$")
        assert heads[1].endswith("平均") or "平均" in heads[1], heads[1]
        cols = {"workers_all": 1}
        for g, pat in AGE_BINS.items():
            cols[g] = find_col(heads, pat)
        for g, k in cols.items():
            for it in ITEMS:
                recs.append((y, g, it, kakei.get(rows, it, k)))
        # 第3-2表 二人以上の世帯（全体）の平均
        rows, heads = kakei.read_book(raw_file("3-2", y), r"全国・全世帯|全国・二人|^二人$")
        assert "平均" in heads[1], heads[1]
        for it in ITEMS:
            if it in ("実収入", "可処分所得"):
                continue  # 二人以上の世帯（全体）の表には収入の行がない
            recs.append((y, "twoplus_all", it, kakei.get(rows, it, 1)))
        # 第3-11表 勤労者世帯：夫婦共働き・夫のみ有業
        rows, heads = kakei.read_book(raw_file("3-11", y), r"全国・勤労|^勤労$|^3-11勤労")
        assert heads[1].startswith("夫婦共働き世帯"), heads[1]
        assert heads[28].startswith("夫のみ有業"), heads[28]
        for g, k in (("dual", 1), ("husband_only", 28)):
            for it in ITEMS:
                recs.append((y, g, it, kakei.get(rows, it, k)))
    df = pd.DataFrame(recs, columns=["year", "group", "item", "value"])
    df.to_csv(OUT / "kakei_pocket_long.csv", index=False, float_format="%.2f")

    c = pd.read_csv(RAW / "cpi_2025base_middle_class_monthly.csv", encoding="cp932", header=None, dtype=str)
    col = [i for i, x in enumerate(c.iloc[0]) if x == "持家の帰属家賃を除く総合"][0]
    body = c[c[0].str.fullmatch(r"\d{6}", na=False)].copy()
    body["year"] = body[0].str[:4].astype(int)
    body["cpi"] = body[col].astype(float)
    a = body.groupby("year", sort=True).agg(cpi=("cpi", "mean"), n=("cpi", "size")).reset_index()
    a = a[a["year"].isin(YEARS)]
    assert (a["n"] == 12).all()
    a["deflator_to_2025"] = a.loc[a["year"] == 2025, "cpi"].iloc[0] / a["cpi"]
    a.to_csv(OUT / "cpi_annual.csv", index=False, float_format="%.6f")
    print("rows", len(df), "missing", int(df["value"].isna().sum()))


if __name__ == "__main__":
    main()
