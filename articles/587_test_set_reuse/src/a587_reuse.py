"""587 同じテスト用データでモデルの調整を何度もくり返すと、テストの成績はどれだけ楽観的になるか（seed 587）"""
import json
import numpy as np, pandas as pd, duckdb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(587)
SRC = "架空のデータ（作成者が乱数で作成、seed 587）"
P, INFO = 40, 4                       # 特徴40個のうち、予測力があるのは4個
N_TRAIN, N_VAL, N_FRESH = 600, 300, 20000
KMAX, KS, REPS = 200, [1, 5, 20, 50, 100, 200], 40


def make(n, beta):
    X = rng.normal(0, 1, (n, P))
    p = 1 / (1 + np.exp(-(X @ beta - 0.5)))
    return X, rng.binomial(1, p)


def configs():
    out = []
    for _ in range(KMAX):
        k = int(rng.integers(2, 11))
        out.append((np.sort(rng.choice(P, k, replace=False)), float(10 ** rng.uniform(-3, 1))))
    return out


def one(signal, n_test):
    beta = np.zeros(P); beta[:INFO] = 0.35 * signal
    Xtr, ytr = make(N_TRAIN, beta); Xva, yva = make(N_VAL, beta); Xte, yte = make(n_test, beta); Xfr, yfr = make(N_FRESH, beta)
    rows = []
    for cols, C in configs():
        m = LogisticRegression(C=C, max_iter=500).fit(Xtr[:, cols], ytr)
        rows.append([roc_auc_score(yte, m.decision_function(Xte[:, cols])), roc_auc_score(yva, m.decision_function(Xva[:, cols])),
                     roc_auc_score(yfr, m.decision_function(Xfr[:, cols]))])
    a = np.array(rows)
    res = []
    for K in KS:
        i = int(np.argmax(a[:K, 0])); j = int(np.argmax(a[:K, 1]))
        res.append({"K": K, "reuse_test": a[i, 0], "reuse_true": a[i, 2], "val_test": a[j, 0], "val_true": a[j, 2],
                    "best_true": float(a[:K, 2].max())})
    return res


rows = []
for signal, lab in [(0, "none"), (1, "weak")]:
    for n_test in [200, 1000]:
        for r in range(REPS):
            for d in one(signal, n_test):
                rows.append({"signal": lab, "n_test": n_test, "rep": r, **d})
sim = pd.DataFrame(rows); sim.to_csv(RES / "simulation.csv", index=False)
sim["gap_reuse"] = sim.reuse_test - sim.reuse_true
sim["gap_val"] = sim.val_test - sim.val_true
summ = sim.groupby(["signal", "n_test", "K"]).agg(reuse_test=("reuse_test", "mean"), reuse_true=("reuse_true", "mean"),
                                                 gap_reuse=("gap_reuse", "mean"), val_test=("val_test", "mean"),
                                                 val_true=("val_true", "mean"), gap_val=("gap_val", "mean"),
                                                 share_reuse_over=("gap_reuse", lambda x: float((x > 0).mean())),
                                                 best_true=("best_true", "mean")).reset_index().round(4)
summ.to_csv(RES / "summary.csv", index=False)

# 例の1回：予測力のない特徴だけ・テスト200件・200回の調整で選んだモデルのテストAUCを DuckDB の SQL で出し直す
beta = np.zeros(P)
Xtr, ytr = make(N_TRAIN, beta); Xte, yte = make(200, beta)
best = None
for cols, C in configs():
    m = LogisticRegression(C=C, max_iter=500).fit(Xtr[:, cols], ytr)
    s = m.decision_function(Xte[:, cols]); auc = roc_auc_score(yte, s)
    if best is None or auc > best[0]:
        best = (auc, s)
ex = pd.DataFrame({"y": yte, "score": best[1]}); ex.to_csv(DATA / "example_noise_test200.csv", index=False)
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("pred", ex)
auc_sql = float(con.execute(open(SQL / "a587_auc.sql").read()).fetchone()[0])
pd.DataFrame([{"auc_python": best[0], "auc_duckdb": auc_sql, "match": abs(best[0] - auc_sql) < 1e-12}]).to_csv(RES / "sql_example.csv", index=False)

