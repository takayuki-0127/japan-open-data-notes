# 03_分析：広告費は売上にどれだけ効いているのか
#  A. 公開データ（業界全体）：広告業の売上高と小売3業態の販売額の関係を、条件を変えて推定する（交絡と逆の因果を見る）
#  B. 架空の会社「みどりホーム（架空）」のシミュレーション：アドストック・飽和つきの MMM で ROI がどこまで当たるか
#     ・広告費がばらばらに動く場合／需要の見込みに合わせて動く場合（交絡）／地域を分けた実験との比較・実験で補正した MMM
#  C. 予算配分：推定した反応曲線で配分を決めると、本当の売上の増え方はどれだけ違うか
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
OUT = {}

# ---------------------------------------------------------------- A. 公開データ
p = pd.read_csv(D / "panel_2014_2024.csv", index_col="ym")
p.index = pd.PeriodIndex(p.index, freq="M")
y = np.log(p["小売3業態計"])
mo = pd.get_dummies(p.index.month, prefix="m", drop_first=True, dtype=float).set_index(p.index)
t = pd.Series(np.arange(len(p)) / 12.0, index=p.index, name="trend")
cov = pd.Series(((p.index >= pd.Period("2020-04", "M")) & (p.index <= pd.Period("2021-12", "M"))).astype(float), index=p.index, name="covid")
tax = pd.DataFrame({"tax_rush": [1.0 if str(i) in ("2014-03", "2019-09") else 0.0 for i in p.index],
                    "tax_after": [1.0 if str(i) in ("2014-04", "2019-10") else 0.0 for i in p.index]}, index=p.index)


