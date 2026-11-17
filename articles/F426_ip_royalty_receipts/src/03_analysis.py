"""03 分析：受取の伸び（著作権・産業財産権）、構成、ドル建て、地域、頑健性。
出力：results/main.json, results/annual_table.csv, results/region_shares.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def cagr(s, y0, y1):
    return float(((s.loc[y1] / s.loc[y0]) ** (1 / (y1 - y0)) - 1) * 100)


def slope(s, y0, y1):
    x = s.loc[y0:y1]
    return float((np.exp(np.polyfit(x.index, np.log(x.values), 1)[0]) - 1) * 100)


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    m = pd.read_csv(D / "monthly.csv").set_index("ym")
    t = pd.DataFrame({"ip_rec": a.ip_rec / 1e4, "ind_rec": a.ind_rec / 1e4, "cr_rec": a.cr_rec / 1e4, "cr_pay": a.cr_pay / 1e4,
                      "cr_net": a.cr_net / 1e4, "ind_net": a.ind_net / 1e4, "ip_net": a.ip_net / 1e4,
                      "cr_rec_usd": a.cr_rec_usd, "ind_rec_usd": a.ind_rec_usd, "usdjpy": a.usdjpy,
                      "cr_share_ip_rec": a.cr_rec / a.ip_rec * 100, "ip_share_services_rec": a.ip_rec / a.services_rec * 100})
    t.round(4).to_csv(R / "annual_table.csv")   # 兆円、ドル建ては億ドル（億円÷円）
    r = pd.read_csv(D / "region_annual.csv").set_index("year")
    r = r.drop(columns=["非分類"])
    sh = r.div(r["合計"], axis=0) * 100
    sh.round(3).to_csv(R / "region_shares.csv")
    y = 2025
    main = dict(cr_rec_2014=float(t.loc[2014, "cr_rec"]), cr_rec_2025=float(t.loc[y, "cr_rec"]), ind_rec_2014=float(t.loc[2014, "ind_rec"]), ind_rec_2025=float(t.loc[y, "ind_rec"]),
                ip_rec_2025=float(t.loc[y, "ip_rec"]), cr_rec_1996=float(t.loc[1996, "cr_rec"]),
                cr_cagr_2014_2025=cagr(t.cr_rec, 2014, 2025), ind_cagr_2014_2025=cagr(t.ind_rec, 2014, 2025),
                cr_share_2014=float(t.loc[2014, "cr_share_ip_rec"]), cr_share_2025=float(t.loc[y, "cr_share_ip_rec"]),
                ind_share_2025=float(100 - t.loc[y, "cr_share_ip_rec"]),
                cr_usd_2014=float(t.loc[2014, "cr_rec_usd"]), cr_usd_2025=float(t.loc[y, "cr_rec_usd"]), cr_usd_ratio=float(t.loc[y, "cr_rec_usd"] / t.loc[2014, "cr_rec_usd"]),
                ind_usd_ratio=float(t.loc[y, "ind_rec_usd"] / t.loc[2014, "ind_rec_usd"]),
                cr_pay_2025=float(t.loc[y, "cr_pay"]), cr_net_2025=float(t.loc[y, "cr_net"]), ind_net_2025=float(t.loc[y, "ind_net"]),
                ip_share_services_2025=float(t.loc[y, "ip_share_services_rec"]),
                region_asia_2025=float(sh.loc[y, "アジア"]), region_na_2025=float(sh.loc[y, "北米"]), region_us_2025=float(sh.loc[y, "米国"]),
                region_eu_2025=float(sh.loc[y, "欧州"]), region_china_2025=float(sh.loc[y, "中国"]), region_asia_2014=float(sh.loc[2014, "アジア"]),
                region_na_2014=float(sh.loc[2014, "北米"]), region_china_2014=float(sh.loc[2014, "中国"]), region_us_2014=float(sh.loc[2014, "米国"]),
                region_total_2025=float(r.loc[y, "合計"] / 1e4))
    main["H1"] = "支持" if main["cr_cagr_2014_2025"] > main["ind_cagr_2014_2025"] else "外れ"
    main["H2"] = "支持" if main["ind_share_2025"] >= 200 / 3 else "外れ"
    main["H3"] = "支持" if main["cr_usd_ratio"] >= 2 else "外れ"
    main["H4"] = "支持" if main["region_asia_2025"] > main["region_na_2025"] else "外れ"
    rob = []
    for lab, y0, y1, f in [("2014→2025年 両端の比（本線）", 2014, 2025, cagr), ("2014〜2025年 対数の傾き", 2014, 2025, slope),
                           ("2005→2025年 両端の比", 2005, 2025, cagr), ("2019→2025年 両端の比", 2019, 2025, cagr)]:
        rob.append(dict(check=lab, cr_rec_pct=f(t.cr_rec, y0, y1), ind_rec_pct=f(t.ind_rec, y0, y1),
                        cr_rec_usd_pct=f(t.cr_rec_usd, y0, y1), ind_rec_usd_pct=f(t.ind_rec_usd, y0, y1)))
    roll = m[["ip_rec", "ind_rec", "cr_rec"]].rolling(12).sum().dropna().iloc[-1]
    rob.append(dict(check=f"最新の12か月（{int(m.index[-1])}まで）の産業財産権の割合", cr_rec_pct=np.nan, ind_rec_pct=float(roll.ind_rec / roll.ip_rec * 100), cr_rec_usd_pct=np.nan, ind_rec_usd_pct=np.nan))
    pd.DataFrame(rob).round(3).to_csv(R / "robustness.csv", index=False)
    main["latest_12m_ind_share"] = float(roll.ind_rec / roll.ip_rec * 100)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())
    print(t.loc[[1996, 2005, 2014, 2019, 2022, 2023, 2024, 2025]].round(2).to_string())
    print(sh.loc[[2014, 2019, 2025]].round(1).T.to_string())


if __name__ == "__main__":
    main()
