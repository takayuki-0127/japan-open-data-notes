"""主な分析：移出入（純）の県内総生産比を県ごとに出し、産業の割合との関係を見る。仮説と頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "pref_year.csv", dtype={"code": str})
IND = ["agri", "mining", "manuf", "utility", "constr", "trade", "transport", "accom", "ict", "finance", "realestate", "prof", "public", "educ", "othsvc_b", "othsvc"]
for c in IND:
    d[f"{c}_sh"] = 100 * d[c] / d.gdp
d["pubedu_sh"] = d.public_sh + d.educ_sh  # 公務＋教育
d["nx"] = 100 * d.netexp / d.gdp_exp          # 移出入（純）÷県内総生産（%）
d["nx_sum"] = 100 * d.netexp_sum / d.gdp_exp  # （移出入＋統計上の不突合）÷県内総生産
REGION = {"北海道・東北": range(1, 8), "関東": range(8, 15), "中部": range(15, 24), "近畿": range(24, 31), "中国": range(31, 36), "四国": range(36, 40), "九州・沖縄": range(40, 48)}
d["region"] = d.code.astype(int).map({c: k for k, v in REGION.items() for c in v})
d.to_csv(R / "pref_year_ratio.csv", index=False, float_format="%.4f")


def r(x, k=2):
    return round(float(x), k)


def period(y0, y1):
    g = d[(d.year >= y0) & (d.year <= y1)]
    cols = ["nx", "nx_sum", "pubedu_sh"] + [f"{c}_sh" for c in IND]
    p = g.groupby(["code", "pref", "region"], as_index=False)[cols].mean()
    return p.sort_values("code").reset_index(drop=True)


P = period(2019, 2023); E = period(2011, 2013); L = period(2021, 2023)
P.to_csv(R / "pref_2019_2023.csv", index=False, float_format="%.3f")
ex_tokyo = P[P.pref != "東京都"]
rp = stats.pearsonr(P.manuf_sh, P.nx)[0]
rp_ex = stats.pearsonr(ex_tokyo.manuf_sh, ex_tokyo.nx)[0]
rg = stats.pearsonr(P.pubedu_sh, P.nx)[0]
b, a = np.polyfit(ex_tokyo.manuf_sh, ex_tokyo.nx, 1)
n_pos = int((P.nx > 0).sum()); n_pos_E = int((E.nx > 0).sum()); n_pos_L = int((L.nx > 0).sum())
hyp = {
    "H1": {"n_positive_2019_2023": n_pos, "verdict": "支持" if n_pos < 24 else "外れ"},
    "H2": {"r_manuf": r(rp, 3), "verdict": "支持" if rp >= 0.5 else "外れ"},
    "H3": {"r_public_educ": r(rg, 3), "verdict": "支持" if rg <= -0.3 else "外れ"},
    "H4": {"n_positive_2011_2013": n_pos_E, "n_positive_2021_2023": n_pos_L, "verdict": "支持" if n_pos_L - n_pos_E < 3 else "外れ"},
}
y23 = d[d.year == 2023]
rob = [
    {"check": "本線：製造業の割合と移出入比の相関（2019〜2023年度の平均、47県）", "value": r(rp, 3)},
    {"check": "東京都を除く（46県）", "value": r(rp_ex, 3)},
    {"check": "移出入＋統計上の不突合で（47県）", "value": r(stats.pearsonr(P.manuf_sh, P.nx_sum)[0], 3)},
    {"check": "2023年度だけ（47県）", "value": r(stats.pearsonr(y23.manuf_sh, y23.nx)[0], 3)},
    {"check": "2011〜2013年度の平均（47県）", "value": r(stats.pearsonr(E.manuf_sh, E.nx)[0], 3)},
    {"check": "順位の相関（スピアマン、47県）", "value": r(stats.spearmanr(P.manuf_sh, P.nx)[0], 3)},
    {"check": "公務＋教育の割合との相関：本線", "value": r(rg, 3)},
    {"check": "公務＋教育の割合との相関：東京都を除く", "value": r(stats.pearsonr(ex_tokyo.pubedu_sh, ex_tokyo.nx)[0], 3)},
    {"check": "公務＋教育の割合との相関：移出入＋不突合で", "value": r(stats.pearsonr(P.pubedu_sh, P.nx_sum)[0], 3)},
    {"check": "黒字の県の数：移出入＋不突合で（2019〜2023年度）", "value": int((P.nx_sum > 0).sum())},
    {"check": "黒字の県の数：2023年度だけ", "value": int((y23.nx > 0).sum())},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
# 地方ブロック別（県内総生産で重みをつけた比）
g = d[(d.year >= 2019) & (d.year <= 2023)].groupby("region")[["netexp", "gdp_exp"]].sum()
reg = (100 * g.netexp / g.gdp_exp).reindex(list(REGION)).round(2)
reg.to_csv(R / "region_2019_2023.csv", header=["nx_pct"])
# 全国の移出入の和（海外との純輸出に近い）
nat = d.groupby("year")[["netexp", "gdp_exp"]].sum()
nat["nx_pct"] = 100 * nat.netexp / nat.gdp_exp
nat.round(3).to_csv(R / "national_by_year.csv")
persist = stats.pearsonr(E.nx, L.nx)[0]
tok = P[P.pref == "東京都"].iloc[0]
main = {
    "period": "2019〜2023年度の平均", "n_positive": n_pos, "positive_prefs": P[P.nx > 0].pref.tolist(),
    "tokyo_nx": r(tok.nx), "tokyo_netexp_trillion_2023": r(y23[y23.pref == "東京都"].netexp.iloc[0] / 1e6, 1),
    "median_nx": r(P.nx.median()), "nx_range_ex_tokyo": [r(ex_tokyo.nx.min()), r(ex_tokyo.nx.max())],
    "slope_manuf_ex_tokyo": r(b, 3), "r_manuf": r(rp, 3), "r_manuf_ex_tokyo": r(rp_ex, 3), "r_public_educ": r(rg, 3),
    "manuf_median_pos": r(P[P.nx > 0].manuf_sh.median(), 1), "manuf_median_neg": r(P[P.nx <= 0].manuf_sh.median(), 1),
    "pubedu_median_pos": r(P[P.nx > 0].pubedu_sh.median(), 1), "pubedu_median_neg": r(P[P.nx <= 0].pubedu_sh.median(), 1),
    "persistence_r_2011_13_vs_2021_23": r(persist, 3),
    "n_switch": int(((E.nx > 0) != (L.nx > 0)).sum()),
    "switch_to_positive": E[(E.nx <= 0) & (L.nx > 0)].pref.tolist(), "switch_to_negative": E[(E.nx > 0) & (L.nx <= 0)].pref.tolist(),
    "national_nx_pct": {str(k): r(v) for k, v in nat.nx_pct.items()},
    "region_nx_pct": {k: float(v) for k, v in reg.items()},
    "hypotheses": hyp,
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=1)); print(pd.DataFrame(rob).to_string())
print(P[["pref", "nx", "nx_sum", "manuf_sh", "pubedu_sh"]].round(1).to_string())
