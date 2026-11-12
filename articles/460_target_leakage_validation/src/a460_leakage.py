"""460 予測に「答えが漏れた列」が混ざると、確かめの成績はどれだけ良く見え、本番でどれだけ落ちるか
架空の解約の予測データ。漏れを3種類入れ、漏れのある確かめ方・時点を守った確かめ方・本番の成績（AUC）を比べる。seed 460"""
import json
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 460
N = 20000                                    # 学習に使う顧客の数（本番も同じ数）
BASE = ["tenure_months", "monthly_fee", "usage_trend", "tickets_90d", "pay_fail_90d", "days_since_login_t0"]
BASE_JA = {"tenure_months": "契約からの月数", "monthly_fee": "月額", "usage_trend": "利用の増減", "tickets_90d": "問い合わせ（90日）",
           "pay_fail_90d": "支払いの失敗（90日）", "days_since_login_t0": "最後のログインからの日数（予測の時点）"}
SRC = "架空の解約データ（作成者が乱数で作成、seed 460）"


def make(rng, n, k_agency=500):
    """予測の時点 t0 で分かる6列と、そのあと90日のうちに解約したか（churn）"""
    d = pd.DataFrame({
        "tenure_months": rng.integers(1, 97, n), "monthly_fee": rng.choice([980, 1980, 2980, 4980], n, p=[0.3, 0.35, 0.25, 0.1]),
        "usage_trend": rng.normal(0, 1, n), "tickets_90d": rng.poisson(0.6, n), "pay_fail_90d": rng.binomial(2, 0.06, n),
        "days_since_login_t0": np.minimum(rng.exponential(12, n), 120).round(0)})
    d["agency"] = rng.integers(0, k_agency, n)                       # 申込みの窓口
    ag = rng.normal(0, 0.25, k_agency)                               # 窓口ごとの本当の違い（小さい）
    z = (-2.3 - 0.012 * d.tenure_months + 0.00012 * d.monthly_fee - 0.55 * d.usage_trend + 0.25 * d.tickets_90d
         + 0.8 * d.pay_fail_90d + 0.02 * d.days_since_login_t0 + ag[d.agency] + rng.normal(0, 0.6, n))
    d["churn"] = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)
    d["churn_day"] = np.where(d.churn == 1, rng.integers(1, 91, n), 0)      # 解約した日（t0 からの日数）
    return d


def add_future(d, rng, strength):
    """漏れ①：あとの時点の情報。データを取り出した日（t0+90日）の「最後のログインからの日数」。
    strength の割合の行だけが取り出し日の値で、残りは予測の時点の値"""
    later = np.where(d.churn == 1, d.days_since_login_t0 + d.churn_day * 0 + (90 - d.churn_day) + rng.integers(0, 15, len(d)),
                     np.minimum(rng.exponential(12, len(d)), 120).round(0))   # 続けている人は、取り出し日でもふつうに使っている
    use = rng.random(len(d)) < strength
    return np.where(use, later, d.days_since_login_t0)


def auc_cv(X, y, enc=None, model="gb", seed=0, scale_inside=None):
    """5つに分けて確かめる。enc=(窓口の列, 'leak'|'oof') のとき、窓口ごとの解約率の列を足す"""
    skf = StratifiedKFold(5, shuffle=True, random_state=seed); out = []
    for tr, va in skf.split(X, y):
        Xtr, Xva = X.iloc[tr].copy(), X.iloc[va].copy()
        if enc is not None:
            ag, mode = enc
            if mode == "oof":                                       # 学習側だけで率を出す
                rate = pd.Series(y[tr]).groupby(ag[tr]).mean(); prior = y[tr].mean()
                Xtr["agency_rate"] = pd.Series(ag[tr]).map(rate).values; Xva["agency_rate"] = pd.Series(ag[va]).map(rate).fillna(prior).values
        m = fit(Xtr, y[tr], model, seed)
        out.append(roc_auc_score(y[va], m.predict_proba(Xva)[:, 1]))
    return float(np.mean(out))


def fit(X, y, model="gb", seed=0):
    if model == "gb":
        return HistGradientBoostingClassifier(max_iter=120, learning_rate=0.08, max_leaf_nodes=15, l2_regularization=1.0, random_state=seed).fit(X, y)
    return LogisticRegression(max_iter=2000, C=1.0).fit((X - X.mean()) / X.std(), y)


