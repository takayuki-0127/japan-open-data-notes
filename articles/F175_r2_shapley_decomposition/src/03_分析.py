"""03 分析：R² を特徴量のまとまり（グループ）ごとに Shapley 値で分ける

地価（F03、7グループ）と電力需要（F22、7グループ→6・4グループに読み替え）について、
  A. 学び直し（refit）の Shapley（LightGBM）
  B. 周辺でならす SAGE（学習済み LightGBM のまま）
  C. 線形回帰の学び直し（LMG）
  D. 1つだけ外す（drop）・1つだけ使う（alone）
  E. |SHAP| の取り分（F91 の見方。グループの SHAP を足してから絶対値）
を並べる。評価データの行を200回ブートストラップして、A・C の幅も出す。
2^7=128 通りの学習は、結果を results/_cache_*.npz に置いて再実行時は読み直す。
"""
import sys, time, json
import numpy as np, pandas as pd
import shap
from common import (RES, SEED, L_GROUPS, L_GROUPS4, P_GROUPS, P_GROUPS4, P_GROUPS7, data_land, data_power, r2)
from shapley import refit_values, sage_values, fit_lgbm, coarsen, summary_table, r2_matrix, shapley

T0 = time.time()


def log(s):
    print(f"[{time.time() - T0:6.0f}s] {s}", flush=True)


def cached(name, fn):
    f = RES / f"_cache_{name}.npz"
    if f.exists():
        return np.load(f)["a"]
    a = fn()
    np.savez_compressed(f, a=a)
    return a


def boot(y, P, k, B=200, seed=SEED):
    rng = np.random.default_rng(seed)
    out = np.zeros((B, k))
    for b in range(B):
        out[b] = shapley(r2_matrix(y, P, rng.integers(0, len(y), len(y))), k)
    return np.percentile(out, [2.5, 97.5], axis=0)


def group_shap(model, X, groups, n=2000):
    Xs = X.sample(n, random_state=SEED)
    sv = shap.TreeExplainer(model).shap_values(Xs)
    cols = list(X.columns)
    g = {name: np.abs(sv[:, [cols.index(c) for c in cs]].sum(1)).mean() for name, cs in groups.items()}
    tot = sum(g.values())
    return {k: v / tot for k, v in g.items()}


def run(name, Xtr, ytr, Xte, yte, groups, coarse_sets):
    k = len(groups)
    log(f"{name}: 学習 {len(Xtr)}・評価 {len(Xte)}・{k}グループ")
    P = cached(f"{name}_refit_lgbm", lambda: refit_values(Xtr, ytr, Xte, yte, groups, "lgbm", log))
    PL = cached(f"{name}_refit_linear", lambda: refit_values(Xtr, ytr, Xte, yte, groups, "linear", log))
    full = fit_lgbm(Xtr, ytr)
    log(f"{name}: SAGE")
    vS = cached(f"{name}_sage_K32", lambda: sage_values(full, Xte, yte, groups, K=32))
    gs = group_shap(full, Xte, groups)
    vA, vC = r2_matrix(yte, P), r2_matrix(yte, PL)
    pd.DataFrame({"mask": range(1 << k), "グループ": [" + ".join(g for i, g in enumerate(groups) if m >> i & 1) or "（なし）" for m in range(1 << k)],
                  "R2_学び直しLGBM": vA, "R2_SAGE": vS, "R2_線形": vC}).to_csv(RES / f"coalitions_{name}.csv", index=False)
    tA, totA = summary_table(vA, groups)
    tS, totS = summary_table(vS, groups)
    tC, totC = summary_table(vC, groups)
    ciA, ciC = boot(yte, P, k), boot(yte, PL, k)
    t = pd.DataFrame({"グループ": list(groups), "変数の数": [len(v) for v in groups.values()],
                      "学び直し": tA.shapley, "学び直し_下": ciA[0], "学び直し_上": ciA[1],
                      "SAGE": tS.shapley, "線形LMG": tC.shapley, "線形_下": ciC[0], "線形_上": ciC[1],
                      "1つだけ外す": tA.drop_one, "1つだけ使う": tA.alone,
                      "SHAP取り分": [gs[g] for g in groups]})
    for c, tot in (("学び直し", totA), ("SAGE", totS), ("線形LMG", totC)):
        t[c + "_割合"] = t[c] / tot
    t.to_csv(RES / f"shapley_{name}.csv", index=False)
    summ = {"R2_全変数_学び直し": float(vA[-1]), "R2_全変数_SAGE": float(vS[-1]), "R2_全変数_線形": float(vC[-1]),
            "R2_なし_学び直し": float(vA[0]), "R2_なし_SAGE": float(vS[0]),
            "外す合計/R2": float(tA.drop_one.sum() / totA), "使う合計/R2": float(tA.alone.sum() / totA)}
    # 粗いグループへの読み替え
    for cname, cg in coarse_sets.items():
        rows = []
        for lab, v in (("学び直し", vA), ("SAGE", vS), ("線形LMG", vC)):
            vc = coarsen(v, groups, cg)
            phi = shapley(vc, len(cg))
            for g, p in zip(cg, phi):
                fine_sum = sum(t.loc[t.グループ == f, lab].item() for f in groups if set(groups[f]) <= set(cg[g]))
                rows.append({"まとめ方": cname, "方法": lab, "グループ": g, "shapley": p, "細かいグループの合計": fine_sum,
                             "割合": p / (vc[-1] - vc[0])})
        pd.DataFrame(rows).to_csv(RES / f"regroup_{name}_{cname}.csv", index=False)
    log(f"{name}: 完了")
    return t, summ, P, vA


if __name__ == "__main__":
    which = sys.argv[1:] or ["land", "power"]
    summary = json.loads((RES / "summary.json").read_text()) if (RES / "summary.json").exists() else {}
    if "land" in which:
        Xtr, ytr, Xte, yte, _ = data_land()
        t, s, _, _ = run("地価", Xtr, ytr, Xte, yte, L_GROUPS, {"4グループ": L_GROUPS4})
        summary["地価"] = s
        print(t.round(3).to_string())
    if "power" in which:
        Xtr, ytr, Xte, yte, idx = data_power()
        t, s, P, vA = run("電力需要", Xtr, ytr, Xte, yte, P_GROUPS7, {"6グループ": P_GROUPS, "4グループ": P_GROUPS4})
        summary["電力需要"] = s
        print(t.round(3).to_string())
        # 評価する年度ごと（同じ学習済みモデルの予測を年度で切る）
        fy = np.where(idx.month >= 4, idx.year, idx.year - 1)
        rows = []
        for y0 in sorted(set(fy)):
            j = np.where(fy == y0)[0]
            v = r2_matrix(yte, P, j)
            vc = coarsen(v, P_GROUPS7, P_GROUPS)
            phi = shapley(vc, len(P_GROUPS))
            for g, p in zip(P_GROUPS, phi):
                rows.append({"年度": int(y0), "時間数": len(j), "グループ": g, "shapley": p, "割合": p / (vc[-1] - vc[0]),
                             "R2全変数": vc[-1]})
        pd.DataFrame(rows).to_csv(RES / "power_by_fiscal_year.csv", index=False)
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    log("終了")
