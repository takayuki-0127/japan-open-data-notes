"""02 整形：月次から暦年（1996〜2025年、円・ドル）、四半期の地域別から暦年（2014〜2025年）の表を作る。
出力：data/annual.csv, data/region_annual.csv, data/monthly.csv
"""
import pathlib
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
NAME = {"BPBP6JYNSC906": "ip_rec", "BPBP6JYNSD906": "ip_pay", "BPBP6JYNSN906": "ip_net",
        "BPBP6JYNSC9061": "ind_rec", "BPBP6JYNSD9061": "ind_pay", "BPBP6JYNSN9061": "ind_net",
        "BPBP6JYNSC9062": "cr_rec", "BPBP6JYNSD9062": "cr_pay", "BPBP6JYNSN9062": "cr_net", "BPBP6JYNSC": "services_rec"}
REG = {"95": "合計", "AS95": "アジア", "CN95": "中国", "HK95": "香港", "TW95": "台湾", "KR95": "韓国", "SG95": "シンガポール", "TH95": "タイ",
       "IN95": "インド", "AA95": "ASEAN", "NA95": "北米", "US95": "米国", "CS95": "中南米", "OC95": "大洋州", "EP95": "欧州", "EU95": "EU",
       "GB95": "英国", "DE95": "ドイツ", "NL95": "オランダ", "CH95": "スイス", "ME95": "中東", "AF95": "アフリカ", "RW95": "非分類"}


def main():
    m = load(RAW / "boj_ip_monthly.json").rename(columns=NAME)
    m = m.join(load(RAW / "boj_usdjpy_monthly.json")["FXERM07"].rename("usdjpy"))
    m.index.name = "ym"; m["year"] = m.index // 100
    m.round(4).to_csv(D / "monthly.csv")
    full = m[m.year <= 2025]
    cols = list(NAME.values())
    a = full.groupby("year")[cols].sum(min_count=12)
    usd = full[cols].div(full.usdjpy, axis=0); usd["year"] = full.year
    a = a.join(usd.groupby("year")[cols].sum(min_count=12).add_suffix("_usd"))
    a["usdjpy"] = full.groupby("year").usdjpy.mean()
    a.round(4).to_csv(D / "annual.csv")
    q = load(RAW / "boj_ip_region_quarterly.json")
    q.columns = [REG[c.replace("BPBP6QSC", "")] for c in q.columns]
    q.index.name = "yq"; q["year"] = q.index // 100
    qa = q[q.year <= 2025].groupby("year").sum(min_count=4)
    assert (q[q.year <= 2025].groupby("year").size() == 4).all()
    qa.round(4).to_csv(D / "region_annual.csv")


if __name__ == "__main__":
    main()
