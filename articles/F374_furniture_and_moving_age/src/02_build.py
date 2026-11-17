"""02_build.py : 家計調査（家具・家事用品）と住民基本台帳人口移動報告から分析用の表を作る。
- data/fies_age.csv   : 年、世帯主の年齢階級、品目、支出金額（円、1世帯当たり年間）
- data/fies_month.csv : 年、月、品目、支出金額（円、1世帯当たり）
- data/fies_2025_age5.csv : 2025年の年齢区分（再掲の5歳ずらしを含む）、品目、支出金額、世帯数分布
- data/move_rate_age.csv : 2024年 年齢（5歳階級）別 都道府県内移動率・他都道府県への転出率（%、全国）
- data/moves_month.csv : 年、月、移動者数（日本人、都道府県内＋都道府県間）
"""
import pathlib
import re
import unicodedata

import pandas as pd
import xlrd.formatting as xf

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]
OLD_AGE_KEYS = ["～29", "30～39", "40～49", "50～59", "60～69", "70歳～"]
CODES = {"451~542": "家具・家事用品", "480~489": "一般家具", "491~499": "室内装備・装飾品", "500~509": "寝具類",
         "482": "テーブル・ソファー", "496": "カーテン", "500": "ベッド"}
NAMES25 = ["家具・家事用品", "一般家具", "室内装備・装飾品", "寝具類", "テーブル・ソファー", "カーテン", "ベッド"]

_orig = xf.handle_format


def handle_format(self, data, rectype=xf.XL_FORMAT):
    """一部の年の .xls は書式の記録に壊れた文字があり xlrd が止まるため、数値の表示形式だけ読み飛ばす。"""
    try:
        return _orig(self, data, rectype)
    except UnicodeDecodeError:
        return None


xf.handle_format = handle_format


def n(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))


def num(x):
    v = pd.to_numeric(x, errors="coerce")
    return None if pd.isna(v) else float(v)


def fies_old(path):
    v = pd.read_excel(path, header=None)
    cols = {}
    for c in range(10, v.shape[1]):
        if n(v.iat[14, c]) != "金額":
            continue
        head = "".join(n(v.iat[r, c]) for r in range(5, 14))
        m = re.match(r"^(\d{3}(?:~\d{3})?)(?![\d･~])", head)
        if m and m.group(1) in CODES:
            cols[CODES[m.group(1)]] = c
    assert set(cols) == set(CODES.values()), (path.name, sorted(cols))
    lab = [n("".join(n(x) for x in v.iloc[r, 0:10])) for r in range(v.shape[0])]
    freq_start = next(i for i, l in enumerate(lab) if "購入頻度" in l)
    # 表の左上の見出しにも「世帯主の年齢階級」があるので、購入頻度の行より後で探す
    age_start = next(i for i, l in enumerate(lab) if i > freq_start and l.startswith("世帯主の年齢階級"))
    rows = {"平均": next(i for i in range(age_start, len(lab)) if lab[i].startswith("二人以上の世帯平均"))}
    for a, k in zip(AGES, OLD_AGE_KEYS):
        rows[a] = next(i for i in range(age_start, len(lab)) if lab[i].startswith(n(k)))
    # 月の行は英語の月名で見分ける（年によって「2月」と「2」の書き方が違うため）
    en = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sep", "Oct", "Nov", "Dec"]
    months = []
    for r in range(freq_start, age_start):
        m = re.search(r"(Jan|Feb|Mar|Apr|May|June|July|Aug|Sep|Oct|Nov|Dec)\.?$", lab[r])
        if m and len(months) < 12:
            months.append((en.index(m.group(1)) + 1, r))
    assert [m for m, _ in months] == list(range(1, 13)), (path.name, months)
    return v, cols, rows, months


def fies_2025():
    v = pd.read_excel(RAW / "fies_2025_age_4_6.xlsx", sheet_name="二人", header=None)
    head = [n(v.iat[8, c]) for c in range(v.shape[1])]
    cols = {}
    for c, h in enumerate(head):
        if h.endswith("・支出金額"):
            a = h[: -len("・支出金額")].replace("(再掲)", "再掲")
            cols[a] = c
    names = [n(x) for x in v[11]]
    out = []
    for item in NAMES25 + ["世帯数分布(抽出率調整)"]:
        r = names.index(n(item))
        for a, c in cols.items():
            out.append({"age": a, "item": item.replace("(抽出率調整)", ""), "value": num(v.iat[r, c])})
    return pd.DataFrame(out)


def moves_rate(path, label):
    v = pd.read_excel(path, header=None)
    r = next(i for i in range(v.shape[0]) if n(v.iat[i, 6]) == "全国" and n(v.iat[i, 2]) == "移動者")
    out = []
    for c in range(8, v.shape[1]):
        if n(v.iat[3, c]) != "総数":
            continue
        a = n(v.iat[4, c])
        if not a or a == "総数":
            continue
        out.append({"age5": a, label: num(v.iat[r, c])})
    return pd.DataFrame(out)


def moves_month():
    v = pd.read_excel(RAW / "moves_long_t1.xlsx", sheet_name="総数", header=None)
    years = {c: int(num(v.iat[6, c])) for c in range(2, v.shape[1]) if num(v.iat[6, c])}
    start = next(i for i in range(v.shape[0]) if n(v.iat[i, 0]) == "移動者数")
    out = []
    for r in range(start + 1, start + 14):
        m = re.match(r"(\d{1,2})月", n(v.iat[r, 0]))
        if not m:
            continue
        for c, y in years.items():
            x = num(v.iat[r, c])
            if x is not None:
                out.append({"year": y, "month": int(m.group(1)), "movers": x})
    d = pd.DataFrame(out)
    assert d.groupby("year").size().loc[2013:2024].eq(12).all()
    return d


def main():
    age, mon = [], []
    for y in range(2013, 2025):
        v, cols, rows, months = fies_old(RAW / f"fies_{y}_furn.xls")
        for item, c in cols.items():
            for a, r in rows.items():
                age.append({"year": y, "age": a, "item": item, "amount": num(v.iat[r, c])})
            for m, r in months:
                mon.append({"year": y, "month": m, "item": item, "amount": num(v.iat[r, c])})
    f25 = fies_2025()
    key = {"平均": "平均", "29歳以下": "29歳以下", "30~39歳": "30〜39歳", "40~49歳": "40〜49歳", "50~59歳": "50〜59歳",
           "60~69歳": "60〜69歳", "70歳以上": "70歳以上"}
    for _, r in f25[f25.age.isin(key) & (f25.item != "世帯数分布")].iterrows():
        age.append({"year": 2025, "age": key[r["age"]], "item": r["item"], "amount": r["value"]})
    a = pd.DataFrame(age)
    a.to_csv(BASE / "data" / "fies_age.csv", index=False)
    pd.DataFrame(mon).to_csv(BASE / "data" / "fies_month.csv", index=False)
    f25.to_csv(BASE / "data" / "fies_2025_age5.csv", index=False)
    mr = moves_rate(RAW / "moves_rate_within_pref_2024.xlsx", "within_pref").merge(
        moves_rate(RAW / "moves_rate_out_pref_2024.xlsx", "out_pref"), on="age5")
    mr.to_csv(BASE / "data" / "move_rate_age.csv", index=False)
    mm = moves_month()
    mm.to_csv(BASE / "data" / "moves_month.csv", index=False)
    print(a[a.year == 2024].pivot_table(index="item", columns="age", values="amount"))
    print(mr)
    print(sorted(f25.age.unique()))


if __name__ == "__main__":
    main()
