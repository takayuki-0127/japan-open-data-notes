"""F39 分析：グレンジャー因果（VAR）・VAR-LiNGAM・PC アルゴリズムで、6変数の因果の向きを推定して比べる

出力（results/）
- granger_main.csv          : 原因→結果ごとのグレンジャー検定の p 値（主設定）
- lingam_B0_main.csv        : VAR-LiNGAM の同時点の係数（標準化した変数、行=結果・列=原因）
- lingam_Blag_main.csv      : VAR-LiNGAM の時間差の係数の合計（同上）
- lingam_boot_B0.csv / lingam_boot_Blag.csv : ブートストラップで矢印が出た割合
- pc_boot.csv               : PC の矢印（向きあり）が出た割合（VAR の残差に対して）
- pc_main_edges.csv         : PC の主設定の結果
- edges_compare.csv         : 手法ごとの矢印の一覧
- normality.csv             : VAR の残差の非ガウス性の確認
- robustness.csv            : 期間・変数・変換を変えたときの主な矢印
- order_main.csv            : VAR-LiNGAM の因果の順番
"""
import json
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.api import VAR
from lingam import VARLiNGAM
from causallearn.search.ConstraintBased.PC import pc
from common import DATA, RES, MAIN_VARS, SEED

warnings.filterwarnings("ignore")
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)

TH_B0 = 0.05    # 同時点の係数（標準化）がこれより大きければ「矢印あり」
TH_LAG = 0.10   # 時間差の係数の合計（標準化）がこれより大きければ「矢印あり」
N_BOOT = 200


def zscore(df):
    return (df - df.mean()) / df.std()


def pick_lags(X, maxlags=13):
    sel = VAR(X).select_order(maxlags=maxlags)
    return int(max(1, sel.selected_orders["bic"]))


def granger(X, lags):
    res = VAR(X).fit(lags)
    names = list(X.columns)
    rows = []
    for c in names:
        for e in names:
            if c == e:
                continue
            t = res.test_causality(e, [c], kind="f")
            rows.append({"cause": c, "effect": e, "p": t.pvalue})
    return pd.DataFrame(rows), res


def varlingam(X, lags, boot=0):
    m = VARLiNGAM(lags=lags, criterion=None, prune=True, random_state=SEED)
    m.fit(X.values)
    B0 = m.adjacency_matrices_[0]
    Blag = sum(m.adjacency_matrices_[1:])
    out = {"B0": B0, "Blag": Blag, "order": [X.columns[i] for i in m.causal_order_], "resid": m.residuals_}
    if boot:
        r = m.bootstrap(X.values, n_sampling=boot)
        A = r.adjacency_matrices_  # (n_sampling, n, n*(1+lags))
        n = X.shape[1]
        b0 = np.array([a[:, :n] for a in A])
        bl = np.array([sum(a[:, n * (k + 1): n * (k + 2)] for k in range(lags)) for a in A])
        out["boot_B0"] = (np.abs(b0) > TH_B0).mean(axis=0)
        out["boot_Blag"] = (np.abs(bl) > TH_LAG).mean(axis=0)
        out["boot_B0_sign"] = np.where(np.abs(b0) > TH_B0, np.sign(b0), 0).mean(axis=0)
    return out


def pc_edges(R, names, alpha=0.05):
    """PC（Fisher z）の結果から、向きのある矢印 (原因,結果) と向きのない線 を返す"""
    cg = pc(R, alpha=alpha, indep_test="fisherz", show_progress=False)
    G = cg.G.graph
    directed, undirected = [], []
    n = len(names)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = G[i, j], G[j, i]
            if a == 0 and b == 0:
                continue
            if a == -1 and b == 1:      # i --> j
                directed.append((names[i], names[j]))
            elif a == 1 and b == -1:    # j --> i
                directed.append((names[j], names[i]))
            else:
                undirected.append(tuple(sorted((names[i], names[j]))))
    return directed, undirected


