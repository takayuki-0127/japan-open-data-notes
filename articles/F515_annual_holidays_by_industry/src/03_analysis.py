"""主な分析：産業別の労働者1人平均年間休日の推移、産業間の差（範囲・標準偏差）、多い3産業・少ない3産業、企業規模、仮説、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "holidays.csv")
ind = d[(d.kind == "industry") & (d.year >= 2009)]
w = ind.pivot(index="year", columns="code", values="mean_days")
s120 = ind.pivot(index="year", columns="code", values="share_120plus")
names = ind.drop_duplicates("code", keep="last").set_index("code").name
CODES = [c for c in w.columns if w[c].notna().all()]  # 2009年から毎年ある産業（Q 複合サービス事業を除く）
w.round(2).to_csv(R / "industry_mean_days.csv")
Y0, Y1 = 2009, int(w.index.max())


def r(x, k=1):
    return round(float(x), k)


def spread(tab, codes):
    t = tab[codes]
    return pd.DataFrame({"range": t.max(axis=1) - t.min(axis=1), "sd": t.std(axis=1, ddof=0)})


sp = spread(w, CODES)
sp.round(3).to_csv(R / "spread_by_year.csv")
base = w.loc[Y0, CODES]
low3 = list(base.nsmallest(3).index)
high3 = list(base.nlargest(3).index)
ch = (w.loc[Y1, CODES] - w.loc[Y0, CODES])
low_inc = float(ch[low3].mean()); high_inc = float(ch[high3].mean())
size = d[d.kind.isin(["size", "total"])].pivot(index="year", columns="code", values="mean_days")
size.to_csv(R / "size_mean_days.csv")
gap_size = size["1000+"] - size["30-99"]

hyp = {
    "H1": {"range_2009": r(sp.range[Y0]), "range_last": r(sp.range[Y1]), "verdict": "支持" if sp.range[Y1] < sp.range[Y0] else "外れ"},
    "H2": {"sd_2009": r(sp.sd[Y0], 2), "sd_2017": r(sp.sd[2017], 2), "sd_last": r(sp.sd[Y1], 2),
           "verdict": "支持" if (sp.sd[2017] < sp.sd[Y0] and sp.sd[Y1] < sp.sd[2017]) else "外れ"},
    "H3": {"low3": low3, "high3": high3, "low3_increase": r(low_inc), "high3_increase": r(high_inc),
           "verdict": "支持" if high_inc <= low_inc / 2 else "外れ"},
    "H4": {"gap_2009": r(gap_size[Y0]), "gap_last": r(gap_size[Y1]), "verdict": "支持" if gap_size[Y1] < gap_size[Y0] else "外れ"},
}

# 頑健性
rob = []


def add(lab, tab, codes, y0=Y0, y1=Y1):
    s_ = spread(tab, codes)
    rob.append({"check": lab, "period": f"{y0}→{y1}", "range0": r(s_.range[y0]), "range1": r(s_.range[y1]),
                "sd0": r(s_.sd[y0], 2), "sd1": r(s_.sd[y1], 2)})


add("本線：15産業、労働者1人平均の休日", w, CODES)
add("鉱業を除く14産業", w, [c for c in CODES if c != "C"])
add("2025年を除く（2009→2024）", w, CODES, Y0, 2024)
m3 = w[CODES].rolling(3).mean()
add("3年平均（2009〜11年→2023〜25年）", m3.dropna().rename(index=lambda y: y), CODES, 2011, Y1)
add("120日以上の労働者の割合（%）", s120, CODES)
qcodes = CODES + (["Q"] if "Q" in w.columns else [])
add("複合サービス事業を含む16産業（2015→2025）", w, qcodes, 2015, Y1)
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)

main = {
    "years": [Y0, Y1], "codes": CODES, "names": {c: names[c] for c in w.columns},
    "industry_2009": {c: r(w.loc[Y0, c]) for c in CODES}, "industry_last": {c: r(w.loc[Y1, c]) for c in CODES},
    "industry_2024": {c: r(w.loc[2024, c]) for c in CODES},
    "change_2009_last": {c: r(ch[c]) for c in CODES},
    "max_2009": {"code": str(base.idxmax()), "value": r(base.max())}, "min_2009": {"code": str(base.idxmin()), "value": r(base.min())},
    "max_last": {"code": str(w.loc[Y1, CODES].idxmax()), "value": r(w.loc[Y1, CODES].max())},
    "min_last": {"code": str(w.loc[Y1, CODES].idxmin()), "value": r(w.loc[Y1, CODES].min())},
    "total": {int(y): r(size.loc[y, "T"]) for y in size.index},
    "size_2009": {c: r(size.loc[Y0, c]) for c in ["1000+", "300-999", "100-299", "30-99"]},
    "size_last": {c: r(size.loc[Y1, c]) for c in ["1000+", "300-999", "100-299", "30-99"]},
    "size_gap": {int(y): r(v) for y, v in gap_size.items()},
    "total_jump_2024_2025": r(size.loc[Y1, "T"] - size.loc[2024, "T"]),
    "spread": {int(y): {"range": r(sp.range[y]), "sd": r(sp.sd[y], 2)} for y in sp.index},
    "hypotheses": hyp,
    "note": "労働者1人平均年間休日総数（日）。企業で最も多くの労働者に適用される年間休日を労働者数で加重平均した値。調査は各年1月1日現在。2022年は表の形が違う。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(hyp, ensure_ascii=False)); print(pd.read_csv(R / "robustness.csv").to_string()); print(sp.round(2).T)
print(main["change_2009_last"])
