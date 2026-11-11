"""F261 分析：潜在成長率・GDP ギャップを手法ごとに出し、PLAN.md の H1〜H4 と頑健性を判定する。

出力：results/main.json、results/methods_q.csv（四半期×手法）、results/fy_pg.csv（年度×手法）、
      results/endpoint.csv（端点の比べ）、results/robustness.json
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data" / "processed", ROOT / "results"
RES.mkdir(exist_ok=True)

P = pd.read_csv(PROC / "panel_q.csv")
Q = P["quarter"].tolist()


import importlib.util

_spec = importlib.util.spec_from_file_location("zz_f261_methods", Path(__file__).resolve().parent / "zz_f261_methods.py")
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
tr_hp, tr_bk, tr_cf, tr_ham, tr_uc, tr_lin = _m.tr_hp, _m.tr_bk, _m.tr_cf, _m.tr_ham, _m.tr_uc, _m.tr_lin
stat_trends, yoy, qoq_ann4 = _m.stat_trends, _m.yoy, _m.qoq_ann4


def build(l, quarters, lam=1600, ham_h=8, growth=yoy):
    T = stat_trends(l, quarters, lam=lam, ham_h=ham_h)
    pg = pd.DataFrame({k: growth(v) for k, v in T.items()}, index=quarters)
    gap = pd.DataFrame({k: 100 * (l - v) for k, v in T.items()}, index=quarters)
    return pg, gap


def add_official(pg, gap, panel):
    d = panel.set_index("quarter")
    pg = pg.copy()
    gap = gap.copy()
    # 内閣府：前期比年率 -> 4期平均で前年比相当にそろえる
    pg["CAO"] = d["cao_pg"].rolling(4).mean().reindex(pg.index).values
    pg["BOJ"] = d["boj_pg"].reindex(pg.index).values
    gap["CAO"] = d["cao_gap"].reindex(gap.index).values
    gap["BOJ"] = d["boj_gap"].reindex(gap.index).values
    return pg, gap


def fy_mean(df, panel):
    fy = panel.set_index("quarter")["fy"].reindex(df.index)
    g = df.groupby(fy.values)
    m = g.mean()
    m[g.count() < 4] = np.nan  # 4四半期そろった年度だけ
    return m


ORDER = ["CAO", "BOJ", "HP1600", "BK", "CF", "HAM", "UC", "LIN"]

l = P["lny"].values
pg, gap = build(l, Q)
pg, gap = add_official(pg, gap, P)
pg, gap = pg[ORDER], gap[ORDER]
fy = fy_mean(pg, P)

out = pd.concat({"pg": pg, "gap": gap}, axis=1)
out.index.name = "quarter"
out.round(4).to_csv(RES / "methods_q.csv")
fy.index.name = "fy"
fy.round(4).to_csv(RES / "fy_pg.csv")

main = {}
# ---- H1：FY2025 の幅 ----
f25 = fy.loc[2025].dropna()
main["H1"] = {
    "fy2025": f25.round(3).to_dict(),
    "range": round(float(f25.max() - f25.min()), 3),
    "max": [f25.idxmax(), round(float(f25.max()), 3)],
    "min": [f25.idxmin(), round(float(f25.min()), 3)],
    "range_official_only": round(float(abs(f25["CAO"] - f25["BOJ"])), 3),
    "range_stat_only": round(float(f25.drop(["CAO", "BOJ"]).max() - f25.drop(["CAO", "BOJ"]).min()), 3),
    "verdict": "支持" if f25.max() - f25.min() >= 0.5 else ("外れ" if f25.max() - f25.min() < 0.3 else "どちらとも言えない"),
}
fyr = fy.loc[2000:2025]
rng = (fyr.max(axis=1) - fyr.min(axis=1))
main["H1"]["range_by_fy"] = rng.round(3).to_dict()
main["H1"]["range_fy_median_2000_2025"] = round(float(rng.median()), 3)
main["H1"]["range_fy_min_2000_2025"] = [int(rng.idxmin()), round(float(rng.min()), 3)]
main["H1"]["range_fy_max_2000_2025"] = [int(rng.idxmax()), round(float(rng.max()), 3)]


# ---- H2：符号の割れ ----
def sign_split(g, start="2000Q1", end="2026Q2", cols=None):
    g = g.loc[start:end] if cols is None else g.loc[start:end, cols]
    s = np.sign(g)
    ok = g.notna().sum(axis=1) >= 3
    split = ((s > 0).sum(axis=1) > 0) & ((s < 0).sum(axis=1) > 0)
    return float(split[ok].mean()), int(ok.sum()), split


share, nq, split = sign_split(gap)
share_off, _, _ = sign_split(gap, cols=["CAO", "BOJ"])
# CAO と BOJ の2つだけでの割れ（2つとも出ている四半期）
gg = gap.loc["2000Q1":"2026Q2", ["CAO", "BOJ"]].dropna()
cb_split = float((np.sign(gg.CAO) != np.sign(gg.BOJ)).mean())
corr = gap.loc["2000Q1":"2026Q2"].corr().round(3)
main["H2"] = {
    "split_share_all_methods": round(share, 3), "n_quarters": nq,
    "split_share_cao_vs_boj": round(cb_split, 3),
    "verdict": "支持" if share >= 0.2 else ("外れ" if share < 0.1 else "どちらとも言えない"),
    "gap_corr": corr.to_dict(),
    "gap_2026Q2": gap.loc["2026Q2"].round(3).to_dict(),
    "gap_sd_2000_2026": gap.loc["2000Q1":"2026Q2"].std().round(3).to_dict(),
}
# 結果を見てから足した確認（計画になし）：
#  (a) 振れの大きい Hamilton を除く、(b) Hamilton と CF を除く、
#  (c) 「はっきり割れた」＝＋0.5%超と−0.5%未満の手法が両方ある四半期だけ数える
g_ = gap.loc["2000Q1":"2026Q2"]
main["H2"]["posthoc"] = {
    "split_share_excl_HAM": round(sign_split(gap, cols=[c for c in gap.columns if c != "HAM"])[0], 3),
    "split_share_excl_HAM_CF": round(sign_split(gap, cols=[c for c in gap.columns if c not in ("HAM", "CF")])[0], 3),
    "clear_split_share_all": round(float((((g_ > 0.5).sum(axis=1) > 0) & ((g_ < -0.5).sum(axis=1) > 0)).mean()), 3),
    "clear_split_share_excl_HAM": round(float((((g_.drop(columns="HAM") > 0.5).sum(axis=1) > 0)
                                               & ((g_.drop(columns="HAM") < -0.5).sum(axis=1) > 0)).mean()), 3),
}
f25x = fy.loc[2025].drop(["HAM"]).dropna()
main["H1"]["posthoc_range_excl_HAM"] = round(float(f25x.max() - f25x.min()), 3)
# 年度ごとの Hamilton の振れ（参考）
main["H1"]["posthoc_sd_fy_2000_2025"] = fy.loc[2000:2025].std().round(3).to_dict()

# ---- H3：CAO と BOJ の差の内訳（年度、FY2010〜FY2025）----
d = P.set_index("quarter")
cao_fy = d[["cao_pg", "c_tfp", "c_capital", "c_hours", "c_employed"]].groupby(d["fy"]).mean()
cao_fy.columns = ["pg", "tfp", "capital", "hours", "employed"]
boj_fy = d[["boj_pg", "boj_c_tfp", "boj_c_capital", "boj_c_hours", "boj_c_employed"]].groupby(d["fy"]).mean()
boj_fy.columns = ["pg", "tfp", "capital", "hours", "employed"]
yrs = list(range(2010, 2026))
diff = (cao_fy.loc[yrs] - boj_fy.loc[yrs])
comp = ["tfp", "capital", "hours", "employed"]
absum = diff[comp].abs().sum()
main["H3"] = {
    "mean_diff_cao_minus_boj": diff.mean().round(3).to_dict(),
    "mean_abs_diff": diff.abs().mean().round(3).to_dict(),
    "abs_share": (absum / absum.sum()).round(3).to_dict(),
    "verdict": "支持" if absum["tfp"] / absum.sum() >= 0.5 else "外れ",
    "by_fy": diff.round(3).to_dict(orient="index"),
    "cao_fy2025": cao_fy.loc[2025].round(3).to_dict(), "boj_fy2025": boj_fy.loc[2025].round(3).to_dict(),
}
# 寄与の合計と潜在成長率の差（内閣府の丸めの影響の確認）
main["H3"]["cao_sum_check_max_abs"] = round(float((cao_fy.loc[yrs, comp].sum(axis=1) - cao_fy.loc[yrs, "pg"]).abs().max()), 3)
main["H3"]["boj_sum_check_max_abs"] = round(float((boj_fy.loc[yrs, comp].sum(axis=1) - boj_fy.loc[yrs, "pg"]).abs().max()), 3)


# ---- H4：端点 ----
# 「最新のデータ」も F50 の最新の公表回（2026年4-6月期2次）の前期比（小数1桁）から作り、丸めの条件をそろえる
VL = pd.read_csv(PROC / "vintage_levels.csv.gz")
rel = pd.read_csv(ROOT / "data" / "raw" / "f50_releases.csv")
latest = VL[VL.rid == rel.rid.iloc[-1]]
lq = latest.quarter.tolist()
ll = np.log(latest.level.values)

FUNCS = {"HP1600": lambda x, qs: tr_hp(x), "UC": lambda x, qs: tr_uc(x), "HAM": lambda x, qs: tr_ham(x),
         "CF": lambda x, qs: tr_cf(x)}
final_pg = {k: pd.Series(yoy(f(ll, lq)), index=lq) for k, f in FUNCS.items()}

# 対象：2次速報（stage 2）の公表回のうち、対象四半期が 2004Q1〜2023Q2（その後に3年分のデータがある）
sel = rel[(rel.stage == 2) & (rel.ref >= "2004Q1") & (rel.ref <= "2023Q2") & (~rel.reissue)]
rows = []
for _, r in sel.iterrows():
    e = r.ref
    k = lq.index(e)
    pseudo_l = ll[: k + 1]
    rv = VL[VL.rid == r.rid]
    real_l = np.log(rv.level.values)
    assert rv.quarter.iloc[-1] == e
    for name, f in FUNCS.items():
        ps = yoy(f(pseudo_l, lq[: k + 1]))[-1]
        rt = yoy(f(real_l, rv.quarter.tolist()))[-1]
        rows.append({"ref": e, "method": name, "final": final_pg[name][e], "pseudo": ps, "real": rt})
EP = pd.DataFrame(rows)
EP["endpoint"] = EP.pseudo - EP.final  # 端点だけの違い
EP["revision"] = EP.real - EP.pseudo  # データの改定による違い
EP["total"] = EP.real - EP.final
EP.round(4).to_csv(RES / "endpoint.csv", index=False)
h4 = {}
for name, g in EP.groupby("method"):
    h4[name] = {
        "n": int(len(g)),
        "mad_pseudo_vs_final": round(float(g.endpoint.abs().mean()), 3),
        "mad_real_vs_final": round(float(g.total.abs().mean()), 3),
        "mad_revision_only": round(float(g.revision.abs().mean()), 3),
        "mean_pseudo_minus_final": round(float(g.endpoint.mean()), 3),
        "mean_real_minus_final": round(float(g.total.mean()), 3),
        "share_abs_gt_0.5_real": round(float((g.total.abs() > 0.5).mean()), 3),
        "max_abs_real": round(float(g.total.abs().max()), 3),
    }
hp = h4["HP1600"]
main["H4"] = {
    "by_method": h4,
    "verdict": ("支持" if hp["mad_pseudo_vs_final"] >= 0.3 and hp["mad_real_vs_final"] > hp["mad_pseudo_vs_final"]
                else ("外れ" if hp["mad_pseudo_vs_final"] < 0.15 or hp["mad_real_vs_final"] < hp["mad_pseudo_vs_final"]
                      else "どちらとも言えない")),
    "note": "対象は2次速報の公表回、対象四半期 2004Q1〜2023Q2。最新のデータも公表回の前期比（小数1桁）から作り、丸めをそろえた",
}
# 最新の値（丸めあり系列）と本来の水準系列の HP の違い（丸めの影響の確認）
hp_true = pd.Series(yoy(tr_hp(l)), index=Q)
main["H4"]["rounding_check_mad_hp"] = round(float((final_pg["HP1600"] - hp_true.reindex(lq)).loc["1996Q1":].abs().mean()), 4)

(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=float))

# ---------- 頑健性 ----------
rob = {}


def summary(pg_, gap_, label):
    pg_, gap_ = add_official(pg_, gap_, P)
    f = fy_mean(pg_, P).loc[2025].dropna()
    s, _, _ = sign_split(gap_)
    return {"label": label, "fy2025": f.round(3).to_dict(), "range": round(float(f.max() - f.min()), 3),
            "split_share": round(s, 3)}


# 1. λ
for lam in (400, 6400):
    pg_, gap_ = build(l, Q, lam=lam)
    r = summary(pg_, gap_, f"HP λ={lam}（ほかは同じ）")
    hp_ep = []
    for e in EP.ref.unique():
        k = lq.index(e)
        hp_ep.append(abs(yoy(tr_hp(ll[: k + 1], lam))[-1] - yoy(tr_hp(ll, lam))[k]))
    r["hp_endpoint_mad"] = round(float(np.mean(hp_ep)), 3)
    rob[f"lambda_{lam}"] = r
# 2. コロナ期をならす
lc = pd.Series(l.copy(), index=Q)
lc.loc["2020Q2":"2020Q4"] = np.nan
lc = lc.interpolate().values
pg_, gap_ = build(lc, Q)
rob["covid_smoothed"] = summary(pg_, gap_, "2020Q2〜Q4 を線でならす")
# 3. 定義：前期比年率の4期平均
pg_, gap_ = build(l, Q, growth=qoq_ann4)
rob["qoq_ann4"] = summary(pg_, gap_, "潜在成長率＝前期比年率の4期平均")
# 4. 開始 2000年
k0 = Q.index("2000Q1")
pg_, gap_ = build(l[k0:], Q[k0:])
pg_ = pg_.reindex(Q)
gap_ = gap_.reindex(Q)
rob["start_2000"] = summary(pg_, gap_, "推計の開始を2000Q1に")
# 5. Hamilton h=12
pg_, gap_ = build(l, Q, ham_h=12)
r = summary(pg_, gap_, "Hamilton h=12")
rob["ham_h12"] = r
(RES / "robustness.json").write_text(json.dumps(rob, ensure_ascii=False, indent=1, default=float))
print(json.dumps({k: (v["verdict"] if isinstance(v, dict) and "verdict" in v else None) for k, v in main.items()}, ensure_ascii=False))
print("H1", main["H1"]["fy2025"], main["H1"]["range"])
print("H2", main["H2"]["split_share_all_methods"], main["H2"]["split_share_cao_vs_boj"])
print("H3", main["H3"]["mean_diff_cao_minus_boj"], main["H3"]["abs_share"])
print("H4", {k: (v["mad_pseudo_vs_final"], v["mad_real_vs_final"], v["mad_revision_only"]) for k, v in h4.items()})
for k, v in rob.items():
    print(k, v["range"], v["split_share"], v.get("hp_endpoint_mad"), v["fy2025"])
