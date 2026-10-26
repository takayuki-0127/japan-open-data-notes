"""03 分析：素の SMR → BYM2（PyMC）→ 共変量つき → 公表のベイズ推定値との比較 → 頑健性
使い方：python 03_分析.py [main|all]（main は本体3本だけ、all は頑健性も）"""
import json
import sys
import time
import numpy as np
import pandas as pd
import arviz as az
from scipy import stats
from common import DATA, RES, SEED, load_topo, to_km
from bym2 import fit, connect

rng = np.random.default_rng(SEED)
df = pd.read_csv(DATA / "smr_2018_22.csv", dtype={"code": str, "pref": str}).set_index("code")
df = df[df["E_all"].notna()]
rings, used = load_topo()
df = df[df.index.isin(rings.keys())]
codes = list(df.index)
n = len(codes)
cent = np.array([np.vstack(rings[c]).mean(axis=0) for c in codes])
P = np.c_[to_km(cent[:, 0], cent[:, 1])]


def queen():
    owner = {}
    for i, c in enumerate(codes):
        for a in used[c]:
            owner.setdefault(a, set()).add(i)
    A = np.zeros((n, n))
    for s in owner.values():
        for i in s:
            for j in s:
                if i != j:
                    A[i, j] = 1
    isl = 0
    for i in range(n):  # 島などで接する区域がない → いちばん近い1区域
        if A[i].sum() == 0:
            dd = np.hypot(*(P - P[i]).T)
            dd[i] = np.inf
            j = int(np.argmin(dd))
            A[i, j] = A[j, i] = 1
            isl += 1
    A, added = connect(A, P)
    return A, isl, added


def knn(k=6):
    A = np.zeros((n, n))
    for i in range(n):
        dd = np.hypot(*(P - P[i]).T)
        dd[i] = np.inf
        for j in np.argsort(dd)[:k]:
            A[i, j] = A[j, i] = 1
    A, added = connect(A, P)
    return A, 0, added


A_q, n_isl, n_add = queen()
print(f"区域 {n}、隣の数の中央値 {np.median(A_q.sum(1)):.0f}、島を最寄りと結んだ {n_isl}、塊どうしを結んだ {n_add}")

# 共変量（F20 と同じ社会・人口統計体系の値。政令市の区の所得は市の値）
cov = pd.read_csv(DATA / "covariates_2018_22.csv", dtype={"code": str}).set_index("code")
XV = {"income": "納税者1人あたり所得（対数）", "density": "可住地の人口密度（対数）",
      "tertiary": "第3次産業就業者の割合", "unmarried": "未婚者の割合"}


def Xmat(idx):
    X = cov.reindex(idx)[list(XV)]
    X = X.fillna(X.median())
    return ((X - X.mean()) / X.std()).values


