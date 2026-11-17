"""02 整形：残高（年末、兆円）、地域別残高、年ごとの流れ（月次の合計）、名目GDP（暦年）を1つの年の表にする。
BOJ の残高は十億円、地域別は億円、流れは億円。すべて兆円にそろえる。
出力：data/annual.csv, data/region.csv
"""
import csv, io, pathlib
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
REG = {"BPBP6M1": "合計", "BPBP6M1AS": "アジア", "BPBP6M1CN": "中国", "BPBP6M1HK": "香港", "BPBP6M1SG": "シンガポール", "BPBP6M1TW": "台湾",
       "BPBP6M1KR": "韓国", "BPBP6M1NA": "北米", "BPBP6M1US": "米国", "BPBP6M1CS": "中南米", "BPBP6M1CI": "ケイマン諸島", "BPBP6M1EP": "欧州",
       "BPBP6M1GB": "英国", "BPBP6M1NL": "オランダ", "BPBP6M1FR": "フランス", "BPBP6M1CH": "スイス", "BPBP6M1DE": "ドイツ", "BPBP6M1OC": "大洋州",
       "BPBP6M1ME": "中東", "BPBP6M1AF": "アフリカ", "BPBP6M1EU": "EU", "BPBP6M1AA": "ASEAN"}


def main():
    s = load(RAW / "boj_iip_annual.json") / 1e3
    s = s.rename(columns={"BPBP6KL1": "inward", "BPBP6KL11": "inward_equity", "BPBP6KL12": "inward_reinv", "BPBP6KL13": "inward_debt",
                          "BPBP6KA1": "outward", "BPBP6KL38": "inward_mv", "BPBP6KA50": "outward_mv", "BPBP6KL": "liab_total", "BPBP6KA": "asset_total"})
    f = load(RAW / "boj_fdi_flow_monthly.json") / 1e4
    f = f.rename(columns={"BPBP6JYNFL13": "flow", "BPBP6JYNFL131": "flow_equity", "BPBP6JYNFL132": "flow_reinv", "BPBP6JYNFL133": "flow_debt"})
    yr = f.index // 100
    assert (f.groupby(yr).size() == 12).all()
    a = s.join(f.groupby(yr).sum())
    rows = list(csv.reader(io.StringIO((RAW / "esri_gaku-mcy2532.csv").read_bytes().decode("cp932"))))
    gdp = {int(r[0][:4]): float(r[1].replace(",", "")) / 1e3 for r in rows if r and r[0][:4].isdigit() and "/1-12" in r[0]}
    a["gdp"] = pd.Series(gdp)
    a.index.name = "year"
    a.round(4).to_csv(D / "annual.csv")
    r = load(RAW / "boj_fdi_region_annual.json").rename(columns=REG) / 1e4
    r.index.name = "year"
    r.round(4).to_csv(D / "region.csv")
    print(a[["inward", "outward", "flow", "gdp"]].iloc[[0, 9, 18, 28, 29]])


if __name__ == "__main__":
    main()
