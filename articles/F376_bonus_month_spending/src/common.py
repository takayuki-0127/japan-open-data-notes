"""共通：行の対応表と、ボーナスの月の上乗せの計算。"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
BONUS = (6, 7, 12)
YEARS = list(range(2000, 2026))

V = {  # items.csv の label（完全一致）→ 名前
    "実収入": "実収入", "臨時収入・賞与": "世帯主の臨時収入・賞与", "可処分所得": "可処分所得", "非消費支出": "非消費支出",
    "消費支出": "消費支出", "黒字": "黒字",
    "預貯金純増": "預貯金純増", "保険純増": "保険純増", "有価証券純購入": "有価証券純購入",
    "土地家屋借金純減": "土地家屋借金純減", "他の借金純減": "他の借金純減", "クレジット購入借入金純減": "クレジット購入借入金純減",
    "財産純増": "財産純増", "その他の純増": "その他の純増", "繰越純増": "繰越純増",
    # 10大費目
    "1|食料": "食料", "2|住居": "住居", "3|光熱・水道": "光熱・水道", "4|家具・家事用品": "家具・家事用品",
    "5|被服及び履物": "被服及び履物", "6|保健医療": "保健医療", "7|交通・通信": "交通・通信", "8|教育": "教育",
    "9|教養娯楽": "教養娯楽", "10|その他の消費支出": "その他の消費支出",
    # 主な中分類・小分類
    "1.12|外食": "外食", "1.11|酒類": "酒類", "1.8|菓子類": "菓子類", "5.2|洋服": "洋服", "4.1|家庭用耐久財": "家庭用耐久財",
    "7.1|交通": "交通", "7.2.1|自動車等購入": "自動車等購入", "7.3|通信": "通信", "8.1|授業料等": "授業料等",
    "9.1|教養娯楽用耐久財": "教養娯楽用耐久財", "9.2|教養娯楽用品": "教養娯楽用品", "9.4|教養娯楽サービス": "教養娯楽サービス",
    "9.4.1|宿泊料": "宿泊料", "9.4.2|パック旅行費": "パック旅行費",
    "10.2|こづかい(使途不明)": "こづかい(使途不明)", "10.3|交際費": "交際費", "10.3.6|贈与金": "贈与金",
    "10.3.1|食料": "交際費のうち食料", "10.4|仕送り金": "仕送り金",
}
CATS10 = ["食料", "住居", "光熱・水道", "家具・家事用品", "被服及び履物", "保健医療", "交通・通信", "教育", "教養娯楽", "その他の消費支出"]
SURPLUS_PARTS = ["預貯金純増", "保険純増", "有価証券純購入", "土地家屋借金純減", "他の借金純減", "クレジット購入借入金純減",
                 "財産純増", "その他の純増", "繰越純増"]


def load_wide():
    """year, month を行、名前を列にした表。"""
    d = pd.read_csv(ROOT / "data" / "monthly_long.csv", dtype={"key": str})
    items = pd.read_csv(ROOT / "data" / "items.csv", dtype={"key": str})
    items = items[items.label.isin(V)]
    assert items.label.is_unique and len(items) == len(V), "行の対応が一意でない"
    k2n = {k: V[l] for k, l in zip(items.key, items.label)}
    d = d[d.key.isin(k2n)].copy()
    d["name"] = d.key.map(k2n)
    w = d.pivot_table(index=["year", "month"], columns="name", values="value", aggfunc="first").sort_index()
    return w, dict(zip(items.key, items.label))


def excess(w, cols, years=YEARS, bonus=BONUS, base="nine"):
    """年ごとの上乗せ E_y(X)。base='nine'：ボーナスの月以外の9か月の平均。base='near'：近い月の平均。"""
    out = []
    for y in years:
        g = w.loc[y]
        row = {"year": y}
        for c in cols:
            s = g[c]
            tot = 0.0
            for m in bonus:
                if base == "nine":
                    b = s[[k for k in range(1, 13) if k not in BONUS]].mean()
                else:
                    b = s[[4, 5, 8, 9]].mean() if m in (6, 7) else s[[10, 11]].mean()
                tot += s[m] - b
            row[c] = tot
        out.append(row)
    return pd.DataFrame(out).set_index("year")


def ols(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    X = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n = len(x)
    s2 = resid @ resid / (n - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    return float(beta[0]), float(beta[1]), float(np.sqrt(cov[1, 1]))


def theil_sen(x, y):
    from scipy.stats import theilslopes
    r = theilslopes(np.asarray(y, float), np.asarray(x, float))
    return float(r.slope)