def rank_of(m, X, y, col, seed=0):
    pi = permutation_importance(m, X, y, scoring="roc_auc", n_repeats=3, random_state=seed)
    order = np.argsort(-pi.importances_mean); return int(np.where(X.columns[order] == col)[0][0]) + 1, float(pi.importances_mean[list(X.columns).index(col)])


def one_run(seed, k_agency=500, strength=1.0, n=N):
    rng = np.random.default_rng(seed)
    tr = make(rng, n, k_agency); pr = make(rng, n, k_agency)                 # 学習用と本番（同じ作り方、別の顧客）
    # 本番の窓口の違いは学習用と同じ（同じ窓口）にするため、作り直す
    rng2 = np.random.default_rng(seed + 10_000); ag = rng2.normal(0, 0.25, k_agency)
    def relabel(d):
        z = (-2.3 - 0.012 * d.tenure_months + 0.00012 * d.monthly_fee - 0.55 * d.usage_trend + 0.25 * d.tickets_90d
             + 0.8 * d.pay_fail_90d + 0.02 * d.days_since_login_t0 + ag[d.agency] + rng2.normal(0, 0.6, len(d)))
        d["churn"] = (rng2.random(len(d)) < 1 / (1 + np.exp(-z))).astype(int); d["churn_day"] = np.where(d.churn == 1, rng2.integers(1, 91, len(d)), 0); return d
    tr, pr = relabel(tr), relabel(pr)
    y, yp = tr.churn.values, pr.churn.values
    res = {"churn_rate": float(y.mean())}
    # 漏れなし（基準）
    res["base_cv"] = auc_cv(tr[BASE], y, seed=seed); mb = fit(tr[BASE], y, seed=seed); res["base_prod"] = roc_auc_score(yp, mb.predict_proba(pr[BASE])[:, 1])
    # 漏れ①：あとの時点の情報
    X1 = tr[BASE].copy(); X1["days_since_login_extract"] = add_future(tr, rng, strength)
    res["future_cv"] = auc_cv(X1, y, seed=seed); m1 = fit(X1, y, seed=seed)
    P1 = pr[BASE].copy(); P1["days_since_login_extract"] = pr.days_since_login_t0          # 本番では、予測の時点の値しかない
    res["future_prod"] = roc_auc_score(yp, m1.predict_proba(P1)[:, 1])
    res["future_rank"], res["future_imp"] = rank_of(m1, X1.iloc[:5000], y[:5000], "days_since_login_extract", seed)
    # 漏れ②：答えから作った集計値（窓口ごとの解約率を、確かめに使う行も入れて出す）
    rate_all = tr.groupby("agency").churn.mean()
    X2 = tr[BASE].copy(); X2["agency_rate"] = tr.agency.map(rate_all).values
    res["agg_cv"] = auc_cv(X2, y, seed=seed); m2 = fit(X2, y, seed=seed)
    P2 = pr[BASE].copy(); P2["agency_rate"] = pr.agency.map(rate_all).fillna(y.mean()).values   # 本番の顧客は、率の計算に入っていない
    res["agg_prod"] = roc_auc_score(yp, m2.predict_proba(P2)[:, 1])
    res["agg_rank"], res["agg_imp"] = rank_of(m2, X2.iloc[:5000], y[:5000], "agency_rate", seed)
    res["agg_cv_proper"] = auc_cv(tr[BASE], y, enc=(tr.agency.values, "oof"), seed=seed)       # 分けたあとで率を出す
    # 漏れ③：分ける前に全体でそろえた値（平均と標準偏差を全部の行で出してから分ける）。線形のモデルで比べる
    Z = (tr[BASE] - tr[BASE].mean()) / tr[BASE].std()
    skf = StratifiedKFold(5, shuffle=True, random_state=seed); a, b = [], []
    for i, j in skf.split(Z, y):
        a.append(roc_auc_score(y[j], LogisticRegression(max_iter=2000).fit(Z.iloc[i], y[i]).predict_proba(Z.iloc[j])[:, 1]))
        mu, sd = tr[BASE].iloc[i].mean(), tr[BASE].iloc[i].std()
        b.append(roc_auc_score(y[j], LogisticRegression(max_iter=2000).fit((tr[BASE].iloc[i] - mu) / sd, y[i]).predict_proba((tr[BASE].iloc[j] - mu) / sd)[:, 1]))
    res["scale_cv_leak"], res["scale_cv_proper"] = float(np.mean(a)), float(np.mean(b))
    res["scale_prod"] = roc_auc_score(yp, LogisticRegression(max_iter=2000).fit(Z, y).predict_proba((pr[BASE] - tr[BASE].mean()) / tr[BASE].std())[:, 1])
    return res, tr


