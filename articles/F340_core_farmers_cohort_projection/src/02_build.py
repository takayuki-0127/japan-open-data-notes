"""data/raw の Excel から、年齢別基幹的農業従事者の縦長の表 data/core_workers_by_age.csv を作る（オフライン）。"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AGES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
        "65-69", "70-74", "75-79", "80-84", "85+"]
REGIONS = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉",
         "東京", "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重",
         "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島",
         "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]


def num(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip().replace(",", "")
    if s in ("-", "－"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return np.nan


def rows_from_sheet(d, year, basis, src, c0):
    """c0：男女計の「計」の列。男女計・男・女がそれぞれ16列（計＋15階級）で並ぶ。"""
    out = []
    names = d[0].astype(str).str.replace(" ", "").str.replace("　", "").str.strip()
    i_pref = int(np.where(names.str.contains("都道府県"))[0][-1])
    for i in range(len(d)):
        nm = names.iloc[i]
        if nm == "全国":
            level = "全国"
        elif nm in REGIONS and i < i_pref:
            level = "地域"
        elif nm in PREFS and i > i_pref:
            level = "都道府県"
        else:
            continue
        for k, sex in enumerate(["計", "男", "女"]):
            base = c0 + 16 * k
            total = num(d.iat[i, base])
            for j, a in enumerate(AGES):
                out.append(dict(year=year, basis=basis, source=src, level=level, name=nm, sex=sex, age=a,
                                n=num(d.iat[i, base + 1 + j]), total_in_table=total))
    return out


def main():
    rows = []
    x = pd.ExcelFile(RAW / "census_longterm_core_workers_by_age_1960_2020.xls")
    for sh, yr, basis in [("17年（販）", 2005, "販売農家"), ("22年（販）", 2010, "販売農家"), ("27年（販）", 2015, "販売農家"),
                          ("27年（個人）", 2015, "個人経営体"), ("令和２年（個人）", 2020, "個人経営体")]:
        rows += rows_from_sheet(x.parse(sh, header=None), yr, basis, "累年統計", 3)
    d = pd.read_excel(RAW / "census2025_core_workers_by_age.xlsx", header=None)
    rows += rows_from_sheet(d, 2025, "個人経営体", "2025年センサス", 3)
    rows += rows_from_sheet(d, 2020, "個人経営体", "2025年センサス（2020年の再掲）", 51)
    out = pd.DataFrame(rows)
    out["age_order"] = out["age"].map({a: k for k, a in enumerate(AGES)})
    out = out.sort_values(["source", "year", "basis", "level", "name", "sex", "age_order"]).reset_index(drop=True)
    out.to_csv(ROOT / "data" / "core_workers_by_age.csv", index=False)
    # 照合：階級の合計と表の「計」
    g = out.groupby(["source", "year", "basis", "level", "name", "sex"]).agg(sum_n=("n", "sum"), total=("total_in_table", "first")).reset_index()
    g["diff"] = g["sum_n"] - g["total"]
    g.to_csv(ROOT / "data" / "check_totals.csv", index=False)
    print(out.groupby(["source", "year", "basis", "level"]).size())
    print("max abs diff (sum of ages - table total):", g["diff"].abs().max())


if __name__ == "__main__":
    main()