# 図1 くり返した回数と、テストの成績・本当の成績（予測力なし・弱い）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharex=True)
for ax, sig, ttl in [(axs[0], "none", "予測力のある特徴なし（本当のAUCは0.5）"), (axs[1], "weak", "弱い予測力のある特徴4個")]:
    g = summ[(summ.signal == sig) & (summ.n_test == 200)]
    ax.plot(g.K, g.reuse_test, "-o", color=ORANGE, ms=4, label="テストで選んだ：テストの成績")
    ax.plot(g.K, g.reuse_true, "--o", color=ORANGE, ms=4, alpha=0.6, label="テストで選んだ：本当の成績")
    ax.plot(g.K, g.val_test, "-o", color=BLUE, ms=4, label="検証用で選んだ：手つかずのテストの成績")
    ax.plot(g.K, g.val_true, "--o", color=BLUE, ms=4, alpha=0.6, label="検証用で選んだ：本当の成績")
    ax.set_xscale("log"); ax.set_title(ttl, fontsize=11); ax.grid(alpha=0.3); ax.set_xlabel("試した設定の数（対数目盛）")
axs[0].set_ylabel("AUC（40回の平均）"); axs[1].legend(fontsize=8.5, loc="lower right")
fig.suptitle("テスト用データで選ぶほど、テストの成績だけが上がる（テスト200件）", fontsize=13)
save(fig, "a587_by_k.png", "出典：" + SRC)

# 図2 楽観の幅：テスト件数200と1000
fig, ax = plt.subplots(figsize=(9, 4.6))
for sig, nt, c, ls in [("weak", 200, ORANGE, "-"), ("weak", 1000, ORANGE, ":"), ("none", 200, GRAY, "-"), ("none", 1000, GRAY, ":")]:
    g = summ[(summ.signal == sig) & (summ.n_test == nt)]
    ax.plot(g.K, g.gap_reuse, ls, marker="o", ms=4, color=c, label=f"{'予測力なし' if sig == 'none' else '弱い予測力'}・テスト{nt}件")
g = summ[(summ.signal == "weak") & (summ.n_test == 200)]
ax.plot(g.K, g.gap_val, "-", marker="s", ms=4, color=BLUE, label="検証用で選んで手つかずのテストで測る（弱い予測力・テスト200件）")
ax.axhline(0, color=INK, lw=0.8)
ax.set_xscale("log"); ax.set_xlabel("試した設定の数（対数目盛）"); ax.set_ylabel("テストの成績 − 本当の成績（AUC）")
ax.legend(fontsize=8.5); ax.grid(alpha=0.3); ax.set_title("楽観の幅は、試した数とともに増え、テストが大きいほど小さい")
save(fig, "a587_gap.png", "出典：" + SRC)

# 図3 200回試したときの分布（弱い予測力・テスト200件）
g = sim[(sim.signal == "weak") & (sim.n_test == 200) & (sim.K == 200)]
fig, ax = plt.subplots(figsize=(9, 4.4))
bins = np.linspace(-0.12, 0.14, 27)
ax.hist(g.gap_reuse, bins=bins, color=ORANGE, alpha=0.7, label="テストで選んだ")
ax.hist(g.gap_val, bins=bins, color=BLUE, alpha=0.6, label="検証用で選んで、手つかずのテストで測った")
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("テストの成績 − 本当の成績（AUC）"); ax.set_ylabel("回数（40回中）"); ax.legend(fontsize=9)
ax.set_title(f"200回試したあと（弱い予測力・テスト200件）：テストで選ぶと40回中{int((g.gap_reuse > 0).sum())}回で上振れ")
save(fig, "a587_dist.png", "出典：" + SRC)

key = summ.set_index(["signal", "n_test", "K"])
main = {"summary": summ.to_dict("records"), "sql": pd.read_csv(RES / "sql_example.csv").to_dict("records")}
json.dump(main, open(RES / "a587_main.json", "w"), ensure_ascii=False, indent=1)
print(summ.to_string())
print(pd.read_csv(RES / "sql_example.csv").to_string())
