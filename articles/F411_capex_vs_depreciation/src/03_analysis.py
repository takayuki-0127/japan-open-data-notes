"""設備投資 ÷ 減価償却費（R）の年度の推移、時期・規模・業種の比較、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
PERIODS = [("1954-1973", 1954, 1973), ("1974-1990", 1974, 1990), ("1991-2001", 1991, 2001),
           ("2002-2012", 2002, 2012), ("2013-2025", 2013, 2025)]
SIZE_JA = {"A": "全規模", "B": "資本金10億円以上", "C": "1億〜10億円", "D": "1千万〜1億円"}
IND_JA = {"all": "全産業（金融保険を除く）", "mfg": "製造業", "nonmfg": "非製造業（金融保険を除く）",
          "all_incl_fin": "全産業（金融保険を含む）", "fin": "金融業・保険業"}


def r6(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 6)


def main():
    fy = pd.read_csv(D / "fiscal_year.csv")
    fy["R_sw"] = fy["capex_sw"] / fy["dep"]
    fy["R_exsw"] = fy["capex_exsw"] / fy["dep"]
    fy["net_sw_tril"] = (fy["capex_sw"] - fy["dep"]) / 1e4
    fy["net_exsw_tril"] = (fy["capex_exsw"] - fy["dep"]) / 1e4
    fy["sw_share"] = fy["software"] / fy["capex_sw"]
    out = fy[["ind", "size", "fy", "capex_sw", "capex_exsw", "software", "dep", "R_sw", "R_exsw",
              "net_sw_tril", "net_exsw_tril", "sw_share"]]
    out.to_csv(R / "ratio_by_year.csv", index=False, float_format="%.6f")

    A = fy[(fy["ind"] == "all") & (fy["size"] == "A")].set_index("fy")
    m = {"fy_first": int(A.index.min()), "fy_last": int(A.index.max())}

    # 時期ごとの平均（全産業・全規模）
    per = []
    for name, a, b in PERIODS:
        s = A.loc[a:b]
        per.append({"period": name, "R_exsw_mean": r6(s["R_exsw"].mean()),
                    "R_sw_mean": r6(s["R_sw"].mean()) if s["R_sw"].notna().any() else None,
                    "net_exsw_tril_mean": r6(s["net_exsw_tril"].mean()), "years": int(len(s))})
    pd.DataFrame(per).to_csv(R / "ratio_by_period.csv", index=False)
    m["periods"] = per

    s = A.loc[2002:2025]
    m["R_sw_2002_2025_mean"] = r6(s["R_sw"].mean())
    m["R_sw_2002_2025_min"] = r6(s["R_sw"].min()); m["R_sw_2002_2025_min_fy"] = int(s["R_sw"].idxmin())
    m["R_sw_2002_2025_max"] = r6(s["R_sw"].max()); m["R_sw_2002_2025_max_fy"] = int(s["R_sw"].idxmax())
    m["R_sw_2025"] = r6(A.loc[2025, "R_sw"]); m["R_exsw_2025"] = r6(A.loc[2025, "R_exsw"])
    m["capex_sw_2025_tril"] = r6(A.loc[2025, "capex_sw"] / 1e4); m["dep_2025_tril"] = r6(A.loc[2025, "dep"] / 1e4)
    m["net_sw_2025_tril"] = r6(A.loc[2025, "net_sw_tril"])
    m["n_years_R_sw_below1"] = int((s["R_sw"] < 1).sum())
    m["n_years_R_sw_1_to_12"] = int(((s["R_sw"] >= 1) & (s["R_sw"] < 1.2)).sum())
    m["n_years_R_sw_ge12"] = int((s["R_sw"] >= 1.2).sum())
    m["years_R_sw_below1"] = [int(x) for x in s.index[s["R_sw"] < 1]]
    m["sw_share_2002"] = r6(A.loc[2002, "sw_share"]); m["sw_share_2025"] = r6(A.loc[2025, "sw_share"])
    pre = A.loc[1954:1990, "R_exsw"]; post = A.loc[2002:2025, "R_exsw"]
    m["R_exsw_1954_1990_mean"] = r6(pre.mean()); m["R_exsw_2002_2025_mean"] = r6(post.mean())
    m["R_exsw_max"] = r6(A["R_exsw"].max()); m["R_exsw_max_fy"] = int(A["R_exsw"].idxmax())
    m["R_exsw_1990"] = r6(A.loc[1990, "R_exsw"]); m["R_exsw_1973"] = r6(A.loc[1973, "R_exsw"])
    m["first_fy_R_exsw_below1"] = int(A.index[A["R_exsw"] < 1].min()) if (A["R_exsw"] < 1).any() else None
    m["n_years_R_exsw_below1_2002_2025"] = int((post < 1).sum())

    # 規模別・業種別（2002〜2025年度の平均）
    tab = []
    for ind in ["all", "mfg", "nonmfg"]:
        for size in ["A", "B", "C", "D"]:
            z = fy[(fy["ind"] == ind) & (fy["size"] == size)].set_index("fy")
            tab.append({"ind": ind, "ind_ja": IND_JA[ind], "size": size, "size_ja": SIZE_JA[size],
                        "R_sw_2002_2025": r6(z.loc[2002:2025, "R_sw"].mean()),
                        "R_sw_2011_2015": r6(z.loc[2011:2015, "R_sw"].mean()),
                        "R_sw_2021_2025": r6(z.loc[2021:2025, "R_sw"].mean()),
                        "R_exsw_1974_1990": r6(z.loc[1974:1990, "R_exsw"].mean()),
                        "R_exsw_2002_2025": r6(z.loc[2002:2025, "R_exsw"].mean()),
                        "sw_share_2021_2025": r6(z.loc[2021:2025, "sw_share"].mean())})
    tb = pd.DataFrame(tab)
    tb.to_csv(R / "ratio_by_size_industry.csv", index=False)
    m["by_size_industry"] = tab

    # 仮説の判定
    def look(ind, size, col):
        return tb[(tb["ind"] == ind) & (tb["size"] == size)][col].iloc[0]
    h1 = m["R_sw_2002_2025_mean"]
    m["H1"] = {"value": h1, "judge": "支持" if 1.0 <= h1 < 1.3 else "外れ"}
    diff = m["R_exsw_1954_1990_mean"] - m["R_exsw_2002_2025_mean"]
    m["H2"] = {"diff": r6(diff), "judge": "支持" if diff >= 0.4 else "外れ"}
    rd, rb = look("all", "D", "R_sw_2002_2025"), look("all", "B", "R_sw_2002_2025")
    m["H3"] = {"R_D": r6(rd), "R_B": r6(rb), "R_C": r6(look("all", "C", "R_sw_2002_2025")),
               "judge": "支持" if rd < rb else "外れ"}
    a1, a2 = A.loc[2011:2015, "R_sw"].mean(), A.loc[2021:2025, "R_sw"].mean()
    m["H4"] = {"R_2011_2015": r6(a1), "R_2021_2025": r6(a2), "judge": "支持" if a2 > a1 else "外れ"}

    # 頑健性
    rob = []
    def add(check, how, value, judge):
        rob.append({"check": check, "how": how, "value": r6(value), "judge": judge})
    add("H1", "基本：ソフトウェアを含む、全産業（金融保険を除く）、全規模、2002〜2025年度の平均", h1, m["H1"]["judge"])
    v = post.mean(); add("H1", "ソフトウェアを除く設備投資で", v, "支持" if 1.0 <= v < 1.3 else "外れ")
    F = fy[(fy["ind"] == "all_incl_fin") & (fy["size"] == "A")].set_index("fy")
    v = F.loc[2008:2025, "R_sw"].mean(); add("H1", "金融業・保険業を含む全産業（2008〜2025年度。データがこの期間のみ）", v, "支持" if 1.0 <= v < 1.3 else "外れ")
    v = A.loc[2008:2025, "R_sw"].mean(); add("H1", "同じ期間（2008〜2025年度）の金融保険を除く全産業（比べるため）", v, "支持" if 1.0 <= v < 1.3 else "外れ")
    keep = [y for y in range(2002, 2026) if y not in (2008, 2009, 2020)]
    v = A.loc[keep, "R_sw"].mean(); add("H1", "2008・2009・2020年度を除く", v, "支持" if 1.0 <= v < 1.3 else "外れ")
    v = s["R_sw"].median(); add("H1", "平均の代わりに中央値", v, "支持" if 1.0 <= v < 1.3 else "外れ")
    # 4四半期の移動合計
    q = pd.read_csv(D / "quarterly_long.csv")
    qa = q[(q["ind"] == "all") & (q["size"] == "A")].pivot_table(index=["fy", "fq", "label"], columns="item", values="oku_yen").reset_index()
    qa = qa.sort_values(["fy", "fq"]).reset_index(drop=True)
    roll = qa[["capex_sw", "dep"]].rolling(4).sum()
    qa["R_sw_roll4"] = roll["capex_sw"] / roll["dep"]
    z = qa.dropna(subset=["R_sw_roll4"])
    z = z[z["fy"] <= 2026]
    qa[["label", "fy", "fq", "R_sw_roll4"]].dropna().to_csv(R / "ratio_roll4_quarterly.csv", index=False, float_format="%.6f")
    v = float((z["R_sw_roll4"] < 1).mean())
    m["roll4_share_below1"] = r6(v); m["roll4_n"] = int(len(z)); m["roll4_last_label"] = str(z["label"].iloc[-1])
    m["roll4_last"] = r6(z["R_sw_roll4"].iloc[-1])
    add("H1", "4四半期の移動合計の比が1を下回った四半期の割合", v, "参考")
    pre2 = A.loc[1974:1990, "R_exsw"].mean()
    add("H2", "比べる時期を1974〜1990年度（安定成長期）だけに", pre2 - post.mean(), "支持" if pre2 - post.mean() >= 0.4 else "外れ")
    pre_med = A.loc[1954:1990, "R_exsw"].median() - post.median()
    add("H2", "中央値どうしの差", pre_med, "支持" if pre_med >= 0.4 else "外れ")
    for ind in ["mfg", "nonmfg"]:
        rd_, rb_ = look(ind, "D", "R_sw_2002_2025"), look(ind, "B", "R_sw_2002_2025")
        add("H3", f"{IND_JA[ind]}で（1千万〜1億円 − 10億円以上）", rd_ - rb_, "支持" if rd_ < rb_ else "外れ")
    rd_x, rb_x = look("all", "D", "R_exsw_2002_2025"), look("all", "B", "R_exsw_2002_2025")
    add("H3", "ソフトウェアを除く設備投資で（1千万〜1億円 − 10億円以上）", rd_x - rb_x, "支持" if rd_x < rb_x else "外れ")
    b1, b2 = A.loc[2010:2014, "R_sw"].mean(), A.loc[2022:2025, "R_sw"].mean()
    add("H4", "比べる期間を2010〜2014年度と2022〜2025年度に", b2 - b1, "支持" if b2 > b1 else "外れ")
    x1, x2 = A.loc[2011:2015, "R_exsw"].mean(), A.loc[2021:2025, "R_exsw"].mean()
    add("H4", "ソフトウェアを除く設備投資で（2021〜2025年度 − 2011〜2015年度）", x2 - x1, "支持" if x2 > x1 else "外れ")
    for ind in ["mfg", "nonmfg"]:
        y1, y2 = look(ind, "A", "R_sw_2011_2015"), look(ind, "A", "R_sw_2021_2025")
        add("H4", f"{IND_JA[ind]}で（2021〜2025年度 − 2011〜2015年度）", y2 - y1, "支持" if y2 > y1 else "外れ")
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)

    (R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: m[k] for k in ["H1", "H2", "H3", "H4"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
