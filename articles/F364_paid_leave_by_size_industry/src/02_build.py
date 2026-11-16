"""02_build.py : 就労条件総合調査の時系列表（付与日数・取得日数・取得率）から、2009〜2025年調査の
規模・産業別の値を取り出して data/paid_leave.csv にする（オフライン）。"""
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
FILES = {"granted": "ts11_granted_days", "taken": "ts12_taken_days", "rate": "ts13_take_rate"}
# 2009〜2019年調査：行31〜52、ラベル12列目、値15〜25列目（平成21〜31年）
# 2020〜2025年調査：行60〜81、ラベル2・3列目、値6〜11列目（令和2〜7年）
NAMES = ["調査産業計", "1000人以上", "100〜999人", "300〜999人", "100〜299人", "30〜99人", "鉱業", "建設業", "製造業",
         "電気・ガス", "情報通信業", "運輸業", "卸売・小売業", "金融・保険業", "不動産業", "学術研究・専門技術", "宿泊・飲食",
         "生活関連・娯楽", "教育・学習支援", "医療・福祉", "複合サービス", "サービス業（他に分類されないもの）"]
KEYS = ["調査産業計", "1,000人以上", "100~999人", "300~999人", "100~299人", "30~99人", "鉱業", "建設", "製造", "電気・ガス",
        "情報", "運輸", "卸売", "金融", "不動産", "学術研究", "宿泊", "生活関連", "教育", "医療", "複合サービス", "サービス"]


def n(s):
    return "" if pd.isna(s) else re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def num(x):
    s = n(x)
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else float("nan")


def parse(path, var):
    v = pd.read_excel(path, header=None, engine="xlrd")
    # 年の見出しを確かめる
    assert [n(x).rstrip(")").rstrip("3") if n(x).endswith("3)") else n(x) for x in v.iloc[26, 15:26]] == [str(k) for k in range(21, 32)], list(v.iloc[26, 15:26])
    assert [n(x) for x in v.iloc[56, 7:12]] == ["3", "4", "5", "6", "7"] and n(v.iat[58, 6]) == "2年"
    rows = []
    for k, (nm, key) in enumerate(zip(NAMES, KEYS)):
        i = 31 + k
        assert key in n(v.iat[i, 12]), (path.name, i, n(v.iat[i, 12]), key)
        for j, y in zip(range(15, 26), range(2009, 2020)):
            rows.append({"var": var, "group": nm, "year": y, "value": num(v.iat[i, j])})
        i = 60 + k
        lab = n(v.iat[i, 2]) or n(v.iat[i, 3])
        assert key in lab, (path.name, i, lab, key)
        for j, y in zip(range(6, 12), range(2020, 2026)):
            rows.append({"var": var, "group": nm, "year": y, "value": num(v.iat[i, j])})
    return rows


if __name__ == "__main__":
    rows = []
    for var, stem in FILES.items():
        rows += parse(RAW / (stem + ".xls"), var)
    df = pd.DataFrame(rows)
    w = df.pivot_table(index=["group", "year"], columns="var", values="value").reset_index()
    w["kind"] = w.group.map(lambda g: "total" if g == "調査産業計" else ("size" if "人" in g else "industry"))
    w["rate_calc"] = w.taken / w.granted * 100
    w = w[["kind", "group", "year", "granted", "taken", "rate", "rate_calc"]].sort_values(["kind", "group", "year"])
    w.to_csv(OUT / "paid_leave.csv", index=False, float_format="%.3f")
    print((w.rate - w.rate_calc).abs().describe())
