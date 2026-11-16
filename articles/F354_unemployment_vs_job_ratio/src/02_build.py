"""data/raw から年の表 data/annual.csv を作る（オフライン）。人数の単位は万人、件数は月平均（人・件）。"""
import pathlib, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def main():
    l = pd.read_excel(RAW / "lfs_longterm_table2_annual_1953_2025.xlsx", sheet_name="長期02", header=None)
    assert "完全失業者" in str(l.iat[7, 5]) and "完全失業率" in str(l.iat[5, 12]) and "就業者" in str(l.iat[7, 4])
    lf = []
    for i in range(10, len(l)):
        y = num(l.iat[i, 1])
        if np.isnan(y):
            continue
        lf.append(dict(year=int(y), labour_force=num(l.iat[i, 3]), employed=num(l.iat[i, 4]), unemployed=num(l.iat[i, 5]), u_rate=num(l.iat[i, 12])))
    # 1973年は沖縄県を含まない行と含む行の2つがある。後の年とつながる「含む」行（後ろの行）を使う
    lf = pd.DataFrame(lf).drop_duplicates("year", keep="last")
    s = pd.read_excel(RAW / "shokugyo_shokai_longterm_table1_1963_2025.xlsx", header=None)
    hdr = [str(v) for v in s.iloc[2].tolist()]
    real = {"新規求人倍率": "new_ratio", "有効求人倍率": "ratio", "新規求人数": "new_openings", "新規求職申込件数": "new_applications",
            "有効求人数": "openings", "有効求職者数": "applicants", "就職件数": "placements"}
    cols = {}
    for c, h in enumerate(hdr):
        if h in real and real[h] not in cols and str(s.iat[1, c]).strip() == "実数":
            cols[real[h]] = c
    hw = []
    for i in range(4, len(s)):
        y = str(s.iat[i, 0]).strip()
        if y.endswith("年度"):
            break  # 年平均の区切りが終わったら止める（後ろは年度・月の表）
        if y.endswith("年") and y[:4].isdigit():
            hw.append(dict(year=int(y[:4]), **{k: num(s.iat[i, c]) for k, c in cols.items()}))
    hw = pd.DataFrame(hw)
    d = lf.merge(hw, on="year", how="inner").sort_values("year")
    d.to_csv(ROOT / "data" / "annual.csv", index=False)
    print(d.shape, d.year.min(), d.year.max(), cols); print(d.iloc[[0, 30, -1]].to_string())


if __name__ == "__main__":
    main()