def fit(yv, X, lags=12):
    X = sm.add_constant(X)
    r = sm.OLS(yv, X, missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return r


rowsA = []
for adv, lab in [("total", "広告業の売上高合計"), ("tv", "テレビ"), ("internet", "インターネット広告")]:
    x = np.log(p[adv]).rename("log_ad")
    specs = {
        "1 そのまま（水準どうし）": pd.concat([x], axis=1),
        "2 ＋月の違い": pd.concat([x, mo], axis=1),
        "3 ＋月＋トレンド": pd.concat([x, mo, t], axis=1),
        "4 ＋月＋トレンド＋コロナ期・消費税": pd.concat([x, mo, t, cov, tax], axis=1),
    }
    for k, X in specs.items():
        r = fit(y, X)
        b, se = r.params["log_ad"], r.bse["log_ad"]
        rowsA.append(dict(媒体=lab, 推定=k, 弾力性=b, 下限=b - 1.96 * se, 上限=b + 1.96 * se, p=r.pvalues["log_ad"], R2=r.rsquared, n=int(r.nobs)))
    # 5 前年同月比どうし（季節を消す）
    gy = (y - y.shift(12)).rename("gy")
    gx = (x - x.shift(12)).rename("log_ad")
    r = fit(gy, pd.concat([gx, cov.diff(12).rename("covid_d")], axis=1))
    b, se = r.params["log_ad"], r.bse["log_ad"]
    rowsA.append(dict(媒体=lab, 推定="5 前年同月比どうし", 弾力性=b, 下限=b - 1.96 * se, 上限=b + 1.96 * se, p=r.pvalues["log_ad"], R2=r.rsquared, n=int(r.nobs)))
A = pd.DataFrame(rowsA)
A.to_csv(R / "A_industry_regressions.csv", index=False, encoding="utf-8-sig")

# 先と後：広告の前年同月比が売上の前年同月比より先に動くか（相関の山の位置）
gy = (y - y.shift(12)).dropna()
gx = (np.log(p["total"]) - np.log(p["total"]).shift(12)).dropna()
cc = []
for k in range(-6, 7):  # k>0：広告が k か月先に動く（広告→売上）、k<0：売上が先に動く
    a = gx.shift(k)
    z = pd.concat([a, gy], axis=1).dropna()
    z = z[(z.index < pd.Period("2020-01", "M")) | (z.index > pd.Period("2022-06", "M"))]
    cc.append(dict(ずれ_月=k, 相関=float(np.corrcoef(z.iloc[:, 0], z.iloc[:, 1])[0, 1]), n=len(z)))
CC = pd.DataFrame(cc)
CC.to_csv(R / "A_lead_lag.csv", index=False, encoding="utf-8-sig")
OUT["A"] = {"rows": A.round(4).to_dict("records"), "lead_lag": CC.round(3).to_dict("records")}

# ---------------------------------------------------------------- B. 架空の会社のシミュレーション
CH = ["テレビ", "Web", "チラシ"]
TRUE = dict(decay=np.array([0.6, 0.2, 0.0]), K=np.array([1.0, 0.6, 0.8]), beta=np.array([380.0, 260.0, 160.0]))
MEAN_SP = np.array([45.0, 25.0, 60.0])  # いまの週の平均の広告費（万円、架空。チラシが多め）
SCALE = np.array([60.0, 40.0, 30.0])  # 反応曲線の目盛り（この額で飽和の目安 K に届く）
W = 156


def adstock(s, d):
    out = np.zeros_like(s, dtype=float)
    c = 0.0
    for i, v in enumerate(s):
        c = v + d * c
        out[i] = c
    return out


def hill(x, K):
    return x / (x + K)


def contrib(S, decay, K, beta, scale):
    # S: W×3 の広告費。アドストック → 平均で割って K で飽和 → beta 倍
    return np.column_stack([beta[j] * hill(adstock(S[:, j], decay[j]) / scale[j], K[j]) for j in range(S.shape[1])])


def season(wk):
    w = wk % 52
    return 120 * np.sin(2 * np.pi * (w - 10) / 52) + 60 * np.cos(4 * np.pi * w / 52)


def simulate(rng, scen, weeks=W, noise=40.0):
    wk = np.arange(weeks)
    base = 2000 + 1.5 * wk + season(wk)
    shock = np.zeros(weeks)  # 担当者には見えているが、データには残らない需要の動き（キャンペーン・競合など）
    for i in range(1, weeks):
        shock[i] = 0.8 * shock[i - 1] + rng.normal(0, 40)
    if scen == "ばらばら":
        S = MEAN_SP * rng.uniform(0.2, 1.8, size=(weeks, 3))
    else:  # 需要の見込みに合わせて広告費を増やす（季節＋見えない需要）
        sig = (season(wk) + 1.2 * shock) / 120.0
        S = MEAN_SP * np.clip(1 + 0.5 * sig[:, None] + rng.normal(0, 0.15, size=(weeks, 3)), 0.1, None)
    scale = SCALE.copy()
    C = contrib(S, TRUE["decay"], TRUE["K"], TRUE["beta"], scale)
    sales = base + shock + C.sum(1) + rng.normal(0, noise, weeks)
    return wk, S, sales, C, scale


def roi_at_mean(decay, K, beta):
    """いまの平均の出し方（MEAN_SP）を続けたときの ROI＝その媒体が生む売上の上乗せ ÷ その媒体の広告費（週あたり、定常状態）"""
    x = MEAN_SP / (1 - decay) / SCALE
    return beta * hill(x, K) / MEAN_SP


def true_roi(S, scale):
    return roi_at_mean(TRUE["decay"], TRUE["K"], TRUE["beta"])


DG = [0.0, 0.2, 0.4, 0.6, 0.8]
KG = [0.4, 0.7, 1.0, 1.6]


def controls(wk):
    w = wk % 52
    return np.column_stack([np.ones_like(wk, dtype=float), wk, np.sin(2 * np.pi * w / 52), np.cos(2 * np.pi * w / 52),
                            np.sin(4 * np.pi * w / 52), np.cos(4 * np.pi * w / 52)])


def fit_mmm(wk, S, sales, scale, fix=None, use_season=True, decay_fixed=None):
    """格子でアドストックの減り方と飽和を選び、残りは最小二乗。fix={j: ROI} なら、その媒体の ROI をその値に固定する"""
    X0 = controls(wk) if use_season else controls(wk)[:, :2]
    best = None
    dgrid = [[decay_fixed[j]] if decay_fixed is not None else DG for j in range(3)]
    # 媒体ごとの変換を先に作る
    feats = {(j, d, k): hill(adstock(S[:, j], d) / scale[j], k) for j in range(3) for d in dgrid[j] for k in KG}
    for d0 in dgrid[0]:
        for d1 in dgrid[1]:
            for d2 in dgrid[2]:
                for k0 in KG:
                    for k1 in KG:
                        for k2 in KG:
                            F = np.column_stack([feats[(0, d0, k0)], feats[(1, d1, k1)], feats[(2, d2, k2)]])
                            yy = sales.copy()
                            fixed_b = {}
                            cols = [0, 1, 2]
                            if fix:
                                for j, roi in fix.items():
                                    dj, kj = (d0, d1, d2)[j], (k0, k1, k2)[j]
                                    fixed_b[j] = roi * MEAN_SP[j] / hill(MEAN_SP[j] / (1 - dj) / SCALE[j], kj)
                                    yy = yy - fixed_b[j] * F[:, j]
                                cols = [j for j in cols if j not in fix]
                            X = np.column_stack([X0, F[:, cols]])
                            coef, *_ = np.linalg.lstsq(X, yy, rcond=None)
                            sse = float(((yy - X @ coef) ** 2).sum())
                            if best is None or sse < best[0]:
                                b = np.zeros(3)
                                b[cols] = coef[X0.shape[1]:]
                                for j, v in fixed_b.items():
                                    b[j] = v
                                best = (sse, np.array([d0, d1, d2]), np.array([k0, k1, k2]), b)
    _, d, k, b = best
    return dict(decay=d, K=k, beta=b, roi=roi_at_mean(d, k, b))


def geo_experiment(rng, j=1, n_reg=47, start=100, length=12, post=4, noise=40.0):
    """47 地域を半分に分け、片方で媒体 j を length 週止める。止める前の8週との差の差から ROI を出す（地域は全国の 1/47 の規模。地域ごとの広告費の揺れは±10%）。
    需要の動きは全国共通の部分と地域ごとの小さな部分に分けた"""
    wk = np.arange(W)
    treat = rng.permutation(n_reg) < n_reg // 2
    common = np.zeros(W)
    for i in range(1, W):
        common[i] = 0.8 * common[i - 1] + rng.normal(0, 40)
    tot_inc = []
    lost = []
    for g in range(n_reg):
        base = (2000 + 1.5 * wk + season(wk)) / n_reg
        shock = common / n_reg
        idio = np.zeros(W)
        for i in range(1, W):
            idio[i] = 0.8 * idio[i - 1] + rng.normal(0, 5 / np.sqrt(n_reg))
        shock = shock + idio
        S = MEAN_SP / n_reg * rng.uniform(0.9, 1.1, size=(W, 3))
        if treat[g]:
            S_off = S.copy()
            S_off[start:start + length, j] = 0
        else:
            S_off = S
        scale = SCALE / n_reg
        C = contrib(S_off, TRUE["decay"], TRUE["K"], TRUE["beta"] / n_reg, scale)
        sales = base + shock + C.sum(1) + rng.normal(0, noise / np.sqrt(n_reg), W)
        win = slice(start, start + length + post)
        pre = slice(start - length - post, start)
        tot_inc.append(sales[win].sum() - sales[pre].sum())
        lost.append(S[start:start + length, j].sum())
    tot_inc, lost = np.array(tot_inc), np.array(lost)
    diff = tot_inc[~treat].mean() - tot_inc[treat].mean()  # 止めなかった地域の方が多い分＝広告が生んだ分
    return diff / lost[treat].mean()


rng0 = np.random.default_rng(239)
REPS = 60
rows = []
alloc_cases = {}
for scen in ["ばらばら", "需要に合わせる"]:
    for rep in range(REPS):
        rng = np.random.default_rng(1000 * (scen == "需要に合わせる") + rep)
        wk, S, sales, C, scale = simulate(rng, scen)
        tr = true_roi(S, scale)
        est = fit_mmm(wk, S, sales, scale)
        rec = dict(場面=scen, 回=rep)
        for j, c in enumerate(CH):
            rec[f"真_{c}"] = tr[j]
            rec[f"MMM_{c}"] = est["roi"][j]
        if True:  # 実験と、実験で補正した MMM（Web の ROI を実験の値に固定）
            ex = geo_experiment(np.random.default_rng(5000 + rep + 100 * (scen == "需要に合わせる")))
            cal = fit_mmm(wk, S, sales, scale, fix={1: ex})
            rec["実験_Web"] = ex
            for j, c in enumerate(CH):
                rec[f"補正MMM_{c}"] = cal["roi"][j]
            alloc_cases.setdefault(scen, []).append(dict(mmm=est, cal=cal))
        rows.append(rec)
B = pd.DataFrame(rows)
B.to_csv(R / "B_simulation_roi.csv", index=False, encoding="utf-8-sig")


def summ(df, col_est, col_true):
    e = df[col_est] / df[col_true] - 1
    return dict(平均のずれ=float(e.mean()), 中央値のずれ=float(e.median()), 外れ_中央値=float(e.abs().median()), n=int(e.notna().sum()))


S1 = []
for scen, g in B.groupby("場面"):
    for c in CH:
        S1.append(dict(場面=scen, 媒体=c, 方法="MMM", **summ(g, f"MMM_{c}", f"真_{c}"), 真のROI=float(g[f"真_{c}"].mean())))
        gg = g.dropna(subset=[f"補正MMM_{c}"])
        S1.append(dict(場面=scen, 媒体=c, 方法="実験で補正したMMM", **summ(gg, f"補正MMM_{c}", f"真_{c}"), 真のROI=float(gg[f"真_{c}"].mean())))
    gg = g.dropna(subset=["実験_Web"])
    S1.append(dict(場面=scen, 媒体="Web", 方法="地域実験", **summ(gg, "実験_Web", "真_Web"), 真のROI=float(gg["真_Web"].mean())))
S1 = pd.DataFrame(S1)
S1.to_csv(R / "B_roi_error_summary.csv", index=False, encoding="utf-8-sig")
OUT["B"] = S1.round(4).to_dict("records")

# ---------------------------------------------------------------- B の頑健性
rob = []


def rob_run(label, scen="ばらばら", reps=30, **kw):
    errs = {c: [] for c in CH}
    for rep in range(reps):
        rng = np.random.default_rng(7000 + rep)
        weeks = kw.get("weeks", W)
        wk, S, sales, C, scale = simulate(rng, scen, weeks=weeks, noise=kw.get("noise", 40.0))
        tr = true_roi(S, scale)
        est = fit_mmm(wk, S, sales, scale, use_season=kw.get("use_season", True), decay_fixed=kw.get("decay_fixed"))
        for j, c in enumerate(CH):
            errs[c].append(est["roi"][j] / tr[j] - 1)
    for c in CH:
        e = np.array(errs[c])
        rob.append(dict(条件=label, 媒体=c, 平均のずれ=float(e.mean()), 外れ_中央値=float(np.median(np.abs(e)))))


rob_run("主（ばらばら・3年・季節あり）")
rob_run("データ1年（52週）", weeks=52)
rob_run("雑音2倍", noise=80.0)
rob_run("季節を入れない", use_season=False)
rob_run("アドストックなしと決めつける", decay_fixed=np.array([0.0, 0.0, 0.0]))
ROB = pd.DataFrame(rob)
ROB.to_csv(R / "B_robustness.csv", index=False, encoding="utf-8-sig")
OUT["B_rob"] = ROB.round(4).to_dict("records")

# ---------------------------------------------------------------- C. 予算配分
BUDGET = MEAN_SP.sum()  # 週130万円（架空）


def steady_inc(share, decay, K, beta):
    s = BUDGET * np.asarray(share)
    x = s / (1 - decay) / SCALE
    return float((beta * hill(x, K)).sum())


grid = [np.array([a, b, 1 - a - b]) for a in np.arange(0, 1.0001, 0.05) for b in np.arange(0, 1.0001 - a, 0.05)]


def best_alloc(decay, K, beta):
    v = [steady_inc(g, decay, K, beta) for g in grid]
    return grid[int(np.argmax(v))]


cur = MEAN_SP / BUDGET
truth_best = best_alloc(TRUE["decay"], TRUE["K"], TRUE["beta"])
val_true = lambda sh: steady_inc(sh, TRUE["decay"], TRUE["K"], TRUE["beta"])
Crows = [dict(配分の決め方="いまの配分（35:19:46）", テレビ=cur[0], Web=cur[1], チラシ=cur[2], 本当の週の上乗せ=val_true(cur))]
Crows.append(dict(配分の決め方="本当の反応曲線で最適化", テレビ=truth_best[0], Web=truth_best[1], チラシ=truth_best[2], 本当の週の上乗せ=val_true(truth_best)))
Cdf = pd.DataFrame(Crows)
Cdf["最適に対する割合"] = Cdf["本当の週の上乗せ"] / val_true(truth_best)
Cdf["25%点"] = Cdf["最適に対する割合"]
Cdf["75%点"] = Cdf["最適に対する割合"]
crow2 = []
for scen, lst in alloc_cases.items():
    for key, lab in [("mmm", "MMM"), ("cal", "実験で補正したMMM")]:
        shs = np.array([best_alloc(d[key]["decay"], d[key]["K"], d[key]["beta"]) for d in lst])
        vals = np.array([val_true(sh) for sh in shs]) / val_true(truth_best)
        med = np.median(shs, axis=0)
        crow2.append(dict(配分の決め方=f"{lab}（{scen}のデータ）", テレビ=med[0], Web=med[1], チラシ=med[2], 本当の週の上乗せ=float(np.median(vals) * val_true(truth_best)),
                          最適に対する割合=float(np.median(vals)), **{"25%点": float(np.quantile(vals, 0.25)), "75%点": float(np.quantile(vals, 0.75))}, いまより悪い回=float((vals < val_true(cur) / val_true(truth_best)).mean())))
Cdf = pd.concat([Cdf, pd.DataFrame(crow2)], ignore_index=True)
Cdf.to_csv(R / "C_allocation.csv", index=False, encoding="utf-8-sig")
OUT["C"] = Cdf.round(4).to_dict("records")

# ダッシュボード用の反応曲線（本当の曲線と、ばらばらのデータの MMM）
curve = []
for j, c in enumerate(CH):
    m = alloc_cases["ばらばら"][0]["mmm"]
    for s in np.linspace(0, 120, 61):
        x = s / (1 - TRUE["decay"][j]) / SCALE[j]
        xe = s / (1 - m["decay"][j]) / SCALE[j]
        curve.append(dict(媒体=c, 週の広告費=float(s), 本当=float(TRUE["beta"][j] * hill(x, TRUE["K"][j])), MMM=float(m["beta"][j] * hill(xe, m["K"][j]))))
pd.DataFrame(curve).to_csv(R / "C_response_curves.csv", index=False, encoding="utf-8-sig")
OUT["TRUE"] = {k: v.tolist() for k, v in TRUE.items()}
OUT["MEAN_SP"] = MEAN_SP.tolist()
OUT["SCALE"] = SCALE.tolist()
json.dump(OUT, open(R / "main.json", "w"), ensure_ascii=False, indent=1)
print(A.round(3).to_string())
print(CC.round(3).to_string())
print(S1.round(3).to_string())
print(ROB.round(3).to_string())
print(Cdf.round(3).to_string())
