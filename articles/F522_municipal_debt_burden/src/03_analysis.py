"""主な分析：将来負担比率・実質公債費比率の分布の推移、人口規模別、改善の内訳（地方債と基金）。仮説と頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "muni_year.csv", dtype={"code": str})
YEARS = [2009, 2014, 2019, 2024]
SEIREI = ["札幌市", "仙台市", "さいたま市", "千葉市", "横浜市", "川崎市", "相模原市", "新潟市", "静岡市", "浜松市", "名古屋市",
          "京都市", "大阪市", "堺市", "神戸市", "岡山市", "広島市", "北九州市", "福岡市", "熊本市"]  # 2024年度の政令市
BINS = [0, 5000, 10000, 30000, 100000, 300000, 1e9]
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]
d["fbr"] = d.fbr_raw.fillna(0.0)          # 「－」（負担なし）は0とする
d["fbr_none"] = d.fbr_raw.isna()
d["debt_r"] = 100 * d.debt / d.sfs        # 地方債現在高÷標準財政規模（%）
d["fund_r"] = 100 * d.fund / d.sfs        # 積立金現在高÷標準財政規模（%）
d["net_r"] = d.debt_r - d.fund_r
d["seirei"] = d.name.isin(SEIREI) & (d.kind == "city")
d["size"] = pd.cut(d["pop"], BINS, right=False, labels=LABELS).astype(str)
d["key"] = d.pref + "_" + d.name
d.to_csv(R / "muni_year_ratio.csv", index=False, float_format="%.4f")


def r(x, k=1):
    return round(float(x), k)


def summ(g):
    w = g.sfs
    return pd.Series({"n": len(g), "fbr_median": r(g.fbr.median()), "fbr_q1": r(g.fbr.quantile(.25)), "fbr_q3": r(g.fbr.quantile(.75)),
                      "fbr_q90": r(g.fbr.quantile(.9)), "fbr_none_pct": r(100 * g.fbr_none.mean()),
                      "fbr_weighted": r((g.fbr * w).sum() / w.sum()), "rdsr_median": r(g.rdsr.median()), "rdsr_weighted": r((g.rdsr * w).sum() / w.sum()),
                      "rdsr_over18": int((g.rdsr >= 18).sum()), "fbr_over200": int((g.fbr >= 200).sum()), "fbr_over350": int((g.fbr >= 350).sum()),
                      "debt_r_median": r(g.debt_r.median()), "fund_r_median": r(g.fund_r.median()), "net_r_median": r(g.net_r.median()),
                      "debt_r_total": r(100 * g.debt.sum() / g.sfs.sum()), "fund_r_total": r(100 * g.fund.sum() / g.sfs.sum())})


yr = d.groupby("year").apply(summ, include_groups=False)
yr.to_csv(R / "by_year.csv")
sz = d.groupby(["year", "size"]).apply(summ, include_groups=False).reset_index()
sz["size"] = pd.Categorical(sz["size"], LABELS, ordered=True)
sz = sz.sort_values(["year", "size"])
sz.to_csv(R / "by_year_size.csv", index=False)

# 改善の内訳：地方債÷標準財政規模の減少と、積立金÷標準財政規模の増加（合計の比と中央値）
y0, y1 = d[d.year == 2009], d[d.year == 2024]
dec = {"debt_r_total_2009": r(100 * y0.debt.sum() / y0.sfs.sum()), "debt_r_total_2024": r(100 * y1.debt.sum() / y1.sfs.sum()),
       "fund_r_total_2009": r(100 * y0.fund.sum() / y0.sfs.sum()), "fund_r_total_2024": r(100 * y1.fund.sum() / y1.sfs.sum()),
       "debt_r_median_2009": r(y0.debt_r.median()), "debt_r_median_2024": r(y1.debt_r.median()),
       "fund_r_median_2009": r(y0.fund_r.median()), "fund_r_median_2024": r(y1.fund_r.median()),
       "debt_trillion_2009": r(y0.debt.sum() / 1e9, 2), "debt_trillion_2024": r(y1.debt.sum() / 1e9, 2),
       "fund_trillion_2009": r(y0.fund.sum() / 1e9, 2), "fund_trillion_2024": r(y1.fund.sum() / 1e9, 2),
       "sfs_trillion_2009": r(y0.sfs.sum() / 1e9, 2), "sfs_trillion_2024": r(y1.sfs.sum() / 1e9, 2)}
dec["debt_drop_pt"] = r(dec["debt_r_total_2009"] - dec["debt_r_total_2024"])
dec["fund_rise_pt"] = r(dec["fund_r_total_2024"] - dec["fund_r_total_2009"])
dec["fund_share_pct"] = r(100 * dec["fund_rise_pt"] / (dec["fund_rise_pt"] + dec["debt_drop_pt"]))
pd.Series(dec).to_csv(R / "decomposition_debt_fund.csv", header=["value"])

a, b = yr.loc[2009], yr.loc[2024]
hyp = {
    "H1": {"fbr_median_2009": float(a.fbr_median), "fbr_median_2024": float(b.fbr_median), "verdict": "支持" if b.fbr_median <= a.fbr_median / 2 else "外れ"},
    "H2": {"fbr_none_pct_2024": float(b.fbr_none_pct), "verdict": "支持" if b.fbr_none_pct >= 50 else "外れ"},
    "H3": {"rdsr_median_2009": float(a.rdsr_median), "rdsr_median_2024": float(b.rdsr_median), "drop": r(a.rdsr_median - b.rdsr_median),
           "verdict": "支持" if a.rdsr_median - b.rdsr_median >= 3 else "外れ"},
    "H4": {"fund_rise_pt": dec["fund_rise_pt"], "debt_drop_pt": dec["debt_drop_pt"], "verdict": "支持" if dec["fund_rise_pt"] > dec["debt_drop_pt"] else "外れ"},
}
# 頑健性
both = set(y0.key) & set(y1.key) & set(d[d.year == 2014].key) & set(d[d.year == 2019].key)
cons = d[d.key.isin(both)]
cy = cons.groupby("year").apply(summ, include_groups=False)
ns = d[~d.seirei].groupby("year").apply(summ, include_groups=False)
pos = d[~d.fbr_none].groupby("year").fbr.median()
rob = [
    {"check": "本線：将来負担比率の中央値 2009→2024年度（「－」は0）", "v2009": a.fbr_median, "v2024": b.fbr_median},
    {"check": "比率が出ている団体だけの中央値", "v2009": r(pos[2009]), "v2024": r(pos[2024])},
    {"check": "標準財政規模で重みをつけた平均", "v2009": a.fbr_weighted, "v2024": b.fbr_weighted},
    {"check": f"4つの年度すべてにある団体だけ（{len(both)}団体）の中央値", "v2009": cy.loc[2009].fbr_median, "v2024": cy.loc[2024].fbr_median},
    {"check": "政令市を除いた中央値", "v2009": ns.loc[2009].fbr_median, "v2024": ns.loc[2024].fbr_median},
    {"check": "本線：実質公債費比率の中央値", "v2009": a.rdsr_median, "v2024": b.rdsr_median},
    {"check": "実質公債費比率：重みつき平均", "v2009": a.rdsr_weighted, "v2024": b.rdsr_weighted},
    {"check": "実質公債費比率：4つの年度すべてにある団体の中央値", "v2009": cy.loc[2009].rdsr_median, "v2024": cy.loc[2024].rdsr_median},
    {"check": "実質公債費比率：政令市を除いた中央値", "v2009": ns.loc[2009].rdsr_median, "v2024": ns.loc[2024].rdsr_median},
    {"check": "（地方債−積立金）÷標準財政規模の中央値", "v2009": a.net_r_median, "v2024": b.net_r_median},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
sd = d[d.seirei]
main = {"n": {str(k): int(v) for k, v in yr.n.items()}, "by_year": {str(k): {c: float(v) for c, v in row.items()} for k, row in yr.iterrows()},
        "seirei_fbr_median": {str(k): r(v) for k, v in sd.groupby("year").fbr.median().items()},
        "decomposition": dec, "hypotheses": hyp}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(yr.T.to_string()); print(sz[sz.year.isin([2009, 2024])][["year", "size", "n", "fbr_median", "fbr_none_pct", "rdsr_median", "debt_r_median", "fund_r_median"]].to_string())
print(json.dumps(dec, ensure_ascii=False)); print(json.dumps(hyp, ensure_ascii=False)); print(pd.DataFrame(rob).to_string()); print(main["seirei_fbr_median"])