def select_before_split(seed, n=2000, p_noise=500, k=10):
    """漏れ③の別の形：分ける前に、全部の行で「答えと関係の強い列」を選ぶ。列はどれも答えと無関係な乱数"""
    rng = np.random.default_rng(seed); X = rng.standard_normal((n, p_noise)); y = (rng.random(n) < 0.2).astype(int); Xp = rng.standard_normal((n, p_noise)); yp = (rng.random(n) < 0.2).astype(int)
    def top(Xa, ya): return np.argsort(-np.abs((Xa - Xa.mean(0)).T @ (ya - ya.mean())))[:k]
    skf = StratifiedKFold(5, shuffle=True, random_state=seed); leak, proper = [], []
    sel_all = top(X, y)
    for i, j in skf.split(X, y):
        leak.append(roc_auc_score(y[j], LogisticRegression(max_iter=1000).fit(X[i][:, sel_all], y[i]).predict_proba(X[j][:, sel_all])[:, 1]))
        s = top(X[i], y[i]); proper.append(roc_auc_score(y[j], LogisticRegression(max_iter=1000).fit(X[i][:, s], y[i]).predict_proba(X[j][:, s])[:, 1]))
    prod = roc_auc_score(yp, LogisticRegression(max_iter=1000).fit(X[:, sel_all], y).predict_proba(Xp[:, sel_all])[:, 1])
    return float(np.mean(leak)), float(np.mean(proper)), float(prod)


