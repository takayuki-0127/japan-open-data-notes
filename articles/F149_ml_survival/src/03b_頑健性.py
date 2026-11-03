"""頑健性と「何が効いたか」の分解。

python 03b_頑健性.py decomp   … Cox＋スプライン・GBM-Cox(深さ1) を5回の分割で（足し算の曲がりだけで追いつくか）
python 03b_頑健性.py group    … 都道府県ごとに分ける検証（GroupKFold 5分割）
python 03b_頑健性.py temporal … 時間で分ける検証（2020年までの設立で学習 → 2021年以降の設立で評価、τ=5年）
python 03b_頑健性.py feat     … 特徴量を減らす（基本4つだけ／市区町村の閉鎖率なし）
python 03b_頑健性.py lc       … 標本を1万・3万社に減らす
python 03b_頑健性.py e01      … 閉鎖＝清算の結了等だけ
python 03b_頑健性.py imp      … 並べ替えによる特徴量の重要度と、GBM-Cox の部分依存
python 03b_頑健性.py synth    … 半合成データ：本当のハザードが「線形」と「曲がり・交互作用あり」の2通りで、手法が差を見つけられるか
"""
import sys, json
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from common import RES, SEED
import importlib
A = importlib.import_module("03_分析")
from models import design, fit_predict, G
from metrics import evaluate

MODELS = A.MODELS
stage = sys.argv[1]
s = A.load()


def save(rows, cals, name):
    pd.DataFrame(rows).to_csv(RES / f"{name}_metrics.csv", index=False)
    if cals:
        pd.DataFrame(cals).to_csv(RES / f"{name}_calibration.csv", index=False)


if stage == "decomp":
    rows, cals = [], []
    for k in range(5):
        tr, te = A.split(s, k)
        o, c = A.run(["Cox＋スプライン", "GBM-Cox(深さ1)"], tr, te, seed=k, tag={"split": k}); rows += o; cals += c
        save(rows, cals, "decomp")

if stage == "group":
    rows, cals = [], []
    for f, (i, j) in enumerate(GroupKFold(5).split(s, groups=s.pref)):
        o, c = A.run(MODELS, s.iloc[i].reset_index(drop=True), s.iloc[j].reset_index(drop=True), tag={"fold": f}); rows += o; cals += c
        save(rows, cals, "group")

if stage == "temporal":
    tr = s[s.cohort < 2021].reset_index(drop=True); te = s[s.cohort >= 2021].reset_index(drop=True)
    o, c = A.run(MODELS, tr, te, tau=5.0, tag={"split": "temporal"}); save(o, c, "temporal")

if stage == "feat":
    rows = []
    tr, te = A.split(s, 0)
    for fs in ("basic", "all_no_rate"):
        o, _ = A.run(MODELS, tr, te, featset=fs, tag={"featset": fs}); rows += o
        save(rows, None, "feat")

if stage == "lc":
    rows = []
    for n in (10_000, 30_000):
        ss = s.sample(n, random_state=SEED).reset_index(drop=True)
        for k in range(3):
            tr, te = A.split(ss, k)
            o, _ = A.run(MODELS, tr, te, seed=k, tag={"n": n, "split": k}); rows += o
            save(rows, None, "lc")

if stage == "e01":
    s1 = A.load("E01"); tr, te = A.split(s1, 0)
    o, c = A.run(MODELS, tr, te, tag={"event": "01only"}); save(o, c, "e01")

