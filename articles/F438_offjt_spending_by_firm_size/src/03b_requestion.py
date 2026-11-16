"""03b 問い直し：規模による差は「1人あたりにいくらかけるか」と「そもそも OFF-JT に費用を出すか」のどちらから来ているのか。
(1) 3回平均（はじめ：2009〜2011年度調査、おわり：2023〜2025年度調査）で、規模別の1人あたり費用・支出した企業の割合・全企業で平らにした目安を比べる。
(2) 1,000人以上と30〜49人の比を、1人あたり費用の比と、支出した企業の割合の比に分ける（目安＝1人あたり×割合 なので、比はかけ算に分かれる）。
(3) 年度ごとの振れ（前回との差の標準偏差）。
(4) レビューで追加：調査年度ごと・全17回の平均での分け方。
出力：results/requestion.json, results/early_late.csv, results/requestion_by_year.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
U = ["s1000", "s300", "s100", "s50", "s30", "total"]


def main():
    w = pd.read_csv(R / "size_wide.csv", header=[0, 1], index_col=0)
    pw, sh, fl, real = w["per_worker"], w["share_spend"], w["flat"], w["per_worker_real"]
    el = pd.DataFrame({
        "pw_early": pw.loc[2009:2011].mean(), "pw_late": pw.loc[2023:2025].mean(),
        "real_early": real.loc[2009:2011].mean(), "real_late": real.loc[2023:2025].mean(),
        "share_early": sh.loc[2009:2011].mean(), "share_late": sh.loc[2023:2025].mean(),
        "flat_early": fl.loc[2009:2011].mean(), "flat_late": fl.loc[2023:2025].mean()}).loc[U]
    el.round(4).to_csv(R / "early_late.csv")
    q = {}
    for t in ("early", "late"):
        q[f"ratio_flat_{t}"] = float(el.loc["s1000", f"flat_{t}"] / el.loc["s30", f"flat_{t}"])
        q[f"ratio_pw_{t}"] = float(el.loc["s1000", f"pw_{t}"] / el.loc["s30", f"pw_{t}"])
        q[f"ratio_share_{t}"] = float(el.loc["s1000", f"share_{t}"] / el.loc["s30", f"share_{t}"])
        q[f"share_of_log_gap_from_share_{t}"] = float(np.log(q[f"ratio_share_{t}"]) / np.log(q[f"ratio_flat_{t}"]) * 100)
        for u in U:
            q[f"pw_{u}_{t}"] = float(el.loc[u, f"pw_{t}"]); q[f"share_{u}_{t}"] = float(el.loc[u, f"share_{t}"]); q[f"real_{u}_{t}"] = float(el.loc[u, f"real_{t}"])
    q["real_total_chg_pct"] = float((el.loc["total", "real_late"] / el.loc["total", "real_early"] - 1) * 100)
    q["nom_total_chg_pct"] = float((el.loc["total", "pw_late"] / el.loc["total", "pw_early"] - 1) * 100)
    q.update({f"vol_pw_{u}": float(pw[u].diff().std()) for u in U})
    q["share_gap_1000_30_early"] = float(el.loc["s1000", "share_early"] - el.loc["s30", "share_early"])
    q["share_gap_1000_30_late"] = float(el.loc["s1000", "share_late"] - el.loc["s30", "share_late"])
    q["share_drop_2019_2020_total"] = float(sh.loc[2020, "total"] - sh.loc[2019, "total"])
    # (4) レビューで追加：差の分け方が期間の取り方でどれだけ動くか（調査年度ごと・全17回の平均）
    rp, rs = pw["s1000"] / pw["s30"], sh["s1000"] / sh["s30"]
    by = pd.DataFrame({"ratio_pw": rp, "ratio_share": rs, "pct_from_share": np.log(rs) / (np.log(rs) + np.log(rp)) * 100})
    by.round(4).to_csv(R / "requestion_by_year.csv")
    q["pct_from_share_by_year_median"] = float(by.pct_from_share.median())
    q["pct_from_share_2025"] = float(by.pct_from_share.loc[2025])
    q["n_years_pw_ratio_below1"] = int((rp < 1).sum())
    a, b = pw.loc[2009:2025].mean(), sh.loc[2009:2025].mean()
    q["ratio_pw_all"] = float(a["s1000"] / a["s30"]); q["ratio_share_all"] = float(b["s1000"] / b["s30"])
    q["pct_from_share_all"] = float(np.log(q["ratio_share_all"]) / (np.log(q["ratio_share_all"]) + np.log(q["ratio_pw_all"])) * 100)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in q.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(el.round(2).to_string()); print(json.dumps({k: round(v, 3) if isinstance(v, float) else v for k, v in q.items()}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