def main():
    runs = []
    for r in range(5):
        res, tr = one_run(SEED + r); res["rep"] = r; runs.append(res)
        if r == 0:
            ex = tr.head(3000).copy(); ex["days_since_login_extract"] = add_future(tr, np.random.default_rng(SEED), 1.0)[:3000]
            ex["agency_rate_all_rows"] = tr.agency.map(tr.groupby("agency").churn.mean()).values[:3000].round(4)
            ex.to_csv(DATA / "example_customers.csv", index=False)
    R = pd.DataFrame(runs); R.round(5).to_csv(RES / "main_runs.csv", index=False); M = R.mean(numeric_only=True)
    # 強さを変える
    rows = []
    for s in (0.1, 0.25, 0.5, 1.0):
        for r in range(3):
            res, _ = one_run(SEED + 100 + r, strength=s); rows.append(dict(kind="あとの時点の情報", strength=f"{int(s*100)}%の行", x=s, cv=res["future_cv"], prod=res["future_prod"], base_prod=res["base_prod"], rank=res["future_rank"]))
    for k in (2000, 500, 100, 20):
        for r in range(3):
            res, _ = one_run(SEED + 200 + r, k_agency=k); rows.append(dict(kind="答えから作った集計値", strength=f"窓口{k}（1窓口{N//k}人）", x=N // k, cv=res["agg_cv"], prod=res["agg_prod"], base_prod=res["base_prod"], rank=res["agg_rank"], cv_proper=res["agg_cv_proper"]))
    S = pd.DataFrame(rows); S.round(5).to_csv(RES / "strength_runs.csv", index=False)
    Sm = S.groupby(["kind", "strength", "x"], sort=False).mean(numeric_only=True).reset_index(); Sm.round(4).to_csv(RES / "strength_mean.csv", index=False)
    sel = pd.DataFrame([dict(zip(("cv_leak", "cv_proper", "prod"), select_before_split(SEED + 300 + r))) for r in range(20)]); sel.round(4).to_csv(RES / "select_before_split.csv", index=False)

    main_js = dict(mean={k: round(float(v), 4) for k, v in M.items()}, sd={k: round(float(v), 4) for k, v in R.std(numeric_only=True).items()},
                   strength=Sm.round(4).to_dict("records"), select_before_split={k: round(float(v), 4) for k, v in sel.mean().items()},
                   select_before_split_sd={k: round(float(v), 4) for k, v in sel.std().items()})
    json.dump(main_js, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：確かめの成績と本番の成績
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    labs = ["漏れなし", "① あとの時点の情報", "② 答えから作った集計値", "③ 分ける前に全体で\nそろえた値（線形）", "③' 分ける前に列を\n選ぶ（乱数の列）"]
    cv = [M.base_cv, M.future_cv, M.agg_cv, M.scale_cv_leak, sel.cv_leak.mean()]; pp = [M.base_cv, M.base_cv, M.agg_cv_proper, M.scale_cv_proper, sel.cv_proper.mean()]
    pd_ = [M.base_prod, M.future_prod, M.agg_prod, M.scale_prod, sel["prod"].mean()]
    x = np.arange(5); w = 0.26
    for k, (v, col, lab) in enumerate(((cv, ORANGE, "漏れのある確かめ方"), (pp, LIGHT, "時点を守った確かめ方"), (pd_, BLUE, "本番（別の顧客）"))):
        ax.bar(x + (k - 1) * w, v, w, color=col, label=lab)
        for xi, vi in zip(x + (k - 1) * w, v): ax.text(xi, vi + 0.006, f"{vi:.3f}", ha="center", fontsize=8)
    ax.axhline(0.5, color=GRAY, lw=0.8, ls=":"); ax.set_ylim(0.45, 1.05); ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylabel("AUC（0.5＝当てずっぽう、1＝完全）"); ax.set_title("漏れの種類ごとの、確かめの成績と本番の成績", loc="left"); ax.legend(fontsize=9, frameon=False, ncol=3, loc="upper right")
    fig.tight_layout(); save(fig, "a460_cv_vs_production.png", SRC)

    # 図2：強さを変える
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3), sharey=True)
    for a, kind, xl in ((ax[0], "あとの時点の情報", "取り出した日の値になっている行の割合"), (ax[1], "答えから作った集計値", "窓口の数（かっこ内は1窓口あたりの人数）")):
        s = Sm[Sm.kind == kind]; xx = np.arange(len(s))
        a.plot(xx, s.cv, "-o", color=ORANGE, lw=1.8, label="漏れのある確かめ方"); a.plot(xx, s["prod"], "-o", color=BLUE, lw=1.8, label="本番")
        a.plot(xx, s.base_prod, "--", color=GRAY, lw=1.2, label="漏れなしのモデルの本番")
        if kind == "答えから作った集計値": a.plot(xx, s.cv_proper, ":o", color=GREEN, lw=1.4, ms=4, label="分けたあとで率を出す確かめ方")
        for xi, c, p in zip(xx, s.cv, s["prod"]): a.text(xi, c + 0.012, f"{c:.2f}", ha="center", fontsize=8, color=ORANGE); a.text(xi, p - 0.03, f"{p:.2f}", ha="center", fontsize=8, color=BLUE)
        a.set_xticks(xx); a.set_xticklabels([t.replace("（", "\n（") for t in s.strength], fontsize=8.5); a.set_xlabel(xl); a.set_title(kind, loc="left")
    ax[0].set_ylabel("AUC"); ax[0].set_ylim(0.52, 1.0); ax[0].legend(fontsize=8, frameon=False, loc="upper left"); ax[1].legend(fontsize=8, frameon=False, loc="upper right")
    fig.tight_layout(); save(fig, "a460_strength.png", SRC)

    # 図3：漏れた列の重要度
    res0, tr = one_run(SEED)
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.2))
    for a, (col, ja, ttl) in zip(ax, (("days_since_login_extract", "最後のログインからの日数（取り出した日）", "① あとの時点の情報"), ("agency_rate", "窓口ごとの解約率（全部の行で計算）", "② 答えから作った集計値"))):
        X = tr[BASE].copy()
        X[col] = add_future(tr, np.random.default_rng(SEED + 7), 1.0) if col.startswith("days") else tr.agency.map(tr.groupby("agency").churn.mean()).values
        m = fit(X, tr.churn.values, seed=SEED); pi = permutation_importance(m, X.iloc[:5000], tr.churn.values[:5000], scoring="roc_auc", n_repeats=3, random_state=SEED)
        o = np.argsort(pi.importances_mean); names = [BASE_JA.get(c, ja) for c in X.columns[o]]
        a.barh(range(len(o)), pi.importances_mean[o], color=[ORANGE if c == col else LIGHT for c in X.columns[o]])
        a.set_yticks(range(len(o))); a.set_yticklabels(names, fontsize=8.5); a.set_xlabel("その列をかき混ぜたときの AUC の下がり方"); a.set_title(ttl, loc="left")
    fig.suptitle("漏れた列（オレンジ）は、重要度でどこに出るか", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(); save(fig, "a460_importance.png", SRC)
    print(json.dumps(main_js, ensure_ascii=False, indent=0, default=float))


if __name__ == "__main__":
    main()
