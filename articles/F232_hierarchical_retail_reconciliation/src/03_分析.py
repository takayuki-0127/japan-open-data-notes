# F232 03 分析：60系列の階層で、ベース予測を7つの方法でそろえ、階層・予測の先ごとに比べる
import pandas as pd, numpy as np, json, pathlib, warnings
from statsmodels.tsa.holtwinters import ExponentialSmoothing
warnings.filterwarnings("ignore")
B = pathlib.Path(__file__).resolve().parents[1]
R = B / "results"
Y = pd.read_csv(B / "data/hier_wide.csv", index_col=0)
nodes = pd.read_csv(B / "data/nodes.csv")
S = np.loadtxt(B / "data/S_matrix.csv", delimiter=",")
n, m = S.shape
lev = nodes["階層"].values
leaf_idx = np.where(lev == 3)[0]
ym = list(Y.index)
H = 12
COVID = [p for p in ym if "2020-02" <= p <= "2021-12"]
rng = np.random.default_rng(232)

def ets_fc(y, h=H):
    ly = np.log(y)
    mod = ExponentialSmoothing(ly, trend="add", damped_trend=True, seasonal="add",
                               seasonal_periods=12).fit(optimized=True)
    fc = np.exp(mod.forecast(h))
    res = y - np.exp(mod.fittedvalues)  # 1か月先の当てはまりの外れ（元の単位）
    return fc, res

def snaive_fc(y, h=H):
    fc = np.array([y[-12 + (k % 12)] for k in range(h)])
    res = np.r_[np.full(12, np.nan), y[12:] - y[:-12]]
    return fc, res

def base_forecasts(origin, kind, cols=None):
    t = ym.index(origin) + 1
    cols = cols if cols is not None else list(Y.columns)
    F = np.zeros((len(cols), H)); E = np.zeros((len(cols), t))
    for i, c in enumerate(cols):
        y = Y[c].values[:t]
        fc, res = (ets_fc if kind == "ets" else snaive_fc)(y)
        F[i] = fc; E[i] = res
    return F, E

def shrink_cov(E):
    # Schäfer–Strimmer の縮小推定（相関の非対角を0へ寄せる）
    E = E[:, ~np.isnan(E).any(0)]
    T = E.shape[1]
    Ec = E - E.mean(1, keepdims=True)
    W = Ec @ Ec.T / T
    sd = np.sqrt(np.diag(W)); Z = Ec / sd[:, None]
    Rm = Z @ Z.T / T
    num = 0.0
    for i in range(len(sd)):
        zz = Z[i] * Z
        v = ((zz - zz.mean(1, keepdims=True)) ** 2).sum(1) * T / (T - 1) ** 3
        v[i] = 0; num += v.sum()
    den = (Rm ** 2).sum() - (np.diag(Rm) ** 2).sum()
    lam = float(np.clip(num / den, 0, 1))
    Rs = (1 - lam) * Rm; np.fill_diagonal(Rs, 1)
    return Rs * np.outer(sd, sd), lam

def P_from_W(Sx, W):
    Wi = np.linalg.pinv(W)
    return np.linalg.solve(Sx.T @ Wi @ Sx, Sx.T @ Wi)

def children_map(Sx, levx):
    ch = {}
    for r in range(len(Sx)):
        ch[r] = [c for c in range(len(Sx)) if levx[c] > levx[r] and np.all(Sx[c] <= Sx[r]) and Sx[c].sum() > 0 and
                 not any(levx[k] > levx[r] and levx[k] < levx[c] and np.all(Sx[c] <= Sx[k]) and np.all(Sx[k] <= Sx[r]) for k in range(len(Sx)) if k not in (r, c))]
    return ch

_CH = {}
def reconcile(F, E, Sx, levx, hist, win=48):
    nn, mm = Sx.shape
    lf = [np.where((Sx == np.eye(mm)[j]).all(1))[0][0] for j in range(mm)]
    out = {"ベース（そろえない）": F}
    out["ボトムアップ"] = Sx @ F[lf]
    # トップダウン：過去36か月の平均の割合
    p_hist = hist[-36:, lf].sum(0) / hist[-36:, 0].sum()
    out["トップダウン（過去の割合）"] = Sx @ (p_hist[:, None] * F[0][None, :])
    # トップダウン：予測の割合を上から順に掛ける
    key = (Sx.shape, float(Sx.sum()))
    if key not in _CH: _CH[key] = children_map(Sx, levx)
    ch = _CH[key]
    prop = np.zeros((nn, F.shape[1])); prop[0] = 1
    for r in sorted(range(nn), key=lambda k: levx[k]):
        kids = ch[r]
        if kids:
            tot = F[kids].sum(0)
            for c in kids: prop[c] = prop[r] * F[c] / tot
    out["トップダウン（予測の割合）"] = Sx @ (prop[lf] * F[0][None, :])
    Ew = E[:, -win:] if win else E
    out["OLS"] = Sx @ (P_from_W(Sx, np.eye(nn)) @ F)
    out["WLS（構造）"] = Sx @ (P_from_W(Sx, np.diag(Sx.sum(1))) @ F)
    v = np.nanvar(Ew, axis=1)
    out["WLS（ばらつき）"] = Sx @ (P_from_W(Sx, np.diag(v)) @ F)
    Wm, lam = shrink_cov(Ew)
    out["MinT（縮小）"] = Sx @ (P_from_W(Sx, Wm) @ F)
    return out, lam

