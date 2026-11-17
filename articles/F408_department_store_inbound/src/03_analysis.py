"""年の値・商品別・訪日客の買物との比較・月次の相関・地域・頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
ITEMS = ["total", "clothes", "mens", "womens", "other_clothes", "accessories", "food", "others",
         "furniture", "appliances", "household", "other_goods", "restaurant"]
JA = {"total": "合計", "clothes": "衣料品計", "mens": "紳士服・洋品", "womens": "婦人・子供服・洋品", "other_clothes": "その他の衣料品",
      "accessories": "身の回り品", "food": "飲食料品", "others": "その他計", "furniture": "家具", "appliances": "家庭用電気機械器具",
      "household": "家庭用品", "other_goods": "その他の商品", "restaurant": "食堂・喫茶"}
BIG10 = ["北海道", "宮城県", "東京都", "神奈川県", "愛知県", "京都府", "大阪府", "兵庫県", "広島県", "福岡県"]
BIG5 = ["東京都", "愛知県", "京都府", "大阪府", "福岡県"]


def r(x, k=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def main():
    d = pd.read_csv(D / "dept_monthly.csv")
    v = pd.read_csv(D / "visitors_monthly.csv")
    k = pd.read_csv(D / "inbound_shopping.csv").set_index("year")
    p = pd.read_csv(D / "dept_pref_annual.csv")
    cpi = pd.read_csv(D / "cpi_annual.csv").set_index("year")["cpi_all"]

    full = d.groupby("year").filter(lambda g: len(g) == 12)
    A = full.groupby("year", sort=True)[ITEMS].sum()
    A["total_real"] = A["total"] / A.index.map(cpi) * 100
    A.to_csv(R / "dept_annual.csv", float_format="%.1f")
    V = v.groupby("year").filter(lambda g: len(g) == 12).groupby("year", sort=True)["visitors"].sum()

    m = {}
    m["dept_total_oku"] = {str(y): r(A.loc[y, "total"] / 100, 0) for y in [1991, 2010, 2018, 2019, 2020, 2023, 2024, 2025]}
    m["dept_peak_year"] = int(A["total"].idxmax())
    h1 = (A.loc[2025, "total"] / A.loc[2019, "total"] - 1) * 100
    m["H1_dept_2019_2025_pct"] = r(h1, 2)
    m["H1_judge"] = "支持" if h1 > 0 else "外れ"
    m["dept_2019_2024_pct"] = r((A.loc[2024, "total"] / A.loc[2019, "total"] - 1) * 100, 2)
    m["dept_2024_2025_pct"] = r((A.loc[2025, "total"] / A.loc[2024, "total"] - 1) * 100, 2)
    m["dept_real_2019_2025_pct"] = r((A.loc[2025, "total_real"] / A.loc[2019, "total_real"] - 1) * 100, 2)
    m["cpi_2019_2025_pct"] = r((cpi.loc[2025] / cpi.loc[2019] - 1) * 100, 2)

    # 商品別
    it = []
    for c in ITEMS:
        it.append({"item": c, "item_ja": JA[c], "y2018": A.loc[2018, c], "y2019": A.loc[2019, c], "y2025": A.loc[2025, c],
                   "pct_2019_2025": (A.loc[2025, c] / A.loc[2019, c] - 1) * 100,
                   "pct_2018_2025": (A.loc[2025, c] / A.loc[2018, c] - 1) * 100,
                   "diff_oku": (A.loc[2025, c] - A.loc[2019, c]) / 100,
                   "share_2019": A.loc[2019, c] / A.loc[2019, "total"] * 100, "share_2025": A.loc[2025, c] / A.loc[2025, "total"] * 100})
    it = pd.DataFrame(it)
    it.to_csv(R / "items.csv", index=False, float_format="%.3f")
    I = it.set_index("item")
    m["items_pct_2019_2025"] = {JA[c]: r(I.loc[c, "pct_2019_2025"], 2) for c in ITEMS}
    m["items_diff_oku"] = {JA[c]: r(I.loc[c, "diff_oku"], 0) for c in ITEMS}
    m["items_share"] = {JA[c]: [r(I.loc[c, "share_2019"], 2), r(I.loc[c, "share_2025"], 2)] for c in ["clothes", "accessories", "food", "other_goods"]}
    acc, food, clo = I.loc["accessories", "pct_2019_2025"], I.loc["food", "pct_2019_2025"], I.loc["clothes", "pct_2019_2025"]
    m["H2_judge"] = "支持" if acc > food and acc > clo else "外れ"

    # 訪日客の買物
    ib = []
    for y in [2019, 2023, 2024, 2025]:
        vis = V.loc[y]
        shop = vis * k.loc[y, "shopping_per_person_yen"] / 1e8
        tf = vis * k.loc[y, "taxfree_rate_pct"] / 100 * k.loc[y, "taxfree_per_buyer_yen"] / 1e8
        ib.append({"year": y, "visitors": int(vis), "shopping_per_person_yen": k.loc[y, "shopping_per_person_yen"], "shopping_total_oku": shop,
                   "taxfree_total_oku": tf, "dept_use_rate_pct": k.loc[y, "dept_use_rate_pct"], "dept_total_oku": A.loc[y, "total"] / 100})
    ib = pd.DataFrame(ib).set_index("year")
    ib.to_csv(R / "inbound_vs_dept.csv", float_format="%.3f")
    d_dept = ib.loc[2025, "dept_total_oku"] - ib.loc[2019, "dept_total_oku"]
    d_shop = ib.loc[2025, "shopping_total_oku"] - ib.loc[2019, "shopping_total_oku"]
    d_tf = ib.loc[2025, "taxfree_total_oku"] - ib.loc[2019, "taxfree_total_oku"]
    m["visitors"] = {str(y): int(ib.loc[y, "visitors"]) for y in ib.index}
    m["shopping_total_oku"] = {str(y): r(ib.loc[y, "shopping_total_oku"], 0) for y in ib.index}
    m["taxfree_total_oku"] = {str(y): r(ib.loc[y, "taxfree_total_oku"], 0) for y in ib.index}
    m["dept_use_rate_pct"] = {str(y): r(ib.loc[y, "dept_use_rate_pct"], 1) for y in ib.index}
    m["delta_dept_oku_2019_2025"] = r(d_dept, 0)
    m["delta_shopping_oku_2019_2025"] = r(d_shop, 0)
    m["delta_taxfree_oku_2019_2025"] = r(d_tf, 0)
    if h1 > 0:
        m["H5_judge"] = "支持" if d_shop > d_dept else "外れ"
        m["share_needed_pct"] = r(d_dept / d_shop * 100, 1)
    else:
        m["H5_judge"] = "判定できず"
    # 仮の割合 s（訪日客の買物のうち百貨店で使われた割合）を置いたときの「訪日客以外」の販売額の 2019→2025 年の変化
    sc = []
    for s in [0.1, 0.2, 0.3, 0.4]:
        dom19 = ib.loc[2019, "dept_total_oku"] - s * ib.loc[2019, "shopping_total_oku"]
        dom25 = ib.loc[2025, "dept_total_oku"] - s * ib.loc[2025, "shopping_total_oku"]
        sc.append({"assumed_share": s, "inbound_2019_oku": s * ib.loc[2019, "shopping_total_oku"], "inbound_2025_oku": s * ib.loc[2025, "shopping_total_oku"],
                   "other_2019_oku": dom19, "other_2025_oku": dom25, "other_pct": (dom25 / dom19 - 1) * 100})
    sc = pd.DataFrame(sc); sc.to_csv(R / "scenario_share.csv", index=False, float_format="%.3f")
    m["scenario_other_pct"] = {f"{int(s*100)}%": r(x, 2) for s, x in zip(sc["assumed_share"], sc["other_pct"])}

    # 月次：2019年同月比
    mm = d[["year", "month", "total", "accessories", "food", "clothes", "other_goods"]].merge(v, on=["year", "month"])
    b19 = mm[mm.year == 2019].set_index("month")
    mm = mm[(mm.year * 100 + mm.month >= 202301) & (mm.year * 100 + mm.month <= 202609)].copy()
    for c in ["total", "accessories", "food", "clothes", "other_goods", "visitors", "visitors_china"]:
        mm[c + "_vs2019"] = mm.apply(lambda x: x[c] / b19.loc[x["month"], c] * 100, axis=1)
    mm.to_csv(R / "monthly_vs2019.csv", index=False, float_format="%.3f")
    h3 = stats.pearsonr(mm["visitors_vs2019"], mm["total_vs2019"])[0]
    m["H3_corr"] = r(h3, 3)
    m["H3_judge"] = "支持" if h3 >= 0.3 else "外れ"
    m["H3_n_months"] = int(len(mm))
    m["corr_by_item"] = {JA[c]: r(stats.pearsonr(mm["visitors_vs2019"], mm[c + "_vs2019"])[0], 3) for c in ["accessories", "other_goods", "food", "clothes"]}
    sl = stats.linregress(mm["visitors_vs2019"], mm["total_vs2019"])
    m["H3_slope"] = r(sl.slope, 4)
    m["visitors_vs2019_range"] = [r(mm["visitors_vs2019"].min(), 1), r(mm["visitors_vs2019"].max(), 1)]
    m["dept_vs2019_range"] = [r(mm["total_vs2019"].min(), 1), r(mm["total_vs2019"].max(), 1)]

    # 地域
    P = p.pivot(index="pref", columns="year", values="dept_sales")
    big = [x for x in BIG10 if not np.isnan(P.loc[x, 2019]) and not np.isnan(P.loc[x, 2025])]
    big5 = [x for x in BIG5 if not np.isnan(P.loc[x, 2019]) and not np.isnan(P.loc[x, 2025])]
    reg = []
    for y in [2018, 2019, 2023, 2024, 2025]:
        bs = P.loc[big, y].sum(); b5 = P.loc[big5, y].sum(); nat = A.loc[y, "total"]
        reg.append({"year": y, "national": nat, "big": bs, "rest": nat - bs, "big5": b5, "rest5": nat - b5})
    reg = pd.DataFrame(reg).set_index("year")
    reg.to_csv(R / "region_groups.csv", float_format="%.1f")
    g = lambda c, y0, y1: (reg.loc[y1, c] / reg.loc[y0, c] - 1) * 100
    m["big_prefs"] = big
    m["big_share_2019_pct"] = r(reg.loc[2019, "big"] / reg.loc[2019, "national"] * 100, 1)
    m["big_share_2025_pct"] = r(reg.loc[2025, "big"] / reg.loc[2025, "national"] * 100, 1)
    m["H4_big_pct"] = r(g("big", 2019, 2025), 2)
    m["H4_rest_pct"] = r(g("rest", 2019, 2025), 2)
    m["H4_gap_pt"] = r(g("big", 2019, 2025) - g("rest", 2019, 2025), 2)
    m["H4_judge"] = "支持" if m["H4_gap_pt"] >= 5 else "外れ"
    pr = []
    for x in big:
        pr.append({"pref": x, "y2019": P.loc[x, 2019], "y2025": P.loc[x, 2025], "pct": (P.loc[x, 2025] / P.loc[x, 2019] - 1) * 100})
    pr = pd.DataFrame(pr); pr["order"] = pr["pref"].map({x: i for i, x in enumerate(BIG10)}); pr = pr.sort_values("order").drop(columns="order")
    pr.to_csv(R / "big_prefs.csv", index=False, float_format="%.2f")
    m["big_pref_pct"] = {a: r(b, 1) for a, b in zip(pr["pref"], pr["pct"])}

    # 頑健性
    rb = []
    def add(name, h, val, judge, note=""):
        rb.append({"check": name, "hypothesis": h, "value": r(val, 3), "judge": judge, "note": note})
    add("基本", "H1", h1, m["H1_judge"], "百貨店販売額 2019→2025 %")
    add("基本", "H2", acc, m["H2_judge"], f"身の回り品 %（飲食料品 {food:.1f}、衣料品計 {clo:.1f}）")
    add("基本", "H3", h3, m["H3_judge"], "相関 2023-01〜2026-09")
    add("基本", "H4", m["H4_gap_pt"], m["H4_judge"], "大都市のある都道府県 − それ以外（ポイント）")
    add("基本", "H5", d_shop - d_dept, m["H5_judge"], "訪日客の買物代の増加 − 百貨店の増加（億円）")
    v1 = (A.loc[2025, "total"] / A.loc[2018, "total"] - 1) * 100; add("1. 2018年を基準", "H1", v1, "支持" if v1 > 0 else "外れ")
    a18, f18, c18 = I.loc["accessories", "pct_2018_2025"], I.loc["food", "pct_2018_2025"], I.loc["clothes", "pct_2018_2025"]
    add("1. 2018年を基準", "H2", a18, "支持" if a18 > f18 and a18 > c18 else "外れ", f"飲食料品 {f18:.1f}、衣料品計 {c18:.1f}")
    gap18 = g("big", 2018, 2025) - g("rest", 2018, 2025); add("1. 2018年を基準", "H4", gap18, "支持" if gap18 >= 5 else "外れ")
    add("2. 実質（消費者物価の総合）", "H1", m["dept_real_2019_2025_pct"], "支持" if m["dept_real_2019_2025_pct"] > 0 else "外れ")
    mm2 = mm[mm.year >= 2024]
    c2 = stats.pearsonr(mm2["visitors_vs2019"], mm2["total_vs2019"])[0]; add("3. 2024年1月以降に絞る", "H3", c2, "支持" if c2 >= 0.3 else "外れ", f"{len(mm2)}か月")
    yy = d[["year", "month", "total"]].merge(v, on=["year", "month"]).sort_values(["year", "month"])
    yy["dept_yoy"] = yy["total"].pct_change(12) * 100; yy["vis_yoy"] = yy["visitors"].pct_change(12) * 100
    yy = yy[(yy.year * 100 + yy.month >= 202401) & (yy.year * 100 + yy.month <= 202609)]
    c3 = stats.pearsonr(yy["vis_yoy"], yy["dept_yoy"])[0]; add("3b. 前年同月比どうし（2024年1月以降）", "H3", c3, "支持" if c3 >= 0.3 else "外れ", f"{len(yy)}か月")
    cx = A.loc[2025, ["mens", "womens", "other_clothes"]].sum() / A.loc[2019, ["mens", "womens", "other_clothes"]].sum() * 100 - 100
    m["clothes_ex_acc_2019_2025_pct"] = r(cx, 2)
    add("6. 衣料品から身の回り品を除く（計画にない追加）", "H2", acc, "支持" if acc > food and acc > cx else "外れ", f"衣料品（身の回り品を除く） {cx:.1f}")
    gap5 = g("big5", 2019, 2025) - g("rest5", 2019, 2025); add("4. 大都市を5都府県に絞る", "H4", gap5, "支持" if gap5 >= 5 else "外れ")
    add("5. 免税物品購入額の総額で見る", "H5", d_tf - d_dept, "支持" if d_tf > d_dept else "外れ", "免税物品購入額の増加 − 百貨店の増加（億円）")
    pd.DataFrame(rb).to_csv(R / "robustness.csv", index=False)
    m["robust"] = {f"{x['check']}|{x['hypothesis']}": x["value"] for x in rb}
    m["robust_H4_big5_rest5"] = [r(g("big5", 2019, 2025), 2), r(g("rest5", 2019, 2025), 2)]
    (R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=1))
    print(pd.DataFrame(rb).to_string())


if __name__ == "__main__":
    main()
