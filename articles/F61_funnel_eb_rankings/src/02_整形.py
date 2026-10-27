"""02 整形：分析用の2つの表を作る。

screening.csv … 市区町村×年度（2021〜2024）の大腸がん・肺がん検診の対象者数 n と受診者数 y、規模区分
smr.csv       … 市区町村の死亡数 O と期待死亡数 E（全死因・心疾患・脳血管疾患、男女計）、規模区分
"""
import numpy as np
import pandas as pd
from common import RAW, DATA

SIZE_BINS = [0, 500, 2000, 10000, np.inf]
SIZE_LABELS = ["500人未満", "500〜2,000人", "2,000〜1万人", "1万人以上"]


def main():
    s = pd.read_csv(RAW / "f19_screening_long.csv", dtype={"code": str})
    s = s[["code", "name", "pref", "year", "n_colon", "y_colon", "n_lung", "y_lung"]].copy()
    for k in ("colon", "lung"):
        bad = s[f"n_{k}"].isna() | s[f"y_{k}"].isna() | (s[f"y_{k}"] > s[f"n_{k}"])
        s.loc[bad, [f"n_{k}", f"y_{k}"]] = np.nan
    # 4年度とも大腸がんの値がそろう団体だけを使う（順位の入れ替わりを比べるため）
    ok = s.groupby("code")["n_colon"].apply(lambda v: v.notna().all())
    s = s[s.code.isin(ok[ok].index)].copy()
    # 規模区分は4年度の対象者数の平均で固定する
    nbar = s.groupby("code")["n_colon"].mean().rename("n_mean")
    s = s.merge(nbar, on="code")
    s["size"] = pd.cut(s.n_mean, SIZE_BINS, labels=SIZE_LABELS, right=False)
    s.to_csv(DATA / "screening.csv", index=False)
    print("screening:", s.code.nunique(), "団体 ×", s.year.nunique(), "年度")
    print(s.drop_duplicates("code")["size"].value_counts().sort_index())

    m = pd.read_csv(RAW / "f27_smr_2018_22.csv", dtype={"code": str})
    keep = ["code", "name", "pref"]
    for k in ("all", "heart", "stroke"):
        keep += [f"O_{k}", f"E_{k}"]
    m = m[keep].dropna(subset=["O_all", "E_all"]).copy()
    m["size"] = pd.cut(m.E_all, [0, 100, 300, 1000, np.inf],
                       labels=["100人未満", "100〜300人", "300〜1,000人", "1,000人以上"], right=False)
    m.to_csv(DATA / "smr.csv", index=False)
    print("smr:", len(m), "地域")
    print(m["size"].value_counts().sort_index())


if __name__ == "__main__":
    main()