def summarize_edges(names, B0, Blag, gr=None, pcd=None, pcu=None):
    """手法ごとの「原因→結果」を1表にまとめる"""
    rows = []
    for ci, c in enumerate(names):
        for ei, e in enumerate(names):
            if c == e:
                continue
            row = {"cause": c, "effect": e,
                   "lingam_B0": B0[ei, ci], "lingam_lag": Blag[ei, ci]}
            if gr is not None:
                row["granger_p"] = float(gr.loc[(gr.cause == c) & (gr.effect == e), "p"].iloc[0])
            if pcd is not None:
                row["pc"] = "→" if (c, e) in pcd else ("—" if tuple(sorted((c, e))) in pcu else "")
            rows.append(row)
    return pd.DataFrame(rows)


def run_setting(df, label, boot=0, with_granger=True, with_pc=True):
    X = zscore(df)
    lags = pick_lags(X)
    out = {"label": label, "n": len(X), "lags": lags}
    gr = None
    if with_granger:
        gr, var_res = granger(X, lags)
        R = var_res.resid.values
    else:
        R = VAR(X).fit(lags).resid.values
    lg = varlingam(X, lags, boot=boot)
    pcd, pcu = pc_edges(R, list(X.columns)) if with_pc else (None, None)
    out.update(lg)
    out["granger"] = gr
    out["pc_dir"], out["pc_undir"] = pcd, pcu
    out["resid_var"] = R
    out["edges"] = summarize_edges(list(X.columns), lg["B0"], lg["Blag"], gr, pcd, pcu)
    return out