if stage == "imp":
    tr, te = A.split(s, 0)
    Xtr = design(tr, "all"); Xte = design(te, "all", ref=Xtr.columns)
    groups = {"種別": "kind_", "地域区分": "area_", "地方": "region_", "都道府県": "pref_", "指定年": "cohort", "指定月": "month_",
              "指定日の日にち": "dom", "曜日": "dow_", "市区町村の規模": "muni_logn", "市区町村の種別構成": ("muni_llc", "muni_other"),
              "市区町村の閉鎖率": "lmuni_rate"}
    rng = np.random.default_rng(SEED)
    Xs = [Xte]; names = ["なし"]
    for g, pre in groups.items():
        pre = pre if isinstance(pre, tuple) else (pre,)
        cols = [c for c in Xte.columns if any(c == p or (p.endswith("_") and c.startswith(p)) for p in pre)]
        P = Xte.copy(); perm = rng.permutation(len(P)); P[cols] = Xte[cols].values[perm]
        Xs.append(P); names.append(g)
    par = A.params(); rows = []
    for m in ["Cox", "RSF", "GBM-Cox"]:
        Ss = fit_predict(m, Xtr, tr["T"].values, tr["E"].values, Xs, seed=SEED, params=par.get(m, {}))
        base = None
        for nm, S in zip(names, Ss):
            r, _ = evaluate(S, tr["T"].values, tr["E"].values, te["T"].values, te["E"].values, t_cal=())
            if base is None:
                base = r
            rows.append({"model": m, "permuted": nm, "C_uno": r["C_uno"], "dC": base["C_uno"] - r["C_uno"], "IBS": r["IBS"],
                         "dIBS_pct": (r["IBS"] - base["IBS"]) / base["IBS"] * 100})
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(RES / "importance.csv", index=False)
    # 部分依存：GBM-Cox の対数ハザード（学習データ全体の平均を0）を、特徴量の値ごとに。Cox の係数による直線と並べる
    import xgboost as xgb
    from sksurv.linear_model import CoxPHSurvivalAnalysis
    from sksurv.util import Surv
    p = par.get("GBM-Cox", {})
    lab = np.where(tr.E.values == 1, tr["T"].values, -tr["T"].values)
    rng2 = np.random.default_rng(SEED); va = rng2.random(len(Xtr)) < 0.2
    prm = dict(eta=0.05, max_depth=p.get("depth", 4), min_child_weight=p.get("mcw", 20), subsample=0.8, colsample_bytree=0.8,
               seed=SEED, nthread=2, tree_method="hist", objective="survival:cox", eval_metric="cox-nloglik")
    b = xgb.train(prm, xgb.DMatrix(Xtr[~va].values, label=lab[~va]), 3000, evals=[(xgb.DMatrix(Xtr[va].values, label=lab[va]), "va")],
                  early_stopping_rounds=100, verbose_eval=False)
    b = xgb.train(prm, xgb.DMatrix(Xtr.values, label=lab), b.best_iteration + 1)
    sub = Xtr.sample(5000, random_state=SEED)
    base = b.predict(xgb.DMatrix(sub.values), output_margin=True).mean()
    pd_rows = []
    for c, vals in {"cohort": np.arange(2016, 2026.01, 0.5), "dom": np.arange(1, 32), "lmuni_rate": np.quantile(Xtr.lmuni_rate, np.linspace(0.02, 0.98, 25)),
                    "muni_logn": np.quantile(Xtr.muni_logn, np.linspace(0.02, 0.98, 25))}.items():
        for v in vals:
            P = sub.copy(); P[c] = v
            pd_rows.append({"feature": c, "value": v, "gbm": b.predict(xgb.DMatrix(P.values), output_margin=True).mean() - base})
    # 種別×地域区分（交互作用の確認）
    for k in ["株式会社", "合同会社", "その他法人"]:
        for a in ["東京23区", "政令市", "その他"]:
            P = sub.copy()
            for col in [c for c in P.columns if c.startswith("kind_")]:
                P[col] = 1.0 if col == f"kind_{k}" else 0.0
            for col in [c for c in P.columns if c.startswith("area_")]:
                P[col] = 1.0 if col == f"area_{a}" else 0.0
            pd_rows.append({"feature": "kind×area", "value": f"{k}|{a}", "gbm": b.predict(xgb.DMatrix(P.values), output_margin=True).mean() - base})
    m = CoxPHSurvivalAnalysis(alpha=1e-3, ties="breslow").fit(Xtr.values, Surv.from_arrays(tr.E.values.astype(bool), tr["T"].values))
    coef = dict(zip(Xtr.columns, m.coef_))
    pdd = pd.DataFrame(pd_rows); pdd["cox_coef"] = pdd.feature.map(coef)
    pdd.to_csv(RES / "partial_dependence.csv", index=False)
    pd.Series(coef).to_csv(RES / "cox_coef.csv")

if stage == "synth":
    # 実際の特徴量はそのまま、閉鎖の時刻だけを作り直す。打ち切りは実際と同じ（2026-09-30 までの観察年数）
    X = design(s, "all")
    rng = np.random.default_rng(SEED)
    cmax = (2026.75 - s.cohort).clip(lower=1 / 12).values            # 観察できる最大の年数
    lin = 0.35 * X["kind_合同会社"] + 0.5 * X["kind_その他法人"] + 0.4 * X.get("area_東京23区", 0) + 0.25 * (X.lmuni_rate - X.lmuni_rate.mean())
    nonlin = lin + 0.9 * X["kind_合同会社"] * X.get("area_東京23区", 0) + 0.6 * ((s.dom == 1) | (s.dom >= 28)).astype(float) \
        - 0.8 * ((s.cohort - 2021) / 3) ** 2 * X["kind_その他法人"] + 0.5 * (X.muni_logn > X.muni_logn.quantile(0.9))
    rows = []
    for truth, eta in (("線形", lin), ("曲がり・交互作用あり", nonlin)):
        eta = eta - eta.mean()
        # ワイブル（形 0.8）で、全体の5年閉鎖率が実データ（約5%）程度になる尺度
        u = rng.random(len(s)); lam = 0.011
        Tt = (-np.log(u) / (lam * np.exp(eta.values))) ** (1 / 0.8)
        T = np.minimum(Tt, cmax); E = (Tt <= cmax).astype(int)
        ss = s.copy(); ss["T"] = np.ceil(T * 12) / 12; ss["E"] = E
        tr, te = A.split(ss, 0)
        o, _ = A.run(MODELS, tr, te, tag={"truth": truth}); rows += o
        # 本当のリスクで並べたときの C（上限の目安）
        from sksurv.metrics import concordance_index_ipcw
        from sksurv.util import Surv
        mte = np.random.default_rng(0).random(len(ss)) < 0.7
        rows.append({"model": "本当のリスク", "truth": truth,
                     "C_uno": concordance_index_ipcw(Surv.from_arrays(tr.E.astype(bool), tr["T"]), Surv.from_arrays(te.E.astype(bool), te["T"]),
                                                     eta.values[~mte], tau=8)[0]})
        save(rows, None, "synth")
