"""インフルエンザの流行が、どの県からどの県へ広がるかを調べる。

1. シーズンごとに、各都道府県の「流行開始週」（第40週以降で、定点当たり1.0以上が2週続いた最初の週）を出す
2. 開始の順番が、シーズンをまたいで同じか（順位相関・Kendall の W）
3. 開始週が地図の上で固まっているか（Moran's I、隣接の重み、並べ替え検定）
4. 時空間の自己回帰：その県の先週の値に加えて、「隣の県の先週の値」「人の行き来が多い県の先週の値」が
   今週の値を説明するか。シーズン×週の固定効果で全国の波を取り除いたうえで推定する
5. 1週先の予測：隣の県の情報を足すと、流行の立ち上がりの予測がよくなるか（1シーズン抜きの検証）
6. 頑健性：開始の閾値（0.5・2.0）、重み（隣接・移動・距離）、沖縄を除く、コロナ後のシーズン
"""
import json, itertools
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
MAIN = [f"{y}/{str(y + 1)[-2:]}" for y in range(2012, 2020)]      # 2012/13〜2019/20
RECENT = ["2022/23", "2023/24", "2024/25", "2025/26"]
START = 4   # 第40週


def rownorm(W):
    s = W.sum(1, keepdims=True)
    s[s == 0] = 1
    return W / s


def load():
    df = pd.read_csv(DATA / "flu_weekly_pref.csv")
    A = np.load(DATA / "W_adj.npy"); M = np.load(DATA / "W_mig.npy"); D = np.load(DATA / "D_km.npy")
    # 島（沖縄）など隣接のない県は、いちばん近い県とつなぐ
    for i in range(47):
        if A[i].sum() == 0:
            j = np.argsort(D[i])[1]
            A[i, j] = A[j, i] = 1
    Dinv = np.where(D > 0, 1 / np.maximum(D, 1) ** 2, 0)
    return df, A, M, Dinv, D


def wide(df, season, col="per"):
    s = df[df["season"] == season].pivot(index="sw", columns="pcode", values=col).sort_index()
    return s.reindex(columns=range(1, 48))


def onset_weeks(df, seasons, thr=1.0):
    out = {}
    for s in seasons:
        w = wide(df, s)
        on = {}
        for p in range(1, 48):
            x = w[p].values
            ix = w.index.values
            # 第40週（sw=4）以降で、2週続けて閾値以上になった最初の週。前のシーズンからの持ち越しや夏の小流行を除くため
            ok = [t for t in range(len(x) - 1) if ix[t] >= START and x[t] >= thr and x[t + 1] >= thr]
            on[p] = ix[ok[0]] if ok else np.nan
        out[s] = on
    return pd.DataFrame(out)


def morans_i(x, W, nperm=999):
    ok = ~np.isnan(x)
    x = x[ok]; W = W[np.ix_(ok, ok)]
    W = rownorm(W)
    z = x - x.mean()
    I = len(x) / W.sum() * (z @ W @ z) / (z @ z)
    sims = []
    for _ in range(nperm):
        zp = rng.permutation(z)
        sims.append(len(x) / W.sum() * (zp @ W @ zp) / (zp @ zp))
    p = (np.sum(np.array(sims) >= I) + 1) / (nperm + 1)
    return I, p


def panel(df, seasons, Ws):
    """y = log(1+定当)。先週の自分、先週の重み付き近隣を作る。"""
    rows = []
    for s in seasons:
        w = wide(df, s).ffill().fillna(0)
        Y = np.log1p(w.values)            # 週 × 47
        lagW = {k: Y @ rownorm(W).T for k, W in Ws.items()}
        for t in range(2, Y.shape[0]):
            for i in range(47):
                r = {"season": s, "sw": w.index[t], "pcode": i + 1, "y": Y[t, i], "y1": Y[t - 1, i], "y2": Y[t - 2, i],
                     "nat1": Y[t - 1].mean()}
                for k in Ws:
                    r[f"w_{k}"] = lagW[k][t - 1, i]
                rows.append(r)
    return pd.DataFrame(rows)


