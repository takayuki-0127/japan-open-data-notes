"""PLAN の仮説 H1〜H5 と頑健性を計算し、results/ に書く。"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)
s = pd.read_csv(os.path.join(DATA, "summer.csv"), index_col=0)
REG = ["北日本", "東日本", "西日本", "沖縄・奄美"]
r2 = lambda x: float(round(float(x), 2))
r3 = lambda x: float(round(float(x), 3))
NPERM = 10000


def detrend_lin(y):
    x = y.index.values.astype(float)
    b = np.polyfit(x, y.values, 1)
    return y - np.polyval(b, x)


def detrend_ma(y, half=15):
    """前後15年（端は使える年だけ）の移動平均を引く。"""
    return y - y.rolling(2 * half + 1, center=True, min_periods=half + 1).mean()


def perm_p(a, b, seed):
    """平均の差（a − b）の並べ替え検定（両側）。"""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b]); na = len(a)
    cnt = 0
    for _ in range(NPERM):
        rng.shuffle(pool)
        if abs(pool[:na].mean() - pool[na:].mean()) >= abs(obs) - 1e-12:
            cnt += 1
    return (cnt + 1) / (NPERM + 1)


def compare(resid, el, la, seed):
    neu = (el == 0) & (la == 0)
    d_el = resid[el == 1].mean() - resid[neu].mean()
    d_la = resid[la == 1].mean() - resid[neu].mean()
    return {"n_el": int(el.sum()), "n_la": int(la.sum()), "n_neu": int(neu.sum()),
            "mean_el": r3(resid[el == 1].mean()), "mean_la": r3(resid[la == 1].mean()), "mean_neu": r3(resid[neu].mean()),
            "diff_el_neu": r3(d_el), "p_el": r3(perm_p(resid[el == 1], resid[neu], seed)),
            "diff_la_neu": r3(d_la), "p_la": r3(perm_p(resid[la == 1], resid[neu], seed + 1))}


R = {}
el, la = s["elnino_summer"], s["lanina_summer"]
res_jp = detrend_lin(s["jp_jja"])
trend = np.polyfit(s.index.values.astype(float), s["jp_jja"].values, 1)[0]
R["trend_jp_jja_per_decade"] = r3(trend * 10)
R["sd_resid_jp"] = r3(res_jp.std(ddof=1))
R["n_summers"] = int(len(s))
R["elnino_summers"] = [int(y) for y in s.index[el == 1]]
R["lanina_summers"] = [int(y) for y in s.index[la == 1]]

# ---- H1
c = compare(res_jp, el, la, 1)
R["H1"] = {**c, "threshold": -0.2, "result": "支持" if c["diff_el_neu"] <= -0.2 else "外れ"}

# ---- H2：地方ごと
reg = {}
for i, rg in enumerate(REG):
    rr = detrend_lin(s[f"{rg}_jja"])
    reg[rg] = compare(rr, el, la, 10 + i)
    reg[rg]["sd_resid"] = r3(rr.std(ddof=1))
most = min(REG, key=lambda k: reg[k]["diff_el_neu"])
R["H2"] = {"by_region": reg, "most_negative": most, "result": "支持" if most == "北日本" else "外れ"}

# ---- H3：相関
z = pd.DataFrame({"r": res_jp, "n3": detrend_lin(s["nino3_jja"])})
pr = stats.pearsonr(z["n3"], z["r"])
pr_raw = stats.pearsonr(s["nino3_jja"], res_jp)
sl = stats.linregress(s["nino3_jja"], res_jp).slope
R["H3"] = {"r": r3(pr.statistic), "p": r3(pr.pvalue), "r_nino3_not_detrended": r3(pr_raw.statistic),
           "slope_degC_per_1degC_nino3": r3(sl), "threshold": -0.2,
           "result": "支持" if pr.statistic <= -0.2 else "外れ",
           "by_region_r": {rg: r3(stats.pearsonr(s["nino3_jja"], detrend_lin(s[f"{rg}_jja"])).statistic) for rg in REG}}

# ---- H4：冷夏の割合
q1 = res_jp.quantile(1 / 3)
cool = res_jp <= q1
neu = (el == 0) & (la == 0)
R["H4"] = {"cool_threshold_resid": r3(q1), "n_cool": int(cool.sum()),
           "share_cool_in_el": r3(cool[el == 1].mean()), "share_cool_in_neu": r3(cool[neu].mean()),
           "share_cool_in_la": r3(cool[la == 1].mean()),
           "share_hot_in_el": r3((res_jp >= res_jp.quantile(2 / 3))[el == 1].mean()),
           "n_cool_el": int((cool & (el == 1)).sum()), "n_el": int(el.sum()),
           "result": "支持" if cool[el == 1].mean() >= 0.5 else "外れ"}
# 2×2 の正確検定（エルニーニョかどうか × 冷夏かどうか）
tab = [[int((cool & (el == 1)).sum()), int((~cool & (el == 1)).sum())],
       [int((cool & (el == 0)).sum()), int((~cool & (el == 0)).sum())]]
R["H4"]["fisher_p"] = r3(stats.fisher_exact(tab).pvalue)
R["H4"]["table_el_cool"] = tab

# ---- H5
R["H5"] = {"diff_la_neu": c["diff_la_neu"], "p": c["p_la"], "threshold": 0.1,
           "result": "支持" if c["diff_la_neu"] >= 0.1 else "外れ"}

# ---- 頑健性
rob = []
def add(label, resid, el_, la_, seed, note=""):
    cc = compare(resid, el_, la_, seed)
    q = resid.quantile(1 / 3)
    rob.append({"check": label, "n_el": cc["n_el"], "n_la": cc["n_la"], "n_neu": cc["n_neu"],
                "diff_el_neu": cc["diff_el_neu"], "p_el": cc["p_el"], "diff_la_neu": cc["diff_la_neu"], "p_la": cc["p_la"],
                "share_cool_in_el": r3((resid <= q)[el_ == 1].mean()), "note": note})
add("本線（気象庁の発生期間、直線を除く、1949〜2025年）", res_jp, el, la, 100)
el_n = (s["nino3_jja"] >= 0.5).astype(int); la_n = (s["nino3_jja"] <= -0.5).astype(int)
add("6〜8月の NINO.3 が ±0.5℃ 以上で決める", res_jp, el_n, la_n, 101)
s79 = s.loc[1979:]
add("1979年以降", detrend_lin(s79["jp_jja"]), s79["elnino_summer"], s79["lanina_summer"], 102)
add("前後15年の移動平均を除く", detrend_ma(s["jp_jja"]), el, la, 103)
reg_mean = s[[f"{rg}_jja" for rg in REG]].mean(axis=1)
add("15地点平均ではなく4地方の平均", detrend_lin(reg_mean), el, la, 104)
rb = pd.DataFrame(rob)
rb.to_csv(os.path.join(RES, "robustness.csv"), index=False)
R["robust"] = rob

# 年ごとの表（図用）
out = s[["jp_jja", "nino3_jja", "elnino_summer", "lanina_summer", "elnino_prev_winter"]].copy()
out["jp_resid"] = res_jp
for rg in REG:
    out[f"{rg}_resid"] = detrend_lin(s[f"{rg}_jja"])
out["cool"] = cool.astype(int)
out.round(3).to_csv(os.path.join(RES, "summer_table.csv"))
pd.DataFrame([{"region": rg, **reg[rg]} for rg in REG]).to_csv(os.path.join(RES, "region_compare.csv"), index=False)

with open(os.path.join(RES, "main.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in R.items() if k != "robust"}, ensure_ascii=False, indent=1))
print(rb.to_string())
