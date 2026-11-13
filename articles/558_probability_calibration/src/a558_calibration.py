"""558 予測確率が「30%」と出た人のうち、本当に起きるのは何%なのか（正解の分かるデータで較正を確かめる）

架空の会員 30,000人。翌月に解約するかどうかを、本当の確率が分かる式から作る。
4つのモデルで確率を出し、「30%前後」と出た人の実際の解約率、較正曲線、Brier スコア、ECE を比べる。
そのあと Platt（ロジスティック）と isotonic（単調な階段）で較正し直す。
"""
import json
import numpy as np, pandas as pd
import duckdb
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score
from common import save, RES, SQL, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 558
rng = np.random.default_rng(SEED)
SRC = "架空のデータ（作成者が乱数で作成、seed 558）"
N_TR, N_CAL, N_TE = 15000, 5000, 10000


def make(n):
    X = rng.normal(size=(n, 7))
    X[:, 3] = 0.6 * X[:, 0] + 0.8 * X[:, 3]                     # 少し相関のある特徴
    X[:, 5] = X[:, 0] + 0.3 * X[:, 5]                            # ほぼ同じ情報の特徴（本当の確率には使わない）
    X[:, 6] = X[:, 0] + 0.3 * X[:, 6]
    logit = -1.5 + 0.9 * X[:, 0] - 0.7 * X[:, 1] + 0.5 * X[:, 0] * X[:, 1] + 0.5 * X[:, 2] ** 2 + 0.4 * X[:, 3]
    p = 1 / (1 + np.exp(-logit))
    y = (rng.random(n) < p).astype(int)
    return X, y, p


Xtr, ytr, ptr = make(N_TR); Xca, yca, pca = make(N_CAL); Xte, yte, pte = make(N_TE)

# 学習：4つのモデル
idx1 = np.where(ytr == 1)[0]; idx0 = rng.choice(np.where(ytr == 0)[0], len(idx1), replace=False)
und = np.r_[idx1, idx0]
MODELS = {
    "ロジスティック回帰\n（半々に間引いて学習）": (LogisticRegression(max_iter=1000), und),
    "ランダムフォレスト": (RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=SEED, n_jobs=1), None),
    "ナイーブベイズ": (GaussianNB(), None),
    "勾配ブースティング": (HistGradientBoostingClassifier(random_state=SEED), None),
}
pred = {}
for k, (m, ix) in MODELS.items():
    ix = np.arange(N_TR) if ix is None else ix
    m.fit(Xtr[ix], ytr[ix])
    pred[k] = (m.predict_proba(Xca)[:, 1], m.predict_proba(Xte)[:, 1])

EPS = 1e-6


def platt(s_cal, y_cal, s_te):
    z = lambda s: np.log(np.clip(s, EPS, 1 - EPS) / (1 - np.clip(s, EPS, 1 - EPS))).reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(z(s_cal), y_cal)
    return lr.predict_proba(z(s_te))[:, 1]


def iso(s_cal, y_cal, s_te):
    return IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(s_cal, y_cal).predict(s_te)


def ece(p, y, bins=10):
    b = np.minimum((p * bins).astype(int), bins - 1)
    return sum(abs(p[b == k].mean() - y[b == k].mean()) * (b == k).mean() for k in range(bins) if (b == k).any())


def bin30(p, y, ptrue):
    m = (p >= 0.25) & (p < 0.35)
    return dict(n=int(m.sum()), mean_pred=float(p[m].mean()), actual=float(y[m].mean()), true_p=float(ptrue[m].mean()))


rows = []; curves = {}
for k, (sca, ste) in pred.items():
    for how, pt in [("そのまま", ste), ("Platt", platt(sca, yca, ste)), ("isotonic", iso(sca, yca, ste))]:
        b = bin30(pt, yte, pte)
        rows.append(dict(model=k.replace("\n", ""), calib=how, brier=np.mean((pt - yte) ** 2), ece=ece(pt, yte),
                         auc=roc_auc_score(yte, pt), mean_pred=pt.mean(), bin30_n=b["n"], bin30_pred=b["mean_pred"],
                         bin30_actual=b["actual"], bin30_true=b["true_p"], mae_true=np.mean(abs(pt - pte))))
        if how == "そのまま":
            bb = np.minimum((pt * 10).astype(int), 9)
            curves[k] = [(pt[bb == j].mean(), yte[bb == j].mean(), int((bb == j).sum())) for j in range(10) if (bb == j).sum() >= 30]
res = pd.DataFrame(rows); res.round(4).to_csv(RES / "models.csv", index=False)
ref = dict(brier_true=float(np.mean((pte - yte) ** 2)), ece_true=float(ece(pte, yte)), base_rate=float(yte.mean()),
           auc_true=float(roc_auc_score(yte, pte)))

# 較正に使う件数を変える（ランダムフォレストとナイーブベイズ、100回）
rows = []
for k in ["ランダムフォレスト", "ナイーブベイズ"]:
    sca_all, ste = pred[k]
    for nc in [100, 300, 1000, 3000, 5000]:
        e_p, e_i, b_p, b_i = [], [], [], []
        for _ in range(100):
            ix = rng.choice(N_CAL, nc, replace=False)
            pp = platt(sca_all[ix], yca[ix], ste); pi = iso(sca_all[ix], yca[ix], ste)
            e_p.append(ece(pp, yte)); e_i.append(ece(pi, yte)); b_p.append(np.mean((pp - yte) ** 2)); b_i.append(np.mean((pi - yte) ** 2))
        rows.append(dict(model=k, n_cal=nc, ece_platt=np.mean(e_p), ece_iso=np.mean(e_i), brier_platt=np.mean(b_p), brier_iso=np.mean(b_i)))
