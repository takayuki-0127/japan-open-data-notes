"""紙・板紙・段ボールの増減、紙の減少の内訳、通販・宅配・引越用の割合、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
PAPER = ["newsprint", "printing_info", "wrapping", "sanitary", "misc_paper"]
BOARD = ["containerboard", "boxboard", "misc_board"]
JA = {"paper_total": "紙計", "newsprint": "新聞巻取紙", "printing_info": "印刷・情報用紙", "wrapping": "包装用紙",
      "sanitary": "衛生用紙", "misc_paper": "雑種紙", "board_total": "板紙計", "containerboard": "段ボール原紙",
      "boxboard": "紙器用板紙", "misc_board": "雑板紙", "cb_sheet": "段ボール（シート）"}


def r6(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 6)


def main():
    a = pd.read_csv(D / "annual.csv", index_col=0)
    P = lambda s: a[f"production__{s}"]
    S = lambda s: a[f"sales_qty__{s}"]
    C = lambda s: a[f"consumption__{s}"]
    m = {"year_first": int(a.index.min()), "year_last": int(a.index.max())}
    y0, y1 = 2008, 2025

    # 品種ごとの増減（生産）
    rows = []
    for s in ["paper_total"] + PAPER + ["board_total"] + BOARD + ["cb_sheet"]:
        v = P(s)
        rows.append({"series": s, "name_ja": JA[s], "unit": "千㎡" if s == "cb_sheet" else "t",
                     "v2008": r6(v[y0]), "v2010": r6(v[2010]), "v2014": r6(v[2014]), "v2019": r6(v[2019]), "v2025": r6(v[y1]),
                     "ratio_2025_2008": r6(v[y1] / v[y0]), "ratio_2025_2010": r6(v[y1] / v[2010]),
                     "ratio_2025_2014": r6(v[y1] / v[2014]),
                     "peak_year": int(v.idxmax()), "peak_value": r6(v.max())})
    tab = pd.DataFrame(rows)
    tab.to_csv(R / "change_by_grade.csv", index=False)
    m["grades"] = {r["series"]: r for r in rows}

    # 紙の減少の内訳（2008→2025、万t）
    dec_total = P("paper_total")[y1] - P("paper_total")[y0]
    contrib = {s: r6((P(s)[y1] - P(s)[y0]) / 1e4) for s in PAPER}
    m["paper_change_2008_2025_10kt"] = r6(dec_total / 1e4)
    m["paper_change_by_grade_10kt"] = contrib
    np_pi = (P("newsprint")[y1] - P("newsprint")[y0]) + (P("printing_info")[y1] - P("printing_info")[y0])
    m["share_newsprint_printing_in_decline"] = r6(np_pi / dec_total)
    # 紙と板紙を合わせた量、板紙の割合
    allp = P("paper_total") + P("board_total")
    m["all_paper_2008_10kt"] = r6(allp[y0] / 1e4); m["all_paper_2025_10kt"] = r6(allp[y1] / 1e4)
    m["all_paper_ratio_2025_2008"] = r6(allp[y1] / allp[y0])
    m["board_share_2008"] = r6(P("board_total")[y0] / allp[y0]); m["board_share_2025"] = r6(P("board_total")[y1] / allp[y1])
    m["year_board_exceeds_paper"] = int(a.index[P("board_total") > P("paper_total")].min())

    # 通販・宅配・引越用
    sh = C("use_mailorder") / C("use_total") * 100
    use = pd.DataFrame({"year": a.index, "use_total": C("use_total").values, "use_mailorder": C("use_mailorder").values,
                        "mailorder_share_pct": sh.values})
    use.to_csv(R / "mailorder_share.csv", index=False, float_format="%.6f")
    m["mailorder_share_2008"] = r6(sh[y0]); m["mailorder_share_2014"] = r6(sh[2014]); m["mailorder_share_2025"] = r6(sh[y1])
    m["mailorder_2008_100m2"] = r6(C("use_mailorder")[y0] / 1e5); m["mailorder_2025_100m2"] = r6(C("use_mailorder")[y1] / 1e5)
    m["mailorder_ratio_2025_2008"] = r6(C("use_mailorder")[y1] / C("use_mailorder")[y0])
    m["mailorder_peak_year"] = int(C("use_mailorder").idxmax())
    m["mailorder_share_2020"] = r6(sh[2020]); m["mailorder_share_2021"] = r6(sh[2021])

    # 2013→2014年の段差（段ボール側だけ）
    m["step_2013_2014_cb_sheet_pct"] = r6((P("cb_sheet")[2014] / P("cb_sheet")[2013] - 1) * 100)
    m["step_2013_2014_use_total_pct"] = r6((C("use_total")[2014] / C("use_total")[2013] - 1) * 100)
    m["step_2013_2014_containerboard_pct"] = r6((P("containerboard")[2014] / P("containerboard")[2013] - 1) * 100)

    g = m["grades"]
    m["containerboard_2025_over_peak"] = r6(g["containerboard"]["v2025"] / g["containerboard"]["peak_value"])
    m["cb_sheet_peak_since2014"] = int(P("cb_sheet").loc[2014:].idxmax())
    m["cb_sheet_peak_since2014_value"] = r6(P("cb_sheet").loc[2014:].max())
    # 仮説
    m["H1"] = {"ratio": g["paper_total"]["ratio_2025_2008"], "judge": "支持" if g["paper_total"]["ratio_2025_2008"] <= 0.7 else "外れ"}
    m["H2"] = {"ratio": g["containerboard"]["ratio_2025_2008"], "judge": "支持" if g["containerboard"]["ratio_2025_2008"] >= 1 else "外れ"}
    pk = g["containerboard"]["peak_year"]
    m["H3"] = {"peak_year": pk, "judge": "支持" if 2017 <= pk <= 2021 else "外れ"}
    d4 = m["mailorder_share_2025"] - m["mailorder_share_2008"]
    m["H4"] = {"diff_pt": r6(d4), "judge": "支持" if d4 >= 3 else "外れ"}
    m["H5"] = {"share": m["share_newsprint_printing_in_decline"], "judge": "支持" if m["share_newsprint_printing_in_decline"] >= 0.8 else "外れ"}

    # 頑健性
    rob = []
    def add(check, how, value, judge):
        rob.append({"check": check, "how": how, "value": r6(value), "judge": judge})
    add("H1", "基本：紙計 2025年 ÷ 2008年", g["paper_total"]["ratio_2025_2008"], m["H1"]["judge"])
    v = g["paper_total"]["ratio_2025_2010"]; add("H1", "基準を2010年に", v, "支持" if v <= 0.7 else "外れ")
    v = P("paper_total").loc[2023:2025].mean() / P("paper_total").loc[2008:2010].mean(); add("H1", "端を3年平均に（2023〜25年 ÷ 2008〜10年）", v, "支持" if v <= 0.7 else "外れ")
    v = S("paper_total")[y1] / S("paper_total")[y0]; add("H1", "生産の代わりに販売数量", v, "支持" if v <= 0.7 else "外れ")
    add("H2", "基本：段ボール原紙 2025年 ÷ 2008年", g["containerboard"]["ratio_2025_2008"], m["H2"]["judge"])
    v = g["containerboard"]["ratio_2025_2010"]; add("H2", "基準を2010年に", v, "支持" if v >= 1 else "外れ")
    v = P("containerboard").loc[2023:2025].mean() / P("containerboard").loc[2008:2010].mean(); add("H2", "端を3年平均に", v, "支持" if v >= 1 else "外れ")
    v = S("containerboard")[y1] / S("containerboard")[y0]; add("H2", "生産の代わりに販売数量", v, "支持" if v >= 1 else "外れ")
    v = g["cb_sheet"]["ratio_2025_2008"]; add("H2", "段ボール（シートの生産、千㎡）で 2025÷2008（2014年に段差あり）", v, "支持" if v >= 1 else "外れ")
    v = g["cb_sheet"]["ratio_2025_2014"]; add("H2", "段ボール（シート）で 2025÷2014（段差のあと）", v, "支持" if v >= 1 else "外れ")
    add("H3", "基本：段ボール原紙の生産の最大の年", pk, m["H3"]["judge"])
    ma = P("containerboard").rolling(3).mean(); v = int(ma.idxmax())
    add("H3", "3年移動平均の最大の年（終わりの年）", v, "支持" if 2017 <= v <= 2021 else "外れ")
    v = int(S("containerboard").idxmax()); add("H3", "販売数量の最大の年", v, "支持" if 2017 <= v <= 2021 else "外れ")
    v = int(P("cb_sheet").loc[2014:].idxmax()); add("H3", "段ボール（シート）の2014年以降の最大の年", v, "支持" if 2017 <= v <= 2021 else "外れ")
    add("H4", "基本：通販・宅配・引越用の割合 2025年 − 2008年（ポイント）", d4, m["H4"]["judge"])
    v = m["mailorder_share_2025"] - m["mailorder_share_2014"]; add("H4", "2014年（段差のあと）からの差", v, "支持" if v >= 3 else "外れ")
    v = sh.loc[2023:2025].mean() - sh.loc[2008:2010].mean(); add("H4", "端を3年平均に", v, "支持" if v >= 3 else "外れ")
    add("H5", "基本：紙の減少のうち新聞巻取紙と印刷・情報用紙の割合", m["share_newsprint_printing_in_decline"], m["H5"]["judge"])
    dd = P("paper_total")[y1] - P("paper_total")[2010]
    v = ((P("newsprint")[y1] - P("newsprint")[2010]) + (P("printing_info")[y1] - P("printing_info")[2010])) / dd
    add("H5", "基準を2010年に", v, "支持" if v >= 0.8 else "外れ")
    dd = S("paper_total")[y1] - S("paper_total")[y0]
    v = ((S("newsprint")[y1] - S("newsprint")[y0]) + (S("printing_info")[y1] - S("printing_info")[y0])) / dd
    add("H5", "販売数量で", v, "支持" if v >= 0.8 else "外れ")
    # 版による違い（2016・2017年）
    sb = pd.read_csv(D / "series_by_source.csv")
    pv = sb.pivot_table(index=["series", "measure", "year"], columns="source", values="value")
    both = pv.dropna(subset=["nenpo2017_paper.xls", "nenpo2020_paper.xls"])
    mx = float((both["nenpo2020_paper.xls"] / both["nenpo2017_paper.xls"] - 1).abs().max() * 100)
    m["revision_2016_2017_max_abs_pct"] = r6(mx); m["revision_n_compared"] = int(len(both))
    add("全体", "2016・2017年の値の、2017年版と2020年版の違い（最大の絶対値、%）", mx, "参考")
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)

    (R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: m[k] for k in ["H1", "H2", "H3", "H4", "H5"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