def drop_covid(E, t):
    keep = [i for i in range(t) if ym[i] not in COVID]
    return E[:, keep]

def run(origins, kind="ets", two_level=False, win=48, tag="main"):
    rows, gap = [], []
    if two_level:
        idx = [i for i in range(n) if lev[i] <= 1]
        Sx = np.zeros((len(idx), 6)); Sx[0] = 1; Sx[1:] = np.eye(6)
        levx = np.array([0] + [1] * 6)
    else:
        idx = list(range(n)); Sx = S; levx = lev
    cols = [Y.columns[i] for i in idx]
    hist_all = Y[cols].values
    lams = []
    for o in origins:
        t = ym.index(o) + 1
        F, E = base_forecasts(o, kind, cols)
        E = drop_covid(E, t)
        out, lam = reconcile(F, E, Sx, levx, hist_all[:t], win)
        lams.append(lam)
        act = hist_all[t:t + H].T
        # ベース予測のつじつまのずれ（業態の合計と全体、葉の合計と業態）
        g1 = np.abs(F[[i for i in range(len(idx)) if levx[i] == 1]].sum(0) / F[0] - 1) * 100
        gap.append([o] + list(g1))
        for meth, Ft in out.items():
            ape = np.abs(Ft - act) / act * 100
            for i in range(len(idx)):
                for h in range(H):
                    rows.append((tag, o, meth, cols[i], int(levx[i]), h + 1, ape[i, h], act[i, h]))
        print(tag, o, round(lam, 3), flush=True)
    df = pd.DataFrame(rows, columns=["条件", "予測の起点", "方法", "ノード", "階層", "何か月先", "APE", "実績"])
    gp = pd.DataFrame(gap, columns=["予測の起点"] + [f"h{h}" for h in range(1, H + 1)])
    return df, gp, lams

main_orig = [p for p in ym if "2022-06" <= p <= "2025-08"]
pre_orig = [p for p in ym if "2017-01" <= p <= "2018-12"]
res = {}
d_main, gap_main, lam_main = run(main_orig, tag="主（2022-06〜2025-08起点、ETS）")
d_main.to_csv(R / "A_ape_main.csv.gz", index=False)
gap_main.to_csv(R / "B_base_incoherence_total_vs_types.csv", index=False)
# 葉→業態のつじつまのずれ（業態ごと・ベース予測）は別に計算
d_sn, _, _ = run(main_orig, kind="snaive", tag="ベースを前年同月（季節ナイーブ）")
d_pre, _, _ = run(pre_orig, tag="コロナ前（2017〜2018起点）")
d_two, _, _ = run(main_orig, two_level=True, tag="2階層だけ（全体と業態）")
d_w24, _, _ = run(main_orig, win=24, tag="MinTの外れの期間を24か月")
allr = pd.concat([d_main, d_sn, d_pre, d_two, d_w24])
LV = {0: "全体", 1: "業態", 2: "中分類", 3: "商品（葉）"}

def summarize(df, weighted=False):
    df = df.copy(); df["hb"] = pd.cut(df["何か月先"], [0, 3, 6, 12], labels=["1〜3か月", "4〜6か月", "7〜12か月"])
    if weighted:
        g = df.groupby(["条件", "方法", "階層", "hb"], observed=True).apply(lambda x: np.average(x.APE, weights=x.実績)).rename("MAPE")
    else:
        g = df.groupby(["条件", "方法", "階層", "hb"], observed=True).APE.mean().rename("MAPE")
    g = g.reset_index(); g["階層名"] = g["階層"].map(LV)
    return g

summ = summarize(allr)
summ.to_csv(R / "C_mape_by_level_horizon.csv", index=False)
summ_w = summarize(d_main, weighted=True); summ_w["条件"] = "主・売上で重みづけ"
summ_w.to_csv(R / "C_mape_weighted.csv", index=False)
# 全体の平均（全期間 h1〜12）と、ベースに対する改善率
tot = allr.groupby(["条件", "方法", "階層"]).APE.mean().rename("MAPE").reset_index()
base = tot[tot.方法 == "ベース（そろえない）"].set_index(["条件", "階層"]).MAPE
tot["ベース比_%"] = [(r.MAPE / base[(r.条件, r.階層)] - 1) * 100 for r in tot.itertuples()]
tot["階層名"] = tot["階層"].map(LV)
tot.to_csv(R / "D_mape_relative_to_base.csv", index=False)

