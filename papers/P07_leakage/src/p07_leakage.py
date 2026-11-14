"""P07 データの漏れ（leakage）：交差検証の成績が、本番の成績よりよく見える3つの型を、種を固定して作る。
A. 前処理の漏れ：ラベルと無関係な1,000列から、全データで相関の高い列を選んでから交差検証する
B. 時間の漏れ：日ごとの需要（傾きと週の波と自己相関）を、日付を混ぜた5分割で検証する
C. 目的変数の漏れ：「解約したあとに記録される値」（解約手続きの問い合わせ件数）を特徴量に入れる
どれも「交差検証の成績」と「後から来た本番データでの成績」を並べる。
使い方: cd src && python p07_leakage.py
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import KFold, cross_val_score, TimeSeriesSplit
from sklearn.metrics import roc_auc_score, mean_absolute_percentage_error
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
R, FG = HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
REPS = 20
out = []

# A. 前処理の漏れ（ラベルと無関係なデータ。正しい AUC は 0.5）
for r in range(REPS):
    rng = np.random.default_rng(100 + r)
    X = rng.normal(size=(300, 1000)); y = rng.integers(0, 2, 300)
    Xn = rng.normal(size=(300, 1000)); yn = rng.integers(0, 2, 300)          # 後から来る本番データ
    def top20(Xa, ya):
        c = np.abs([np.corrcoef(Xa[:, j], ya)[0, 1] for j in range(Xa.shape[1])])
        return np.argsort(-c)[:20]
    lr = lambda: LogisticRegression(C=1.0, max_iter=2000)
    sel = top20(X, y)                                                        # 漏れあり：全データで列を選ぶ
    cv_leak = cross_val_score(lr(), X[:, sel], y, cv=KFold(5, shuffle=True, random_state=r), scoring="roc_auc").mean()
    aucs = []                                                                # 漏れなし：列の選択も分割の中で
    for tr, te in KFold(5, shuffle=True, random_state=r).split(X):
        s = top20(X[tr], y[tr]); m = lr().fit(X[tr][:, s], y[tr]); aucs.append(roc_auc_score(y[te], m.predict_proba(X[te][:, s])[:, 1]))
    prod = roc_auc_score(yn, lr().fit(X[:, sel], y).predict_proba(Xn[:, sel])[:, 1])
    out += [{"case": "A 前処理の漏れ", "rep": r, "kind": "交差検証（漏れあり）", "score": cv_leak},
            {"case": "A 前処理の漏れ", "rep": r, "kind": "交差検証（漏れなし）", "score": float(np.mean(aucs))},
            {"case": "A 前処理の漏れ", "rep": r, "kind": "本番", "score": prod}]

# B. 時間の漏れ（日ごとの需要。指標は MAPE＝外れの割合。小さいほどよい）
for r in range(REPS):
    rng = np.random.default_rng(200 + r)
    T = 730 + 90
    t = np.arange(T); e = np.zeros(T)
    for i in range(1, T): e[i] = 0.8 * e[i - 1] + rng.normal(0, 6)
    y = 300 + 0.15 * t + 25 * np.sin(2 * np.pi * t / 7) + e
    df = pd.DataFrame({"t": t, "dow": t % 7, "y": y})
    feats = ["t", "dow"]
    hist, fut = df.iloc[:730], df.iloc[730:]
    mk = lambda: lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, random_state=r, num_threads=1, verbose=-1)
    def cv(split):
        errs = []
        for tr, te in split.split(hist):
            m = mk().fit(hist.iloc[tr][feats], hist.iloc[tr].y); errs.append(mean_absolute_percentage_error(hist.iloc[te].y, m.predict(hist.iloc[te][feats])))
        return float(np.mean(errs))
    prod = mean_absolute_percentage_error(fut.y, mk().fit(hist[feats], hist.y).predict(fut[feats]))
    out += [{"case": "B 時間の漏れ", "rep": r, "kind": "交差検証（漏れあり）", "score": cv(KFold(5, shuffle=True, random_state=r))},
            {"case": "B 時間の漏れ", "rep": r, "kind": "交差検証（漏れなし）", "score": cv(TimeSeriesSplit(5, test_size=90))},
            {"case": "B 時間の漏れ", "rep": r, "kind": "本番", "score": float(prod)}]

# C. 目的変数の漏れ（会員の解約。「解約手続きの問い合わせ件数」は、解約が決まってから増える）
for r in range(REPS):
    rng = np.random.default_rng(300 + r)
    def make(n):
        tenure = rng.exponential(24, n); usage = rng.normal(0, 1, n); price_up = rng.integers(0, 2, n)
        logit = -1.5 - 0.03 * tenure - 0.8 * usage + 0.7 * price_up
        churn = rng.random(n) < 1 / (1 + np.exp(-logit))
        inquiries = rng.poisson(np.where(churn, 2.0, 0.1))                    # 解約の手続きで増える（予測する時点では分からない）
        X = pd.DataFrame({"tenure": tenure, "usage": usage, "price_up": price_up, "inquiries": inquiries})
        return X, churn.astype(int)
    X, y = make(5000); Xn, yn = make(5000)
    # 本番では、予測する時点で問い合わせはまだ起きていないので 0 として入ってくる
    Xn_prod = Xn.assign(inquiries=0)
    mk = lambda: lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, random_state=r, num_threads=1, verbose=-1)
    cv_leak = cross_val_score(mk(), X, y, cv=KFold(5, shuffle=True, random_state=r), scoring="roc_auc").mean()
    base = ["tenure", "usage", "price_up"]
    cv_ok = cross_val_score(mk(), X[base], y, cv=KFold(5, shuffle=True, random_state=r), scoring="roc_auc").mean()
    prod_leak = roc_auc_score(yn, mk().fit(X, y).predict_proba(Xn_prod)[:, 1])
    prod_ok = roc_auc_score(yn, mk().fit(X[base], y).predict_proba(Xn[base])[:, 1])
    out += [{"case": "C 目的変数の漏れ", "rep": r, "kind": "交差検証（漏れあり）", "score": cv_leak},
            {"case": "C 目的変数の漏れ", "rep": r, "kind": "交差検証（漏れなし）", "score": cv_ok},
            {"case": "C 目的変数の漏れ", "rep": r, "kind": "本番（漏れありのモデル）", "score": prod_leak},
            {"case": "C 目的変数の漏れ", "rep": r, "kind": "本番（漏れなしのモデル）", "score": prod_ok}]

df = pd.DataFrame(out)
df.round(6).to_csv(R / "sims.csv", index=False, encoding="utf-8")
S = df.groupby(["case", "kind"], sort=False).score.agg(["mean", "std"]).reset_index()
S.round(4).to_csv(R / "summary.csv", index=False, encoding="utf-8")
main = {f"{c}|{k}": round(float(m), 4) for c, k, m in S[["case", "kind", "mean"]].itertuples(index=False)}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), dpi=120)
colors = {"交差検証（漏れあり）": "#b5452b", "交差検証（漏れなし）": "#1f5f8b", "本番": "#2e7d4f",
          "本番（漏れありのモデル）": "#e0a08a", "本番（漏れなしのモデル）": "#2e7d4f"}
labels = {"A 前処理の漏れ": "A 前処理の漏れ（AUC、0.5＝当てずっぽう）", "B 時間の漏れ": "B 時間の漏れ（MAPE、小さいほどよい）",
          "C 目的変数の漏れ": "C 目的変数の漏れ（AUC）"}
for ax, (case, g) in zip(axs, S.groupby("case", sort=False)):
    ax.bar(range(len(g)), g["mean"], yerr=g["std"], color=[colors[k] for k in g.kind], capsize=3)
    ax.set_xticks(range(len(g)), [k.replace("（漏れありのモデル）", "\n漏れあり").replace("（漏れなしのモデル）", "\n漏れなし").replace("（", "\n（") for k in g.kind], fontsize=8)
    for i, (v, sd) in enumerate(zip(g["mean"], g["std"])):
        ax.text(i, v + sd, f"{v:.3f}" if case != "B 時間の漏れ" else f"{v:.1%}", ha="center", va="bottom", fontsize=8.5)
    ax.set_title(labels[case], fontsize=10)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
fig.suptitle("漏れがあると、交差検証は本番よりよく見える（20回の平均と標準偏差）", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "p07_01_leakage.png"); plt.close(fig)
print(S.round(3).to_string())
