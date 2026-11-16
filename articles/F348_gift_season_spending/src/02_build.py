"""data/raw から分析用の表を作る（オフライン）。
- data/gift_monthly.csv：2000年1月〜の月ごとの交際費の内訳（二人以上の世帯、1世帯あたり、円）
- data/gift_annual_long.csv：1963〜2007年の年の交際費の内訳（二人以上の非農林漁家世帯、1世帯あたり年平均1か月間、円）
- data/price_annual.csv：消費支出の名目と実質の増減率から出した物価の目安（2000年＝100）
"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MON = RAW / "kakei_two_plus_usage_monthly_2000_2026.xlsx"
LONG = RAW / "kakei_nonfarm_usage_1963_2007.xls"
GIFT_GOODS = ["食料", "家具・家事用品", "被服及び履物", "教養娯楽", "他の物品サービス"]
COLS = {"食料": "gift_food", "家具・家事用品": "gift_furniture", "被服及び履物": "gift_clothing", "教養娯楽": "gift_recreation",
        "他の物品サービス": "gift_other_goods", "贈与金": "money_gifts", "他の交際費": "other_social"}


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def label(d, i):
    return "".join(str(v).strip() for v in d.iloc[i, 7:15].tolist() if str(v) != "nan" and not str(v).strip().replace(".", "").isdigit())


def find_rows(d):
    """交際費の行と、その下の内訳の行、消費支出・世帯人員の行を探す。"""
    rows = {}
    for i in range(12, len(d)):
        lab = label(d, i)
        if lab == "消費支出" and "consumption" not in rows:
            rows["consumption"] = i
        if lab == "世帯人員(人)" and "persons" not in rows:
            rows["persons"] = i
        if lab == "交際費":
            rows["social_total"] = i
            for j in range(i + 1, i + 8):
                lj = label(d, j)
                if lj in COLS:
                    rows[COLS[lj]] = j
            break
    return rows


def monthly():
    d = pd.read_excel(MON, sheet_name="支出金額（月）", header=None)
    rows = find_rows(d)
    year = None
    out = []
    for c in range(15, d.shape[1]):
        y = str(d.iat[9, c])
        if y.endswith("年"):
            year = int(y.replace("年", ""))
        m = str(d.iat[11, c]).replace("　", "").replace("月", "").strip()
        if not m.isdigit():
            continue
        rec = dict(year=year, month=int(m))
        for k, i in rows.items():
            rec[k] = num(d.iat[i, c])
        out.append(rec)
    df = pd.DataFrame(out)
    df["gift_goods"] = df[[COLS[g] for g in GIFT_GOODS]].sum(axis=1)
    return df


def long_annual():
    d = pd.read_excel(LONG, header=None)
    # 列の見出し（7〜11行目）から交際費の位置を探す
    head = {c: " ".join(str(d.iat[r, c]).replace("\n", "") for r in range(7, 12) if str(d.iat[r, c]) != "nan") for c in range(d.shape[1])}
    c0 = [c for c, s in head.items() if s.strip() == "交際費"][0]
    names = {c0: "social_total", c0 + 1: "gift_food", c0 + 2: "gift_furniture", c0 + 3: "gift_clothing", c0 + 4: "gift_recreation",
             c0 + 5: "gift_other_goods", c0 + 6: "money_gifts", c0 + 7: "other_social"}
    assert head[c0 + 6].strip() == "贈与金" and head[c0 + 7].strip() == "他の交際費", head
    c_cons = [c for c, s in head.items() if s.strip() == "消費支出"][0]
    c_pers = [c for c, s in head.items() if s.strip() == "世帯人員"][0]
    out = []
    seen = set()
    for i in range(14, len(d)):
        y = num(d.iat[i, 1])
        if np.isnan(y) or y < 1900:
            continue
        if y in seen:  # 2つ目の区分（人口5万以上の市）に入ったら止める。使うのは「全国」だけ
            break
        seen.add(y)
        rec = dict(year=int(y), consumption=num(d.iat[i, c_cons]), persons=num(d.iat[i, c_pers]))
        for c, k in names.items():
            rec[k] = num(d.iat[i, c])
        out.append(rec)
    df = pd.DataFrame(out)
    df["gift_goods"] = df[["gift_food", "gift_furniture", "gift_clothing", "gift_recreation", "gift_other_goods"]].sum(axis=1)
    return df


def price():
    res = {}
    for sh, key in [("名目増減率（年）", "nom"), ("実質増減率（年）", "real")]:
        d = pd.read_excel(MON, sheet_name=sh, header=None)
        i = [i for i in range(12, len(d)) if label(d, i) == "消費支出"][0]
        for c in range(15, d.shape[1]):
            y = str(d.iat[9, c])
            if y.endswith("年"):
                res.setdefault(int(y.replace("年", "")), {})[key] = num(d.iat[i, c])
    p = pd.DataFrame([dict(year=y, **v) for y, v in sorted(res.items())])
    p["defl_ratio"] = (1 + p["nom"] / 100) / (1 + p["real"] / 100)
    idx = [100.0]
    for r in p["defl_ratio"]:
        idx.append(idx[-1] * r)
    p = pd.concat([pd.DataFrame([dict(year=p["year"].min() - 1, nom=np.nan, real=np.nan, defl_ratio=np.nan)]), p], ignore_index=True)
    p["price_index_2000"] = np.round(idx, 4)
    return p


def main():
    m = monthly()
    m.to_csv(ROOT / "data" / "gift_monthly.csv", index=False)
    l = long_annual()
    l.to_csv(ROOT / "data" / "gift_annual_long.csv", index=False)
    p = price()
    p.to_csv(ROOT / "data" / "price_annual.csv", index=False)
    print(m.shape, m["year"].min(), m["year"].max(), m.tail(1)[["year", "month"]].values.tolist(), l.shape, l["year"].min(), l["year"].max(), p.shape)


if __name__ == "__main__":
    main()