cs = pd.DataFrame(rows); cs.round(5).to_csv(RES / "by_calib_size.csv", index=False)

# SQL の確認：ナイーブベイズ（そのまま）の予測で、較正表と Brier を DuckDB で計算
kNB = "ナイーブベイズ"
ex = pd.DataFrame({"member_id": np.arange(N_TE), "pred": pred[kNB][1].round(6), "churned": yte})
ex.to_csv(RES / "test_predictions_nb.csv", index=False)
con = duckdb.connect(config={"threads": 1}); con.register("predictions", pd.read_csv(RES / "test_predictions_nb.csv"))
sq = con.execute(open(SQL / "a558_calibration.sql", encoding="utf-8").read()).df(); sq.to_csv(RES / "sql_calibration_table_nb.csv", index=False)
pe = ex.pred.to_numpy(); bins = np.minimum((pe * 10).astype(int), 9)
py_tab = pd.DataFrame({"b": bins, "p": pe, "y": yte}).groupby("b").agg(n=("y", "size"), actual=("y", "mean"))
sql_check = dict(python_brier=float(np.mean((pe - yte) ** 2)), sql_brier=float(sq["brier"].iloc[0]),
                 rows_match=bool(np.allclose(py_tab.actual.to_numpy(), sq.sort_values("bin").actual_rate.to_numpy()) and (py_tab.n.to_numpy() == sq.sort_values("bin").n_members.to_numpy()).all()))

json.dump(dict(ref=ref, sql_check=sql_check, n=dict(train=N_TR, calib=N_CAL, test=N_TE)), open(RES / "a558_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：較正曲線（そのまま）
C = {list(MODELS)[0]: ORANGE, "ランダムフォレスト": GREEN, "ナイーブベイズ": BLUE, "勾配ブースティング": INK}
fig, ax = plt.subplots(figsize=(6.4, 5.6))
ax.plot([0, 1], [0, 1], ls="--", color=GRAY, lw=1); ax.text(0.62, 0.55, "予測どおり", color=GRAY, rotation=40, fontsize=9)
ax.axvspan(0.25, 0.35, color=LIGHT, alpha=0.35, lw=0)
for k, c in curves.items():
    xs, ys, _ = zip(*c); ax.plot(xs, ys, "o-", color=C[k], ms=4, label=k.replace("\n", ""))
ax.set_xlabel("予測した解約の確率（10%ごとに区切った平均）"); ax.set_ylabel("実際に解約した割合")
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.legend(frameon=False, fontsize=8.5, loc="upper left"); ax.set_title("4つのモデルの較正曲線（そのまま）")
save(fig, "a558_reliability.png", SRC + "。テスト用の10,000人。点は30人以上の区間だけ。水色は25〜35%")

# 図2：「30%前後」と出た人の実際の解約率
fig, ax = plt.subplots(figsize=(8.6, 4.3))
ms = list(MODELS); hows = ["そのまま", "Platt", "isotonic"]; col = [GRAY, BLUE, GREEN]; w = 0.26
for j, (h, c) in enumerate(zip(hows, col)):
    v = [res[(res.model == m.replace("\n", "")) & (res.calib == h)].bin30_actual.iloc[0] for m in ms]
    ax.bar(np.arange(4) + (j - 1) * w, v, w, color=c, label=h)
    for i, x in enumerate(v): ax.text(i + (j - 1) * w, x + 0.01, f"{x:.0%}", ha="center", fontsize=8.5)
ax.axhline(0.30, color=ORANGE, ls="--", lw=1.2); ax.text(3.55, 0.305, "30%", color=ORANGE, fontsize=9)
ax.set_xticks(range(4), ms, fontsize=9); ax.set_ylabel("実際に解約した割合"); ax.set_ylim(0, 0.45)
ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left"); ax.set_title("予測が25〜35%だった人のうち、実際に解約した割合")
save(fig, "a558_bin30.png", SRC + "。テスト用の10,000人。較正は別の5,000人で学習")

# 図3：較正に使う件数
fig, ax = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
for a, k in zip(ax, ["ランダムフォレスト", "ナイーブベイズ"]):
    d = cs[cs.model == k]
    a.plot(d.n_cal, d.ece_platt, "o-", color=BLUE, label="Platt"); a.plot(d.n_cal, d.ece_iso, "s-", color=GREEN, label="isotonic")
    e0 = res[(res.model == k) & (res.calib == "そのまま")].ece.iloc[0]
    a.axhline(e0, color=GRAY, ls=":"); a.text(110, e0 + 0.002, f"較正しない {e0:.3f}", color=GRAY, fontsize=8.5)
    a.set_xscale("log"); a.set_xticks(d.n_cal, [f"{v:,}" for v in d.n_cal]); a.set_xlabel("較正に使った人数"); a.set_title(k)
ax[0].set_ylabel("ECE（予測と実際のずれの平均）"); ax[0].legend(frameon=False, fontsize=9); ax[0].set_ylim(0, None)
save(fig, "a558_calib_size.png", SRC + "。各条件100回の平均。テスト用の10,000人で評価")
print(json.dumps(dict(ref=ref, sql_check=sql_check), ensure_ascii=False)); print(res.round(3).to_string()); print(cs.round(4).to_string())