def fe_ols(P, xcols):
    """シーズン×週の固定効果と、シーズン×県の固定効果を入れた OLS（二方向の平均除去）。SE は県クラスター。"""
    d = P.copy()
    d["st"] = d["season"] + "_" + d["sw"].astype(str)
    d["sp"] = d["season"] + "_" + d["pcode"].astype(str)
    cols = ["y"] + xcols
    X = d[cols].astype(float).copy()
    for _ in range(30):                          # 交互に平均を引く（収束まで）
        X = X - X.groupby(d["st"]).transform("mean")
        X = X - X.groupby(d["sp"]).transform("mean")
    m = sm.OLS(X["y"], X[xcols]).fit(cov_type="cluster", cov_kwds={"groups": d["pcode"]})
    return m


def loso_forecast(P, xcols, phase_mask):
    """1シーズン抜きで学習し、抜いたシーズンの1週先を予測。立ち上がりの時期（phase_mask）で RMSE を比べる。"""
    errs = []
    for s in P["season"].unique():
        tr = P[P["season"] != s]; te = P[(P["season"] == s) & phase_mask.loc[P["season"] == s]]
        Xtr = sm.add_constant(tr[xcols]); Xte = sm.add_constant(te[xcols], has_constant="add")
        m = sm.OLS(tr["y"], Xtr).fit()
        e = te["y"] - m.predict(Xte)
        errs.append(pd.DataFrame({"season": s, "e": e}))
    E = pd.concat(errs)
    return float(np.sqrt((E["e"] ** 2).mean())), E