def q(x):
    v = np.asarray(x).ravel()
    return [float(v.mean()), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def summarize(tag, idata, s, idx, O, E, extra=None):
    post = idata.posterior
    th = post["theta"].stack(z=("chain", "draw")).values * 100
    sp = post["spatial"].stack(z=("chain", "draw")).values
    ii = post["iid"].stack(z=("chain", "draw")).values
    rhat = float(az.rhat(idata, var_names=["theta"])["theta"].max())
    ess = float(az.ess(idata, var_names=["theta"])["theta"].min())
    out = pd.DataFrame({"code": idx, "O": O, "E": E, "smr_raw": O / E * 100,
                        "smr_bym2": th.mean(1), "lo": np.percentile(th, 2.5, 1), "hi": np.percentile(th, 97.5, 1),
                        "p_above": (th > 100).mean(1), "spatial": sp.mean(1), "iid": ii.mean(1)}).set_index("code")
    out.to_csv(RES / f"theta_{tag}.csv", encoding="utf-8")
    r = {"tag": tag, "n": len(idx), "scale_factor": s,
         "sigma": q(post["sigma"]), "rho": q(post["rho"]), "alpha": q(post["alpha"]),
         "rhat_max_all": float(max(float(az.rhat(idata, var_names=[v])[v].max()) for v in ["alpha", "sigma", "rho"])), "rhat_max_theta": rhat, "ess_min_theta": ess,
         "sd_log_raw": float(np.log(out["smr_raw"].clip(lower=1)).std()),
         "sd_log_bym2": float(np.log(out["smr_bym2"]).std()),
         "range_raw": [float(out["smr_raw"].min()), float(out["smr_raw"].max())],
         "range_bym2": [float(out["smr_bym2"].min()), float(out["smr_bym2"].max())],
         "share_ci_excl_100": float(((out["lo"] > 100) | (out["hi"] < 100)).mean())}
    if "beta" in post:
        b = post["beta"].stack(z=("chain", "draw")).values
        r["beta"] = {k: [float(b[i].mean()), float(np.percentile(b[i], 2.5)), float(np.percentile(b[i], 97.5))]
                     for i, k in enumerate(XV)}
    if extra:
        r.update(extra)
    return r


def run(tag, cause="all", sex="", A=None, prior="pc", X=False, draws=1000):
    t = time.time()
    sfx = f"_{cause}" + (f"_{sex}" if sex else "")
    d = df[[f"O{sfx}", f"E{sfx}"]].dropna()
    d = d[d[f"E{sfx}"] > 0]
    keep = [codes.index(c) for c in d.index]
    A0 = (A_q if A is None else A)[np.ix_(keep, keep)]
    A0, added = connect(A0, P[keep])
    O, E = d[f"O{sfx}"].values, d[f"E{sfx}"].values
    idata, s = fit(O, E, A0, X=Xmat(d.index) if X else None, prior=prior, draws=draws)
    r = summarize(tag, idata, s, list(d.index), O, E, {"cause": cause, "sex": sex or "both", "prior": prior,
                                                       "covariates": bool(X), "minutes": round((time.time() - t) / 60, 1)})
    print(tag, {k: r[k] for k in ["n", "sigma", "rho", "rhat_max_all", "rhat_max_theta", "ess_min_theta", "minutes"]}, flush=True)
    return r


mode = sys.argv[1] if len(sys.argv) > 1 else "all"
results = {}
f = RES / "fits.json"
if f.exists():
    results = json.load(open(f, encoding="utf-8"))


def save(r):
    results[r["tag"]] = r
    json.dump(results, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


jobs = [("main", dict()), ("covariates", dict(X=True)), ("male", dict(sex="m")), ("female", dict(sex="f"))]
if mode == "all":
    A_k, _, _ = knn(6)
    jobs += [("prior_wide", dict(prior="wide")), ("knn6", dict(A=A_k)), ("cancer", dict(cause="cancer")),
             ("heart", dict(cause="heart")), ("stroke", dict(cause="stroke"))]
for tag, kw in jobs:
    if tag in results and mode != "force":
        continue
    save(run(tag, **kw))

# 公表のベイズ推定値（第5表、男女別）との比較
cmp = {}
for sex, tag in [("m", "male"), ("f", "female")]:
    t = pd.read_csv(RES / f"theta_{tag}.csv", dtype={"code": str}).set_index("code")
    b = df.loc[t.index, f"bayes_all_{sex}"]
    ok = b.notna()
    cmp[tag] = {"n": int(ok.sum()), "corr": float(np.corrcoef(t["smr_bym2"][ok], b[ok])[0, 1]),
                "corr_raw": float(np.corrcoef(t["smr_raw"][ok], b[ok])[0, 1]),
                "mad": float(np.median(np.abs(t["smr_bym2"][ok] - b[ok]))),
                "sd_bym2": float(t["smr_bym2"][ok].std()), "sd_pub": float(b[ok].std()), "sd_raw": float(t["smr_raw"][ok].std())}
json.dump(cmp, open(RES / "compare_published.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(cmp)

# 期待死亡数の大きさ別に、素の SMR と BYM2 の差
t = pd.read_csv(RES / "theta_main.csv", dtype={"code": str}).set_index("code")
bins = [0, 100, 300, 1000, 3000, 10000, 1e9]
lab = ["100未満", "100〜300", "300〜1000", "1000〜3000", "3000〜1万", "1万以上"]
t["Ebin"] = pd.cut(t["E"], bins, labels=lab, right=False)
g = t.groupby("Ebin", observed=False).apply(lambda x: pd.Series({
    "区域数": len(x), "素のSMRの標準偏差": x["smr_raw"].std(), "BYM2の標準偏差": x["smr_bym2"].std(),
    "動いた幅の中央値": (x["smr_bym2"] - x["smr_raw"]).abs().median(),
    "95%区間の幅の中央値": (x["hi"] - x["lo"]).median()}))
g.round(2).to_csv(RES / "by_size.csv", encoding="utf-8")
print(g.round(2))

# ファネル：期待死亡数ごとに「偶然だけ」の 99.8% 範囲の外にある区域の割合
z = stats.norm.ppf(0.999)
lo = 100 * (1 - z / np.sqrt(t["E"]))
hi = 100 * (1 + z / np.sqrt(t["E"]))
out_share = float(((t["smr_raw"] < lo) | (t["smr_raw"] > hi)).mean())
# 上位・下位 50 の区域のうち、期待死亡数が 300 未満の区域の数
top = {}
for col in ["smr_raw", "smr_bym2"]:
    s = t.sort_values(col)
    top[col] = {"top50_smallE": int((s.tail(50)["E"] < 300).sum()), "bottom50_smallE": int((s.head(50)["E"] < 300).sum())}
extra = {"funnel_out_share": out_share, "n_smallE_lt300": int((t["E"] < 300).sum()), "n": len(t), "top_bottom": top,
         "corr_raw_bym2": float(np.corrcoef(t["smr_raw"], t["smr_bym2"])[0, 1])}
json.dump(extra, open(RES / "funnel_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(extra)
