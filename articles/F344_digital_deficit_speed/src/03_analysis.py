"""デジタル赤字の年ごとの集計、伸び率、円安の分、受取・支払、地域。results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
m = pd.read_csv(D / "bop_monthly.csv")
q = pd.read_csv(D / "bop_quarterly_region.csv")
fxm = pd.read_csv(D / "usdjpy_monthly.csv")
OKU_TO_CHO = 1e4  # 億円 → 兆円

ITEM = {"9072": "コンピュータ", "9073": "情報", "9071": "通信", "9062": "著作権等使用料", "9061": "産業財産権等使用料",
        "9082": "専門・経営コンサル", "9081": "研究開発"}
DEFS = {"3項目": ["9072", "9062", "9082"], "5項目": ["9072", "9062", "9082", "9071", "9073"], "3項目＋研究開発": ["9072", "9062", "9082", "9081"]}


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


# 年の合計（12か月そろった年だけ）
def annual(flow):
    t = "SC" if flow == "受取" else ("SD" if flow == "支払" else "SN")
    out = {}
    for i in ITEM:
        s = m[m.code == f"BPBP6JYN{t}{i}"]
        g = s.groupby("year")["value"].agg(["sum", "count"])
        out[ITEM[i]] = g.loc[g["count"] == 12, "sum"] / OKU_TO_CHO
    return pd.DataFrame(out)


A = {f: annual(f) for f in ["受取", "支払", "ネット"]}
for f, df in A.items():
    df.round(4).to_csv(R / f"annual_{ {'受取': 'receipts', '支払': 'payments', 'ネット': 'net'}[f] }.csv")
fx = fxm.groupby("year")["value"].agg(["mean", "count"])
fx = fx.loc[fx["count"] == 12, "mean"]

main = {}
defsum = {}
for name, items in DEFS.items():
    cols = [ITEM[i] for i in items]
    defsum[name] = {f: A[f][cols].sum(axis=1, min_count=len(cols)) for f in A}
yrs = list(range(2014, 2026))
tab = pd.DataFrame({"year": yrs})
for name in DEFS:
    for f in ["受取", "支払", "ネット"]:
        tab[f"{name}_{f}"] = [defsum[name][f].get(y, np.nan) for y in yrs]
tab["usdjpy"] = [fx.get(y, np.nan) for y in yrs]
tab["3項目_ネット_億ドル"] = tab["3項目_ネット"] * 1e4 / tab["usdjpy"]  # 兆円×1e4＝億円、÷円/ドル＝億ドル
tab.round(4).to_csv(R / "digital_annual.csv", index=False)
T = tab.set_index("year")


def cagr(a, b, y0, y1):
    return 100 * ((b / a) ** (1 / (y1 - y0)) - 1)


net3 = -T["3項目_ネット"]  # 赤字を正で
main["deficit3_tyen"] = {str(y): r(net3.loc[y]) for y in [2014, 2019, 2020, 2022, 2023, 2024, 2025]}
main["deficit5_tyen"] = {str(y): r(-T.loc[y, "5項目_ネット"]) for y in [2014, 2019, 2024, 2025]}
main["cagr_3_2014_2025_pct"] = r(cagr(net3.loc[2014], net3.loc[2025], 2014, 2025), 1)
main["cagr_3_2019_2025_pct"] = r(cagr(net3.loc[2019], net3.loc[2025], 2019, 2025), 1)
main["cagr_3_2014_2024_pct"] = r(cagr(net3.loc[2014], net3.loc[2024], 2014, 2024), 1)
main["cagr_5_2014_2025_pct"] = r(cagr(-T.loc[2014, "5項目_ネット"], -T.loc[2025, "5項目_ネット"], 2014, 2025), 1)
main["cagr_3rd_2014_2025_pct"] = r(cagr(-T.loc[2014, "3項目＋研究開発_ネット"], -T.loc[2025, "3項目＋研究開発_ネット"], 2014, 2025), 1)
b = np.polyfit(np.arange(2014, 2026), np.log(net3.loc[2014:2025].values), 1)[0]
main["loglinear_growth_3_2014_2025_pct"] = r(100 * (np.exp(b) - 1), 1)
main["by_item_net_tyen"] = {it: {str(y): r(A["ネット"].loc[y, it]) for y in [2014, 2025]} for it in ITEM.values()}

# H2：円安の分（2020→2025）。ドル建ての赤字の伸びと比べる
usd = -T["3項目_ネット_億ドル"]
l_yen = np.log(net3.loc[2025] / net3.loc[2020]); l_usd = np.log(usd.loc[2025] / usd.loc[2020]); l_fx = np.log(T.loc[2025, "usdjpy"] / T.loc[2020, "usdjpy"])
main["h2"] = {"deficit_yen_2020_2025_tyen": [r(net3.loc[2020]), r(net3.loc[2025])], "deficit_usd_2020_2025_100m": [r(usd.loc[2020], 0), r(usd.loc[2025], 0)],
              "log_yen": r(l_yen, 3), "log_usd": r(l_usd, 3), "log_fx": r(l_fx, 3), "fx_share_pct": r(100 * l_fx / l_yen, 1),
              "yen_change_pct": r(100 * (net3.loc[2025] / net3.loc[2020] - 1), 1), "usd_change_pct": r(100 * (usd.loc[2025] / usd.loc[2020] - 1), 1)}
l_yen14 = np.log(net3.loc[2025] / net3.loc[2014]); l_fx14 = np.log(T.loc[2025, "usdjpy"] / T.loc[2014, "usdjpy"])
main["h2_2014_2025_fx_share_pct"] = r(100 * l_fx14 / l_yen14, 1)

# H3：受取と支払
d_pay = T.loc[2025, "3項目_支払"] - T.loc[2014, "3項目_支払"]; d_rec = T.loc[2025, "3項目_受取"] - T.loc[2014, "3項目_受取"]
d_def = net3.loc[2025] - net3.loc[2014]
main["h3"] = {"payments_tyen": [r(T.loc[2014, "3項目_支払"]), r(T.loc[2025, "3項目_支払"])], "receipts_tyen": [r(T.loc[2014, "3項目_受取"]), r(T.loc[2025, "3項目_受取"])],
              "d_payments_tyen": r(d_pay), "d_receipts_tyen": r(d_rec), "d_deficit_tyen": r(d_def), "ratio_dpay_to_ddef": r(d_pay / d_def, 2)}

# H4：地域（四半期を年に）
qy = q.groupby(["code", "year"])["value"].agg(["sum", "count"]).reset_index()
qy = qy[qy["count"] == 4]
def reg(code_region, flow="SD"):
    v = 0.0
    for it in ("95", "96"):
        s = qy[(qy.code == f"BPBP6Q{flow}{code_region}{it}")].set_index("year")["sum"]
        v = v + s
    return v / OKU_TO_CHO
regions = {"地域別合計": "", "米国": "US", "北米計": "NA", "欧州計": "EP", "EU": "EU", "アジア計": "AS"}
rt = pd.DataFrame({k: reg(v) for k, v in regions.items()})
rt_rec = pd.DataFrame({k: reg(v, "SC") for k, v in regions.items()})
rt.round(4).to_csv(R / "region_payments_annual.csv")
rt_rec.round(4).to_csv(R / "region_receipts_annual.csv")
main["us_share_payments_pct"] = {str(y): r(100 * rt.loc[y, "米国"] / rt.loc[y, "地域別合計"], 1) for y in [2014, 2019, 2025]}
main["eu_share_payments_pct"] = {str(y): r(100 * rt.loc[y, "EU"] / rt.loc[y, "地域別合計"], 1) for y in [2014, 2025]}
main["asia_share_payments_pct"] = {str(y): r(100 * rt.loc[y, "アジア計"] / rt.loc[y, "地域別合計"], 1) for y in [2014, 2025]}
main["us_net_tyen"] = {str(y): r(rt_rec.loc[y, "米国"] - rt.loc[y, "米国"]) for y in [2014, 2025]}
# 照合：四半期の地域別合計と月次の合計（知的財産権等＋通信・コンピュータ・情報、支払）
mon = (A["支払"][["コンピュータ", "情報", "通信", "著作権等使用料", "産業財産権等使用料"]].sum(axis=1))
main["check_region_total_vs_monthly_2025_tyen"] = [r(rt.loc[2025, "地域別合計"]), r(mon.loc[2025])]

# 2026年1〜9月と前年同期
def ytd(year, months=9):
    v = 0.0
    for i in DEFS["3項目"]:
        s = m[(m.code == f"BPBP6JYNSN{i}") & (m.year == year) & (m.month <= months)]["value"].sum()
        v += s
    return -v / OKU_TO_CHO
main["ytd_jan_sep"] = {"2025": r(ytd(2025)), "2026": r(ytd(2026)), "change_pct": r(100 * (ytd(2026) / ytd(2025) - 1), 1)}

main["hypotheses"] = {
    "H1": {"value": main["cagr_3_2014_2025_pct"], "verdict": "支持" if main["cagr_3_2014_2025_pct"] >= 10 else "外れ"},
    "H2": {"value": main["h2"]["fx_share_pct"], "verdict": "支持" if main["h2"]["fx_share_pct"] >= 100 / 3 else "外れ"},
    "H3": {"value": main["h3"]["ratio_dpay_to_ddef"], "verdict": "支持" if main["h3"]["ratio_dpay_to_ddef"] >= 1.5 else "外れ"},
    "H4": {"value": main["us_share_payments_pct"]["2025"], "verdict": "支持" if main["us_share_payments_pct"]["2025"] >= 50 else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=0))
