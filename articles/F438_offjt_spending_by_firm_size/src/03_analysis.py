"""03 分析：OFF-JT の1人あたり費用と支出した企業の割合を、規模別・年度別に比べる。仮説と頑健性。
出力：results/main.json, results/size_wide.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
U = ["s1000", "s300", "s100", "s50", "s30", "total"]


def main():
    d = pd.read_csv(D / "offjt.csv")
    cpi = pd.read_csv(D / "cpi_fy.csv").set_index("fy").cpi
    s = d[d.group != "industry"].copy()
    s["cpi"] = s.spend_fy.map(cpi)
    base = cpi.get(2024)
    s["per_worker_real"] = s.per_worker / s.cpi * base
    s["flat"] = s.per_worker * s.share_spend / 100
    w = {k: s.pivot_table(index="survey_year", columns="unit", values=k)[U] for k in ["per_worker", "per_worker_real", "per_firm", "share_spend", "flat"]}
    pd.concat(w, axis=1).round(4).to_csv(R / "size_wide.csv")
    pw, sh = w["per_worker"], w["share_spend"]
    L = 2025
    m = {f"pw_{u}_{y}": float(pw.loc[y, u]) for u in U for y in (2009, 2015, 2020, 2021, 2025)}
    m.update({f"share_{u}_{y}": float(sh.loc[y, u]) for u in U for y in (2009, 2020, 2021, 2025)})
    m["ratio_pw_1000_30_2025"] = float(pw.loc[L, "s1000"] / pw.loc[L, "s30"])
    m["ratio_pw_1000_30_2009"] = float(pw.loc[2009, "s1000"] / pw.loc[2009, "s30"])
    m["gap_share_1000_30_2025"] = float(sh.loc[L, "s1000"] - sh.loc[L, "s30"])
    m["gap_share_1000_30_2009"] = float(sh.loc[2009, "s1000"] - sh.loc[2009, "s30"])
    m["chg_total_2020_2021_pct"] = float((pw.loc[2021, "total"] / pw.loc[2020, "total"] - 1) * 100)
    m["chg_total_2020_2025_pct"] = float((pw.loc[2025, "total"] / pw.loc[2020, "total"] - 1) * 100)
    m["chg_total_2009_2025_pct"] = float((pw.loc[2025, "total"] / pw.loc[2009, "total"] - 1) * 100)
    m["chg_real_total_2009_2025_pct"] = float((w["per_worker_real"].loc[2025, "total"] / w["per_worker_real"].loc[2009, "total"] - 1) * 100)
    m["min_total_year"] = int(pw.total.idxmin()); m["min_total"] = float(pw.total.min())
    m["max_total_year"] = int(pw.total.idxmax()); m["max_total"] = float(pw.total.max())
    m["cpi_fy2008"] = float(cpi[2008]); m["cpi_fy2024"] = float(cpi[2024])
    m["H1"] = "支持" if m["ratio_pw_1000_30_2025"] >= 2 else "外れ"
    m["H2"] = "支持" if m["gap_share_1000_30_2025"] >= 20 else "外れ"
    m["H3"] = "支持" if m["chg_total_2020_2021_pct"] <= -20 else "外れ"
    m["H4"] = "支持" if pw.loc[2025, "total"] > pw.loc[2020, "total"] else "外れ"
    rob = []
    pf = w["per_firm"]
    rob.append(dict(check="1社あたり平均額 2025年度調査：1,000人以上÷30〜49人（倍）", value=float(pf.loc[L, "s1000"] / pf.loc[L, "s30"])))
    rob.append(dict(check="実質（2024年度の物価）1人あたり 総数 2020→2021年度調査（%）", value=float((w["per_worker_real"].loc[2021, "total"] / w["per_worker_real"].loc[2020, "total"] - 1) * 100)))
    rob.append(dict(check="実質 1人あたり 総数 2020→2025年度調査（%）", value=float((w["per_worker_real"].loc[2025, "total"] / w["per_worker_real"].loc[2020, "total"] - 1) * 100)))
    for y0 in (2009, 2015, 2019):
        for u in ("s1000", "s30", "total"):
            rob.append(dict(check=f"名目 1人あたり {u} {y0}→2025年度調査（%）", value=float((pw.loc[L, u] / pw.loc[y0, u] - 1) * 100)))
    fl = w["flat"]
    rob.append(dict(check="全企業で平らにした目安（1人あたり×支出した割合）2025年度調査：1,000人以上÷30〜49人（倍）", value=float(fl.loc[L, "s1000"] / fl.loc[L, "s30"])))
    rob.append(dict(check="3回平均（2023〜2025年度調査）1人あたり：1,000人以上÷30〜49人（倍）", value=float(pw.loc[2023:2025, "s1000"].mean() / pw.loc[2023:2025, "s30"].mean())))
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(pw.round(2).to_string()); print(sh.round(1).to_string()); print(w["per_worker_real"].round(2).to_string())
    print(pd.DataFrame(rob).round(2).to_string()); print({k: m[k] for k in ["H1", "H2", "H3", "H4", "ratio_pw_1000_30_2025", "gap_share_1000_30_2025", "chg_total_2020_2021_pct"]})


if __name__ == "__main__":
    main()