def main():
    df, A, M, Dinv, D = load()
    out = {}
    seasons_all = sorted(df["season"].unique())
    nat = df.groupby(["season", "sw"])["per"].mean().reset_index()
    peak = nat.loc[nat.groupby("season")["per"].idxmax()].set_index("season")
    out["national_peak"] = {s: {"sw": int(r.sw), "per_mean": round(float(r.per), 2)} for s, r in peak.iterrows()}

    # 1. 開始週
    ON = onset_weeks(df, seasons_all, 1.0)
    ON.to_csv(RES / "onset_week_thr1.csv")
    on_main = ON[MAIN]
    rel = on_main - on_main.median()                                   # 各シーズンの中央値との差（週）
    rel.to_csv(RES / "onset_relative_main.csv")
    rk = on_main.rank()
    # 2. 順番の一貫性
    pairs = list(itertools.combinations(MAIN, 2))
    rhos = [stats.spearmanr(on_main[a], on_main[b], nan_policy="omit")[0] for a, b in pairs]
    m_ = rk.dropna()
    k, n = m_.shape[1], m_.shape[0]
    R = m_.sum(1)
    W_kendall = 12 * ((R - R.mean()) ** 2).sum() / (k ** 2 * (n ** 3 - n))
    # 偶然の W：各シーズンの順位をでたらめに並べ替えた場合
    Wsim = []
    for _ in range(999):
        mm = np.column_stack([rng.permutation(m_.iloc[:, j].values) for j in range(k)])
        RR = mm.sum(1)
        Wsim.append(12 * ((RR - RR.mean()) ** 2).sum() / (k ** 2 * (n ** 3 - n)))
    out["order"] = {"spearman_mean": round(float(np.nanmean(rhos)), 3), "spearman_min": round(float(np.nanmin(rhos)), 3),
                    "spearman_max": round(float(np.nanmax(rhos)), 3), "kendall_W": round(float(W_kendall), 3),
                    "kendall_W_p": float((np.sum(np.array(Wsim) >= W_kendall) + 1) / 1000),
                    "kendall_W_null95": round(float(np.percentile(Wsim, 95)), 3)}
    mean_rel = rel.mean(1).sort_values()
    out["mean_rel_early5"] = mean_rel.head(5).round(2).to_dict()
    out["mean_rel_late5"] = mean_rel.tail(5).round(2).to_dict()
    out["onset_span"] = {s: {"first": float(on_main[s].min()), "median": float(on_main[s].median()), "last": float(on_main[s].max()),
                             "p10_p90": float(on_main[s].quantile(.9) - on_main[s].quantile(.1))} for s in MAIN}

    # 3. 地図の上の固まり
    mor = {}
    for s in MAIN + [x for x in RECENT if x in ON]:
        I, p = morans_i(ON[s].values.astype(float), A)
        mor[s] = {"I": round(float(I), 3), "p": float(p)}
    out["moran_onset"] = mor
    Im, pm = morans_i(mean_rel.reindex(range(1, 48)).values.astype(float), A)
    out["moran_mean_rel"] = {"I": round(float(Im), 3), "p": float(pm)}

    # 開始の早さと県の特徴
    pop = pd.read_csv(DATA.parent / "data" / "raw" / "pref_pop_F10.csv")["jp2023"].values
    tokyo_area = [11, 12, 13, 14]
    msh = M[:, [c - 1 for c in tokyo_area]].sum(1) / M.sum(1)
    feat = pd.DataFrame({"mean_rel": mean_rel.reindex(range(1, 48)).values, "logpop": np.log(pop), "tokyo_share": msh,
                         "lat": pd.read_csv(DATA.parent / "data" / "raw" / "pref_points_F33.csv")["cap_lat"].values})
    feat.index = range(1, 48)
    cors = {c: [round(float(v), 3) for v in stats.spearmanr(feat["mean_rel"], feat[c])] for c in ["logpop", "tokyo_share", "lat"]}
    ex_ok = feat.drop(index=47)
    cors_ex = {c: [round(float(v), 3) for v in stats.spearmanr(ex_ok["mean_rel"], ex_ok[c])] for c in ["logpop", "tokyo_share", "lat"]}
    out["onset_correlates"] = cors
    out["onset_correlates_ex_okinawa"] = cors_ex
    feat.to_csv(RES / "pref_features.csv")

    # 4. 時空間の自己回帰
    Ws = {"adj": A, "mig": M, "dist": Dinv}
    P = panel(df, MAIN, Ws)
    P.to_csv(DATA / "panel_main.csv.gz", index=False, compression="gzip")
    models = {"own": ["y1", "y2"], "adj": ["y1", "y2", "w_adj"], "mig": ["y1", "y2", "w_mig"],
              "adj_mig": ["y1", "y2", "w_adj", "w_mig"], "dist": ["y1", "y2", "w_dist"]}
    coef = []
    for name, xs in models.items():
        m = fe_ols(P, xs)
        for x in xs:
            coef.append({"model": name, "var": x, "b": m.params[x], "se": m.bse[x], "lo": m.conf_int().loc[x, 0], "hi": m.conf_int().loc[x, 1]})
    coef = pd.DataFrame(coef)
    coef.to_csv(RES / "st_ar_coef.csv", index=False)
    out["st_ar"] = {f"{r.model}:{r.var}": [round(r.b, 3), round(r.lo, 3), round(r.hi, 3)] for r in coef.itertuples()}

    # 5. 1週先の予測（固定効果なし。全国の先週の平均も入れる）
    pk = P.merge(peak["sw"].rename("peak_sw"), left_on="season", right_index=True)
    grow = (pk["sw"] <= pk["peak_sw"]) & (pk["sw"] >= pk["peak_sw"] - 8)
    grow.index = P.index
    fc = {}
    for name, xs in {"own": ["y1", "y2", "nat1"], "own_adj": ["y1", "y2", "nat1", "w_adj"], "own_mig": ["y1", "y2", "nat1", "w_mig"],
                     "own_adj_mig": ["y1", "y2", "nat1", "w_adj", "w_mig"]}.items():
        r, E = loso_forecast(P, xs, grow)
        r_all, _ = loso_forecast(P, xs, pd.Series(True, index=P.index))
        fc[name] = {"rmse_growth": round(r, 4), "rmse_all": round(r_all, 4)}
    base = fc["own"]["rmse_growth"]
    for k in fc:
        fc[k]["growth_vs_own_pct"] = round(100 * (fc[k]["rmse_growth"] / base - 1), 2)
    out["forecast"] = fc

    # 6. 頑健性
    rob = []
    for thr in [0.5, 2.0]:
        O = onset_weeks(df, MAIN, thr)
        rh = [stats.spearmanr(O[a], O[b], nan_policy="omit")[0] for a, b in pairs]
        I = np.mean([morans_i(O[s].values.astype(float), A, 199)[0] for s in MAIN])
        rob.append({"setting": f"開始の閾値 {thr}", "spearman_mean": np.nanmean(rh), "moran_mean": I})
    # 沖縄を除く
    O = ON[MAIN].drop(index=47)
    rh = [stats.spearmanr(O[a], O[b], nan_policy="omit")[0] for a, b in pairs]
    A2 = A[:46, :46]
    I = np.mean([morans_i(O[s].values.astype(float), A2, 199)[0] for s in MAIN])
    rob.append({"setting": "沖縄を除く", "spearman_mean": np.nanmean(rh), "moran_mean": I})
    # 重みを変えた Moran's I（移動・距離）
    for nm, W in [("移動の重み", M), ("距離の重み", Dinv)]:
        I = np.mean([morans_i(ON[s].values.astype(float), W, 199)[0] for s in MAIN])
        rob.append({"setting": f"Moran's I を{nm}で", "spearman_mean": np.nan, "moran_mean": I})
    # 時空間 AR：沖縄を除く／コロナ後のシーズン
    keep = P["pcode"] != 47
    m = fe_ols(P[keep].reset_index(drop=True), ["y1", "y2", "w_adj", "w_mig"])
    rob.append({"setting": "時空間AR 沖縄を除く", "b_adj": m.params["w_adj"], "b_mig": m.params["w_mig"],
                "b_adj_lo": m.conf_int().loc["w_adj", 0], "b_mig_lo": m.conf_int().loc["w_mig", 0]})
    rec = [s for s in RECENT if s in seasons_all]
    if rec:
        P2 = panel(df, rec, Ws)
        m = fe_ols(P2, ["y1", "y2", "w_adj", "w_mig"])
        rob.append({"setting": "時空間AR コロナ後（" + "・".join(rec) + "）", "b_adj": m.params["w_adj"], "b_mig": m.params["w_mig"],
                    "b_adj_lo": m.conf_int().loc["w_adj", 0], "b_mig_lo": m.conf_int().loc["w_mig", 0]})
        Or = ON[rec]
        rh = [stats.spearmanr(Or[a], Or[b], nan_policy="omit")[0] for a, b in itertools.combinations(rec, 2)]
        rhx = [stats.spearmanr(on_main.mean(1), Or[s], nan_policy="omit")[0] for s in rec]
        rob.append({"setting": "開始の順番 コロナ後どうし", "spearman_mean": np.nanmean(rh)})
        rob.append({"setting": "開始の順番 コロナ前の平均とコロナ後", "spearman_mean": np.nanmean(rhx)})
    # 隣接のシャッフル（偽の隣）で時空間AR
    Ash = []
    for _ in range(20):
        perm = rng.permutation(47)
        Ap = A[np.ix_(perm, perm)]
        Pp = panel(df, MAIN, {"adj": Ap})
        Ash.append(fe_ols(Pp, ["y1", "y2", "w_adj"]).params["w_adj"])
    rob.append({"setting": "偽の隣接（県をでたらめに入れ替え、20回）", "b_adj": float(np.mean(Ash)), "b_adj_lo": float(np.min(Ash)),
                "b_adj_hi": float(np.max(Ash))})
    R_ = pd.DataFrame(rob)
    R_.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = R_.round(3).to_dict(orient="records")
    out["n_obs_main"] = int(len(P))
    json.dump(out, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
