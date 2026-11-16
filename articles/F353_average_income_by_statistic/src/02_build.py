"""data/raw から CSV を作る（オフライン）。
- data/nta_brackets_2025.csv：令和7年分、給与所得者区分×性別×給与階級（人数・給与総額・平均給与）。1年勤務、1年未満、乙欄適用者を除く1年勤務
- data/nta_brackets_years.csv：累年比較（2016〜2025年分、1年勤務、性別×給与階級）
- data/maikin_2025.csv：毎月勤労 令和7年平均の月額（規模×就業形態×項目）と前年比"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
NTA = RAW / "nta_minkan_2025_table03_income_brackets.xlsx"
MK = RAW / "mhlw_maikin_2025_annual_table01_wages.xlsx"


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def upper(b):
    """給与階級の上限（万円）。「2,500万円超」は上限なし。"""
    s = str(b).replace(",", "")
    m = re.match(r"(\d+)万円以下", s)
    return float(m.group(1)) if m else (np.inf if "超" in s else np.nan)


def nta_2025():
    rows = []
    for sh in ["03_01", "03_03"]:
        d = pd.read_excel(NTA, sheet_name=sh, header=None)
        for i in range(7, len(d)):
            b, kind, sex = str(d.iat[i, 0]).strip(), str(d.iat[i, 1]).strip(), str(d.iat[i, 2]).strip()
            if sex not in ("男", "女", "計"):
                continue
            k = ("1年勤務" if "１年を通じて" in kind else "1年未満") + ("（乙欄除く）" if "乙欄" in kind else "")
            rows.append(dict(kind=k, sex=sex, bracket=b, upper_man=upper(b), persons=num(d.iat[i, 5]), total_million=num(d.iat[i, 10]), mean_thousand=num(d.iat[i, 11]),
                             bonus_mean_thousand=num(d.iat[i, 9])))
    return pd.DataFrame(rows)


def nta_years():
    d = pd.read_excel(NTA, sheet_name="03_02", header=None)
    rows = []
    for i in range(7, len(d)):
        sex = str(d.iat[i, 2]).strip()
        y = str(d.iat[i, 3]).strip()
        if sex not in ("男", "女", "計") or not y.endswith("年"):
            continue
        b = str(d.iat[i, 0]).strip()
        rows.append(dict(year=int(y[:4]), sex=sex, bracket=b, upper_man=upper(b), persons_thousand=num(d.iat[i, 5]), total_million=num(d.iat[i, 7]),
                         mean_thousand=num(d.iat[i, 10])))
    return pd.DataFrame(rows)


def maikin():
    d = pd.read_excel(MK, header=None)
    cols = {"cash_total": 2, "cash_total_yoy": 3, "regular": 4, "regular_yoy": 5, "scheduled": 6, "scheduled_yoy": 7, "overtime": 8, "overtime_yoy": 9, "special": 10, "special_yoy": 11}
    rows = []
    size = "5人以上"; form = None
    for i in range(len(d)):
        c0, c1 = str(d.iat[i, 0]).strip(), str(d.iat[i, 1]).strip()
        if "30人以上" in c0:
            size = "30人以上"
        for f in ["就業形態計", "一般労働者", "パートタイム労働者"]:
            if f in c0 or f in c1:
                form = f
        label = re.sub(r"\s", "", c1 if c1 != "nan" else c0)
        if ("調査産業計" in re.sub(r"\s", "", c0 + c1)) and not np.isnan(num(d.iat[i, 2])):
            rows.append(dict(size=size, form=form, **{k: num(d.iat[i, c]) for k, c in cols.items()}))
        elif size == "30人以上" and form and not np.isnan(num(d.iat[i, 2])):
            rows.append(dict(size=size, form=form, **{k: num(d.iat[i, c]) for k, c in cols.items()}))
    return pd.DataFrame(rows).drop_duplicates(["size", "form"])


def main():
    a = nta_2025(); a.to_csv(ROOT / "data" / "nta_brackets_2025.csv", index=False)
    b = nta_years(); b.to_csv(ROOT / "data" / "nta_brackets_years.csv", index=False)
    m = maikin(); m.to_csv(ROOT / "data" / "maikin_2025.csv", index=False)
    print(a.groupby(["kind", "sex"]).size().to_dict()); print(b.groupby("sex").year.agg(["min", "max", "count"]).to_dict()); print(m.to_string())


if __name__ == "__main__":
    main()
