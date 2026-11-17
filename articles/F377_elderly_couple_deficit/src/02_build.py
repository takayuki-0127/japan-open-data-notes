"""02_build.py : data/raw の家計調査 第3-12表（2000〜2025年）と消費者物価指数から、分析用の CSV を作る（オフライン）。
出力：data/kakei_elderly_long.csv（年・世帯の種類・項目・円）、data/cpi_annual.csv、data/identity_check.csv
"""
import pathlib

import numpy as np
import pandas as pd

import kakei

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
YEARS = list(range(2000, 2026))

# 第3-12表の列の番号（表の1行目の番号。2000〜2025年で同じ並び）
GROUPS = {
    "couple_6560": 31,   # 夫65歳以上・妻60歳以上の夫婦一組の世帯（無職世帯）＝高齢夫婦無職世帯
    "couple_65": 33,     # 65歳以上の夫婦一組の世帯（無職世帯）
    "head65_nojob": 11,  # 世帯主が65歳以上の無職世帯（65歳以上の者がいる世帯）
    "elder_nojob": 26,   # 男65歳以上・女60歳以上の者のみからなる世帯（無職世帯）
    "elder_inc_lt250": 27,
    "elder_inc_250_349": 28,
    "elder_inc_ge350": 29,
}
# 列の見出しに含まれるはずの言葉（読み違えの確かめ）
HEAD_CHECK = {31: "無職", 33: "無職", 11: "無職", 26: "無職", 27: "250万円未満", 28: "250～349", 29: "350万円以上"}

ITEMS = ["集計世帯数", "世帯人員", "世帯主の年齢", "有業人員", "持家率",
         "実収入", "経常収入", "勤め先収入", "事業・内職収入", "他の経常収入", "財産収入", "社会保障給付",
         "公的年金給付", "他の社会保障給付", "仕送り金", "特別収入",
         "実収入以外の受取(繰入金を除く)", "預貯金引出", "保険金", "有価証券売却", "繰入金",
         "実支出", "消費支出", "非消費支出", "直接税", "社会保険料",
         "実支出以外の支払(繰越金を除く)", "預貯金", "保険料", "有価証券購入", "繰越金",
         "可処分所得", "黒字"]


def raw_file(y):
    for ext in (".xlsx", ".xls"):
        p = RAW / f"kakei_3-12_{y}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(y)


def main():
    recs = []
    for y in YEARS:
        rows, heads = kakei.read_book(raw_file(y), ".")
        for k, word in HEAD_CHECK.items():
            assert word in heads[k], (y, k, heads[k])
        for g, k in GROUPS.items():
            for it in ITEMS:
                v = kakei.get(rows, it, k)
                recs.append((y, g, it, v))
    df = pd.DataFrame(recs, columns=["year", "group", "item", "value"])
    df.to_csv(OUT / "kakei_elderly_long.csv", index=False, float_format="%.2f")

    # 収支の恒等式：実支出 − 実収入 ＝ (受取 − 支払) ＋ (繰入金 − 繰越金)
    w = df.pivot_table(index=["group", "year"], columns="item", values="value").reset_index()
    w["deficit"] = w["実支出"] - w["実収入"]
    w["fill_total"] = (w["実収入以外の受取(繰入金を除く)"] - w["実支出以外の支払(繰越金を除く)"]
                       + w["繰入金"] - w["繰越金"])
    w["gap"] = w["deficit"] - w["fill_total"]
    w["gap_kurodi"] = w["deficit"] + w["黒字"]
    w["gap_dispo"] = (w["消費支出"] - w["可処分所得"]) - w["deficit"]
    w[["group", "year", "deficit", "fill_total", "gap", "gap_kurodi", "gap_dispo"]].sort_values(
        ["group", "year"]).to_csv(OUT / "identity_check.csv", index=False, float_format="%.2f")

    # 消費者物価指数（持家の帰属家賃を除く総合、2025年基準）の年平均
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
    print("rows", len(df), "max |gap|", float(np.abs(w["gap"]).max()), float(np.abs(w["gap_kurodi"]).max()))


if __name__ == "__main__":
    main()
