"""03b 問い直し：2021年からのサービスの上昇（+6%）は、どの区分によるのか。
サービスを、公共サービス・外食・民営家賃・持家の帰属家賃・他のサービスの5区分に分け、
2025年基準のウエイト（1万分比）で、2021年平均→最新の上昇への寄与（近似）を出す。
出力：results/requestion.json, results/services_contrib.csv
"""
import csv, io, json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D, R = ROOT / "data" / "raw", ROOT / "data", ROOT / "results"
PARTS = {"0221": "public_services", "0229": "eating_out", "0230": "private_rent", "0231": "imputed_rent", "0232": "other_services"}
JP = {"public_services": "公共サービス", "eating_out": "外食", "private_rent": "民営家賃", "imputed_rent": "持家の帰属家賃", "other_services": "他のサービス"}


def main():
    rows = list(csv.reader(io.StringIO((RAW / "cpi_goods_services_monthly.csv").read_bytes().decode("cp932"))))
    w = {PARTS[c]: float(rows[5][j]) for j, c in enumerate(rows[2]) if c in PARTS}
    tot_w = sum(w.values())
    s = pd.read_csv(R / "since2021.csv", index_col=0).since_2021
    t = pd.DataFrame([dict(part=JP[k], weight=w[k], weight_share=w[k] / tot_w * 100, change_pct=float(s[k]), contrib_pt=w[k] / tot_w * float(s[k])) for k in PARTS.values()])
    t.round(4).to_csv(R / "services_contrib.csv", index=False)
    out = dict(sum_contrib=float(t.contrib_pt.sum()), services_change=float(s["services"]), weight_total=tot_w,
               **{f"contrib_{k}": float(t.set_index("part").loc[JP[k], "contrib_pt"]) for k in PARTS.values()},
               **{f"wshare_{k}": float(w[k] / tot_w * 100) for k in PARTS.values()})
    out["eating_out_share_of_rise"] = out["contrib_eating_out"] / out["sum_contrib"] * 100
    out["other_services_share_of_rise"] = out["contrib_other_services"] / out["sum_contrib"] * 100
    json.dump({k: round(v, 3) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(t.round(2)); print(out)


if __name__ == "__main__":
    main()