if __name__ == "__main__":
    yoy = pd.read_csv(DATA / "yoy.csv", index_col=0, parse_dates=True)
    mom = pd.read_csv(DATA / "mom.csv", index_col=0, parse_dates=True)

    # ---------- 主設定 ----------
    main = run_setting(yoy[MAIN_VARS], "前年比・1995-2026・6変数", boot=N_BOOT)
    names = MAIN_VARS
    main["granger"].to_csv(RES / "granger_main.csv", index=False)
    pd.DataFrame(main["B0"], index=names, columns=names).to_csv(RES / "lingam_B0_main.csv")
    pd.DataFrame(main["Blag"], index=names, columns=names).to_csv(RES / "lingam_Blag_main.csv")
    pd.DataFrame(main["boot_B0"], index=names, columns=names).to_csv(RES / "lingam_boot_B0.csv")
    pd.DataFrame(main["boot_Blag"], index=names, columns=names).to_csv(RES / "lingam_boot_Blag.csv")
    pd.DataFrame(main["boot_B0_sign"], index=names, columns=names).to_csv(RES / "lingam_boot_B0_sign.csv")
    main["edges"].to_csv(RES / "edges_compare.csv", index=False)
    pd.DataFrame({"rank": range(1, 7), "var": main["order"]}).to_csv(RES / "order_main.csv", index=False)
    pd.DataFrame({"cause": [a for a, b in main["pc_dir"]], "effect": [b for a, b in main["pc_dir"]], "type": "→"}) \
        ._append(pd.DataFrame({"cause": [a for a, b in main["pc_undir"]], "effect": [b for a, b in main["pc_undir"]], "type": "—"})) \
        .to_csv(RES / "pc_main_edges.csv", index=False)
    print("lags", main["lags"], "order", main["order"])

    # ---------- PC のブートストラップ（VAR の残差を行ごとに復元抽出） ----------
    R = main["resid_var"]
    cnt_dir = pd.DataFrame(0.0, index=names, columns=names)   # 行=原因, 列=結果
    cnt_adj = pd.DataFrame(0.0, index=names, columns=names)
    for b in range(N_BOOT):
        idx = rng.integers(0, len(R), len(R))
        d, u = pc_edges(R[idx], names)
        for c, e in d:
            cnt_dir.loc[c, e] += 1
            cnt_adj.loc[c, e] += 1
            cnt_adj.loc[e, c] += 1
        for a, bb in u:
            cnt_adj.loc[a, bb] += 1
            cnt_adj.loc[bb, a] += 1
    (cnt_dir / N_BOOT).to_csv(RES / "pc_boot_dir.csv")
    (cnt_adj / N_BOOT).to_csv(RES / "pc_boot_adj.csv")

    # ---------- 非ガウス性の確認（LiNGAM の前提） ----------
    rows = []
    for k, v in enumerate(names):
        e = main["resid_var"][:, k]
        jb = stats.jarque_bera(e)
        rows.append({"var": v, "skew": stats.skew(e), "excess_kurtosis": stats.kurtosis(e),
                     "jb_p": jb.pvalue, "shapiro_p": stats.shapiro(e).pvalue})
    pd.DataFrame(rows).to_csv(RES / "normality.csv", index=False)

    # ---------- 頑健性 ----------
    settings = [
        ("期間 1995-2012", yoy.loc[:"2012-12-01", MAIN_VARS]),
        ("期間 2013-2026", yoy.loc["2013-01-01":, MAIN_VARS]),
        ("期間 2013-2021（2022年の物価高の前）", yoy.loc["2013-01-01":"2021-12-01", MAIN_VARS]),
        ("失業率を除く", yoy[["fx", "imp", "cpi", "wage", "rate"]]),
        ("金利を除く", yoy[["fx", "imp", "cpi", "wage", "unemp"]]),
        ("賃金を所定内に", yoy[["fx", "imp", "cpi", "wage_sched", "rate", "unemp"]].rename(columns={"wage_sched": "wage"})),
        ("輸入物価を円ベースに（為替を除く）", yoy[["imp_yen", "cpi", "wage", "rate", "unemp"]].rename(columns={"imp_yen": "imp"})),
        ("前月比（季節調整）", mom[MAIN_VARS]),
    ]
    KEY = [("fx", "imp"), ("imp", "fx"), ("fx", "cpi"), ("imp", "cpi"), ("cpi", "imp"), ("imp", "wage"), ("wage", "imp"),
           ("imp", "unemp"), ("fx", "wage"), ("cpi", "wage"), ("wage", "cpi"),
           ("unemp", "wage"), ("wage", "unemp"), ("cpi", "rate"), ("rate", "cpi"), ("rate", "fx"), ("fx", "rate"),
           ("unemp", "cpi")]
    allset = [("主設定（前年比・1995-2026）", main)] + [(lab, run_setting(df, lab)) for lab, df in settings]
    rob = []
    for lab, o in allset:
        E = o["edges"].set_index(["cause", "effect"])
        for c, e in KEY:
            if (c, e) not in E.index:
                continue
            r = E.loc[(c, e)]
            rob.append({"setting": lab, "n": o["n"], "lags": o["lags"], "cause": c, "effect": e,
                        "lingam_B0": round(float(r["lingam_B0"]), 3), "lingam_lag": round(float(r["lingam_lag"]), 3),
                        "granger_p": round(float(r["granger_p"]), 4), "pc": r["pc"],
                        "order": " > ".join(o["order"])})
    pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)

    # 図のための期間別の B0・Blag
    per = {}
    for lab, o in allset[:4]:
        per[lab] = {"B0": np.asarray(o["B0"]).tolist(), "Blag": np.asarray(o["Blag"]).tolist(),
                    "names": list(o["edges"]["cause"].unique()) if False else names, "order": o["order"],
                    "pc_dir": o["pc_dir"], "pc_undir": o["pc_undir"]}
    json.dump(per, open(RES / "period_graphs.json", "w"), ensure_ascii=False, indent=1)
    json.dump({"lags_main": main["lags"], "n_main": main["n"], "order_main": main["order"],
               "th_B0": TH_B0, "th_lag": TH_LAG, "n_boot": N_BOOT}, open(RES / "meta.json", "w"), ensure_ascii=False)
    print("done")
