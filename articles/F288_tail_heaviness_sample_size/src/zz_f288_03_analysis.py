"""集計と仮説の判定。results/main.json と表の CSV を書く。"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from zz_f288_common import DISTS, TRUE_MODEL

out = sys.argv[1] if len(sys.argv) > 1 else "results"
CRIT5, CRIT10 = 2.706, 1.642  # 境界の検定：0.5χ²0+0.5χ²1 の片側5%・10%


def summarize(A):
    A = A.copy()
    A["tm"] = A.dist.map(TRUE_MODEL)
    A["heavy5"] = A.lr > CRIT5
    A["heavy10"] = A.lr > CRIT10
    A["ok_aic"] = A.pick_aic == A.tm
    A["ok_bic"] = A.pick_bic == A.tm
    A["ge1"] = A.xi_mle >= 1
    A["ge1_pwm"] = A.xi_pwm >= 1
    g = A.groupby(["dist", "n"])
    t = g.agg(reps=("rep", "size"), heavy5=("heavy5", "mean"), heavy10=("heavy10", "mean"),
              ok_aic=("ok_aic", "mean"), ok_bic=("ok_bic", "mean"),
              xi_q05=("xi_mle", lambda x: x.quantile(.05)), xi_med=("xi_mle", "median"), xi_q95=("xi_mle", lambda x: x.quantile(.95)),
              pwm_q05=("xi_pwm", lambda x: x.quantile(.05)), pwm_med=("xi_pwm", "median"), pwm_q95=("xi_pwm", lambda x: x.quantile(.95)),
              ge1=("ge1", "mean"), ge1_pwm=("ge1_pwm", "mean")).reset_index()
    xi_true = t.dist.map(lambda d: DISTS[d][1])
    t["xi_true"] = xi_true
    A["sq"] = (A.xi_mle - A.dist.map(lambda d: DISTS[d][1])) ** 2
    t["rmse"] = np.sqrt(A.groupby(["dist", "n"]).sq.mean().values)
    return t


def cell(t, d, n, col):
    return float(t[(t.dist == d) & (t.n == n)][col].iloc[0])


def verdicts(t, est="xi", lev="heavy5", pick="ok_aic"):
    h1 = cell(t, "gpd0.4", 50, lev)
    h2 = cell(t, "ln1.5", 100, lev)
    h3a, h3b = cell(t, "gpd0.4", 30, pick), cell(t, "ln1.5", 30, pick)
    h4 = cell(t, "gpd0.5", 15, "ge1" if est == "xi" else "ge1_pwm")
    q05, q95 = (f"{est if est=='pwm' else 'xi'}_q05", f"{est if est=='pwm' else 'xi'}_q95")
    sub = t[t.dist == "gpd0.4"].sort_values("n")
    inside = sub[(sub[q05] >= 0.4 - 0.15) & (sub[q95] <= 0.4 + 0.15)]
    nmin = int(inside.n.min()) if len(inside) else None
    return {
        "H1": {"value": h1, "verdict": "支持" if h1 < 0.8 else "外れ"},
        "H2": {"value": h2, "verdict": "支持" if h2 >= 0.5 else "外れ"},
        "H3": {"gpd0.4": h3a, "ln1.5": h3b, "verdict": "支持" if (h3a < 0.5 and h3b < 0.5) else "外れ"},
        "H4": {"value": h4, "verdict": "支持" if h4 >= 0.10 else "外れ"},
        "H5": {"n_min_inside": nmin, "verdict": "支持" if (nmin is None or nmin >= 200) else "外れ"},
    }


A = pd.read_csv(f"{out}/A_sims_seed288.csv.gz")
B = pd.read_csv(f"{out}/B_sims_seed2881.csv.gz")
C = pd.read_csv(f"{out}/C_r4_ln15_threshold.csv.gz")
D = pd.read_csv(f"{out}/D_r5_2000reps.csv.gz")
tA, tB = summarize(A), summarize(B)
tA.round(4).to_csv(f"{out}/E_table_seed288.csv", index=False)
tB.round(4).to_csv(f"{out}/F_table_seed2881.csv", index=False)

res = {"main": verdicts(tA)}
res["R1_10pct_bic"] = verdicts(tA, lev="heavy10", pick="ok_bic")
res["R2_pwm"] = verdicts(tA, est="pwm")
res["R3_seed2881"] = verdicts(tB)
tD = summarize(D)
res["R5_2000reps"] = {"H1": cell(tD, "gpd0.4", 50, "heavy5"), "H2": cell(tD, "ln1.5", 100, "heavy5"),
                      "H3_gpd0.4": cell(tD, "gpd0.4", 30, "ok_aic"), "H3_ln1.5": cell(tD, "ln1.5", 30, "ok_aic"),
                      "H4": cell(tD, "gpd0.5", 15, "ge1")}
# 検定の大きさ（指数が本当のとき「重い」とした割合）
res["size_exp"] = {int(n): cell(tA, "exp", n, "heavy5") for n in sorted(tA.n.unique())}
# 検出力80%に届く最小の n
p80 = {}
for d in DISTS:
    s = tA[tA.dist == d].sort_values("n")
    hit = s[s.heavy5 >= 0.8]
    p80[d] = int(hit.n.min()) if len(hit) else None
res["n_power80"] = p80
# ξ̂ の幅が ±0.15 に収まる最小の n（GPD のみ）
w15 = {}
for d in ["gpd0.2", "gpd0.4", "gpd0.5", "gpd0.6", "gpd0.8"]:
    xi = DISTS[d][1]
    s = tA[tA.dist == d].sort_values("n")
    hit = s[(s.xi_q05 >= xi - 0.15) & (s.xi_q95 <= xi + 0.15)]
    w15[d] = int(hit.n.min()) if len(hit) else None
res["n_width015"] = w15
# R4：対数正規 σ=1.5 の上位を超過額にしたとき
C["heavy5"] = C.lr > CRIT5
C["ge1"] = C.xi_mle >= 1
tc = C.groupby(["q", "n"]).agg(heavy5=("heavy5", "mean"), xi_med=("xi_mle", "median"),
                                xi_q05=("xi_mle", lambda x: x.quantile(.05)), xi_q95=("xi_mle", lambda x: x.quantile(.95)),
                                ge1=("ge1", "mean")).reset_index()
tc.round(4).to_csv(f"{out}/G_r4_table.csv", index=False)
res["R4"] = {f"q{q}": {"heavy5_n100": float(tc[(tc.q == q) & (tc.n == 100)].heavy5.iloc[0]),
                       "xi_med_n1000": float(tc[(tc.q == q) & (tc.n == 1000)].xi_med.iloc[0]),
                       "ge1_n15": float(tc[(tc.q == q) & (tc.n == 15)].ge1.iloc[0])} for q in [0.8, 0.9, 0.95]}

# 問い直し（結果を見た後に追加）：F260 の15事故と同じ「AIC で見分けられず、ξ̂≈0.47」は、どの本当の分布から出やすいか
r = {}
for n in [15, 30]:
    s = A[A.n == n].copy()
    aics = s[["aic_exp", "aic_weib", "aic_lnorm", "aic_gpd"]].values
    s["close"] = (aics.max(1) - aics.min(1)) < 2
    s["xi_near"] = (s.xi_mle - 0.47).abs() <= 0.10
    s["both"] = s.close & s.xi_near
    r[n] = s.groupby("dist")[["close", "xi_near", "both"]].mean().round(4).to_dict(orient="index")
res["reask"] = r
pd.DataFrame({(n, d): v for n in r for d, v in r[n].items()}).T.to_csv(f"{out}/H_reask_n15_n30.csv")

# レビュー後に追加：ξ<−1 側の下限に張り付いた回の割合と、それを除いた確かめ
res["gpd_bound_share_by_n"] = {int(k): round(float(v), 4) for k, v in A.groupby("n").gpd_bound.mean().items()}
res["gpd_bound_share_n15_by_dist"] = {k: round(float(v), 4) for k, v in A[A.n == 15].groupby("dist").gpd_bound.mean().items()}
res["gpd_bound_n_le15_pick"] = {k: round(float(v), 4) for k, v in A[A.gpd_bound & (A.n <= 15)].pick_aic.value_counts(normalize=True).items()}
Ax = A[~A.gpd_bound]
tx = summarize(Ax)
res["excl_bound"] = {"H3_gpd0.4_n30": cell(tx, "gpd0.4", 30, "ok_aic"), "H3_ln1.5_n30": cell(tx, "ln1.5", 30, "ok_aic"),
                     "ok_aic_n15": {d: round(cell(tx, d, 15, "ok_aic"), 4) for d in DISTS},
                     "ok_aic_n15_all": {d: round(cell(tA, d, 15, "ok_aic"), 4) for d in DISTS}}
rx = {}
s15 = Ax[Ax.n == 15].copy()
aics = s15[["aic_exp", "aic_weib", "aic_lnorm", "aic_gpd"]].values
s15["both"] = ((aics.max(1) - aics.min(1)) < 2) & ((s15.xi_mle - 0.47).abs() <= 0.10)
res["excl_bound"]["reask_both_n15"] = {k: round(float(v), 4) for k, v in s15.groupby("dist").both.mean().items()}
# モンテカルロ誤差（割合の標準誤差）
se = lambda p, n: round(float(np.sqrt(p * (1 - p) / n)), 4)
res["mc_se"] = {"H1": se(res["main"]["H1"]["value"], 500), "H3_gpd": se(res["main"]["H3"]["gpd0.4"], 500), "H3_ln": se(res["main"]["H3"]["ln1.5"], 500),
                "H4": se(res["main"]["H4"]["value"], 500), "H4_R5": se(res["R5_2000reps"]["H4"], 2000),
                "reask_n15": {d: se(v["both"], 500) for d, v in r[15].items()}}
# 検出力80%の件数を対数で線形補間（格子の間の目安）
interp = {}
for d in ["gpd0.2", "gpd0.4", "gpd0.5", "gpd0.6", "gpd0.8", "ln1.5", "weib0.6"]:
    s_ = tA[tA.dist == d].sort_values("n")
    xs, ys = np.log(s_.n.values), s_.heavy5.values
    j = int(np.argmax(ys >= 0.8))
    interp[d] = None if ys[j] < 0.8 or j == 0 else round(float(np.exp(xs[j - 1] + (0.8 - ys[j - 1]) / (ys[j] - ys[j - 1]) * (xs[j] - xs[j - 1]))), 1)
res["n_power80_interp"] = interp
json.dump(res, open(f"{out}/main.json", "w"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(res, ensure_ascii=False, indent=1)[:6000])