# 起点ごとの差の95%区間（ブロック・ブートストラップ、ブロック6か月）
def boot_diff(df, a, b, level, reps=2000, blk=6):
    x = df[(df.方法 == a) & (df.階層 == level)].groupby("予測の起点").APE.mean()
    y = df[(df.方法 == b) & (df.階層 == level)].groupby("予測の起点").APE.mean()
    d = (x - y).values; T = len(d); bs = []
    for _ in range(reps):
        st = rng.integers(0, T - blk + 1, size=int(np.ceil(T / blk)))
        s = np.concatenate([d[k:k + blk] for k in st])[:T]; bs.append(s.mean())
    return d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5), (d < 0).mean()

cmp = []
for lvv in range(4):
    for a, b in [("MinT（縮小）", "ボトムアップ"), ("MinT（縮小）", "ベース（そろえない）"), ("WLS（構造）", "ボトムアップ"),
                 ("MinT（縮小）", "WLS（構造）"), ("トップダウン（予測の割合）", "MinT（縮小）")]:
        mdiff, lo, hi, win = boot_diff(d_main, a, b, lvv)
        cmp.append([LV[lvv], a, b, mdiff, lo, hi, win])
cmp = pd.DataFrame(cmp, columns=["階層", "方法A", "方法B", "差（A−B、MAPEのポイント）", "95%下限", "95%上限", "Aが良かった起点の割合"])
cmp.to_csv(R / "E_paired_diff_bootstrap.csv", index=False)

# 業態ごと（葉レベルと業態レベル）
byg = d_main.copy(); byg["業態"] = byg.ノード.str.split("/").str[0]
byg = byg[byg.階層 >= 1].groupby(["業態", "階層", "方法"]).APE.mean().unstack("方法").round(2)
byg.to_csv(R / "F_mape_by_store_type.csv")

# 推奨表のための数字：各階層で一番よい方法と、MinT・BU・ベースの差
best = tot[tot.条件.str.startswith("主")].sort_values("MAPE").groupby("階層").head(1)
best.to_csv(R / "G_best_by_level.csv", index=False)
res["lambda_mean"] = float(np.mean(lam_main))
res["gap_total_vs_types_mean_pct"] = float(gap_main.iloc[:, 1:].values.mean())
res["gap_total_vs_types_h12_p95"] = float(np.percentile(gap_main["h12"], 95))
res["n_origins_main"] = len(main_orig); res["n_series"] = int(n); res["n_leaves"] = int(m)
json.dump(res, open(R / "main.json", "w"), ensure_ascii=False, indent=1)
# ダッシュボード用：最新起点（2025-08）からの12か月の予測（MinT・BU・ベース）
o = "2025-08"; t = ym.index(o) + 1
F, E = base_forecasts(o, "ets"); E = drop_covid(E, t)
out, _ = reconcile(F, E, S, lev, Y.values[:t])
dash = {"ym_hist": ym[-36:], "ym_fc": [str(pd.Period(o, "M") + k) for k in range(1, H + 1)], "nodes": list(Y.columns),
        "level": [int(x) for x in lev], "hist": Y.values[-36:].T.round(0).tolist(),
        "fc": {k: out[k].round(0).tolist() for k in ["ベース（そろえない）", "ボトムアップ", "MinT（縮小）"]}}
json.dump(dash, open(B / "dashboard/data.json", "w"), ensure_ascii=False)
# SQL 検算用の表（最新起点の予測、縦持ち）
lg = []
for k in ["ベース（そろえない）", "MinT（縮小）"]:
    for i, c in enumerate(Y.columns):
        par = "" if lev[i] == 0 else ("全体" if lev[i] == 1 else c.split("/")[0])
        if lev[i] == 3:
            g, it = c.split("/", 1)
            for (gg, mm2), kids in {("百貨店", "衣料品"): ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品"],
                                   ("百貨店", "その他"): ["家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
                                   ("スーパー", "衣料品"): ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品"],
                                   ("スーパー", "その他"): ["家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
                                   ("コンビニ", "商品販売額"): ["FF・日配食品", "加工食品", "非食品"]}.items():
                if gg == g and it in kids: par = f"{g}/{mm2}"
        for h in range(H):
            lg.append([k, c, par, int(lev[i]), dash["ym_fc"][h], float(out[k][i, h])])
pd.DataFrame(lg, columns=["method", "node", "parent", "level", "ym", "forecast"]).to_csv(B / "data/forecast_2025_08_long.csv", index=False)
print(json.dumps(res, ensure_ascii=False))
