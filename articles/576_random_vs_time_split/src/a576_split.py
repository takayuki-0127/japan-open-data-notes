"""576 時系列をランダムに分けて確かめると、時間順に分けた場合より成績はどれだけ良く見えるか（seed 576）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold
from common import RES, FIG, SQL, save, BLUE, ORANGE, GRAY, INK, GREEN

N_DAYS, N_FUT, N_SIM = 1095, 180, 60
PHIS = [0.0, 0.5, 0.9]
SRC = "架空のデータ（作成者が乱数で作成、seed 576）"


def make_series(rng, phi):
    n = N_DAYS + N_FUT + 7
    t = np.arange(n)
    dow = t % 7
    week = np.array([0, -2, -2, -1, 1, 6, 4])[dow]          # 曜日の形（金土が多い）
    trend = 100 + 10 * t / 365                             # 年に+10
    e = np.zeros(n)
    sd = 6 * np.sqrt(1 - phi ** 2)                          # 全体の散らばりはφによらず6
    e[0] = rng.normal(0, 6)
    for i in range(1, n):
        e[i] = phi * e[i - 1] + rng.normal(0, sd)
    y = trend + week + e
    return pd.DataFrame({"t": t, "dow": dow, "y": y})


def features(df):
    d = df.copy()
    d["lag1"] = d["y"].shift(1)
    d["lag7"] = d["y"].shift(7)
    d = d.dropna().reset_index(drop=True)
    X = np.column_stack([d["t"], d["lag1"], d["lag7"], np.eye(7)[d["dow"]]])
    return d, X, d["y"].to_numpy()


def model(kind, seed):
    if kind == "rf":
        return RandomForestRegressor(n_estimators=60, min_samples_leaf=3, random_state=seed, n_jobs=1)
    return LinearRegression()


def mae(a, b):
    return float(np.mean(np.abs(a - b)))


def one(rng, phi, kind, seed, keep=False):
    df = make_series(rng, phi)
    d, X, y = features(df)
    n_tr = N_DAYS - 7
    Xa, ya, Xf, yf = X[:n_tr], y[:n_tr], X[n_tr:], y[n_tr:]
    out = {}
    preds = []
    # 1 ランダム5分割
    errs = []
    for k, (tr, te) in enumerate(KFold(5, shuffle=True, random_state=seed).split(Xa)):
        m = model(kind, seed).fit(Xa[tr], ya[tr]); p = m.predict(Xa[te]); errs.append(mae(p, ya[te]))
        if keep: preds += [("random_5fold", int(i), float(ya[i]), float(v)) for i, v in zip(te, p)]
    out["random"] = float(np.mean(errs))
    # 2 時間順：最後の20%を確かめ用
    c = int(n_tr * 0.8)
    m = model(kind, seed).fit(Xa[:c], ya[:c]); p = m.predict(Xa[c:]); out["holdout"] = mae(p, ya[c:])
    if keep: preds += [("time_holdout", int(i), float(ya[i]), float(v)) for i, v in zip(range(c, n_tr), p)]
    # 3 ずらした窓：最後の5か月を30日ずつ、その前までで学習
    errs = []
    for j in range(5):
        s = n_tr - 150 + 30 * j
        m = model(kind, seed).fit(Xa[:s], ya[:s]); p = m.predict(Xa[s:s + 30]); errs.append(mae(p, ya[s:s + 30]))
        if keep: preds += [("rolling_origin", int(i), float(ya[i]), float(v)) for i, v in zip(range(s, s + 30), p)]
    out["rolling"] = float(np.mean(errs))
    # 正解：全期間で学習して、まだ見ていない次の180日
    m = model(kind, seed).fit(Xa, ya); out["future"] = mae(m.predict(Xf), yf)
    return out, preds


rows = []
example = None
for phi in PHIS:
    for kind in ["rf", "lin"]:
        rng = np.random.default_rng([576, int(phi * 10), 0 if kind == "rf" else 1])
        for s in range(N_SIM):
            keep = (phi == 0.5 and kind == "rf" and s == 0)
            o, pr = one(rng, phi, kind, 576 + s, keep)
            o.update(phi=phi, model=kind, sim=s); rows.append(o)
            if keep: example = pr
sim = pd.DataFrame(rows)
sim.to_csv(RES / "simulation.csv", index=False)
for c in ["random", "holdout", "rolling"]:
    sim[c + "_ratio"] = sim[c] / sim["future"]
summ = sim.groupby(["model", "phi"]).agg(
    random=("random", "mean"), holdout=("holdout", "mean"), rolling=("rolling", "mean"), future=("future", "mean"),
    random_ratio=("random_ratio", "median"), holdout_ratio=("holdout_ratio", "median"), rolling_ratio=("rolling_ratio", "median"),
    random_under=("random_ratio", lambda x: float((x < 1).mean())), rolling_under=("rolling_ratio", lambda x: float((x < 1).mean())),
).reset_index()
summ.to_csv(RES / "summary.csv", index=False)

# 例の1回の予測（DuckDB で MAE を集計し直す）
ex = pd.DataFrame(example, columns=["method", "row_id", "actual", "pred"])
ex.to_csv(RES / "example_predictions.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1")
con.register("preds", ex)
sql_res = con.execute(open(SQL / "a576_mae.sql", encoding="utf-8").read()).df()
sql_res.to_csv(RES / "sql_mae.csv", index=False)
py_res = ex.assign(ae=(ex.actual - ex.pred).abs()).groupby("method").ae.mean()
ok = all(abs(py_res[r.method] - r.mae) < 1e-9 for r in sql_res.itertuples())

# 図1：方法ごとの「推定MAE ÷ 本当の先のMAE」（ランダムフォレスト）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
lab = {"random": "ランダム5分割", "holdout": "時間順（最後の20%）", "rolling": "ずらした窓"}
col = {"random": ORANGE, "holdout": BLUE, "rolling": GREEN}
for ax, kind, ttl in zip(axes, ["rf", "lin"], ["ランダムフォレスト", "線形回帰"]):
    s = summ[summ.model == kind]
    x = np.arange(len(PHIS)); w = 0.26
    for i, c in enumerate(["random", "holdout", "rolling"]):
        v = s[c + "_ratio"].to_numpy()
        ax.bar(x + (i - 1) * w, v, w, color=col[c], label=lab[c])
        for xx, vv in zip(x + (i - 1) * w, v): ax.text(xx, vv + 0.01, f"{vv:.2f}", ha="center", fontsize=8.5)
    ax.axhline(1, color=INK, lw=1, ls="--")
    ax.set_xticks(x, [f"自己相関 {p}" for p in PHIS]); ax.set_title(ttl)
axes[0].set_ylabel("確かめた誤差 ÷ 本当の先の誤差（中央値）")
axes[0].legend(fontsize=8.5, loc="lower left")
save(fig, "a576_ratio.png", SRC + "。1未満は、成績を良く見積もっている")

# 図2：ランダムフォレスト・自己相関0.9 の1回ずつの分布
fig, ax = plt.subplots(figsize=(8, 4))
s = sim[(sim.model == "rf") & (sim.phi == 0.9)]
bins = np.linspace(0.2, 1.8, 33)
for c in ["random", "rolling"]:
    ax.hist(s[c + "_ratio"], bins=bins, color=col[c], alpha=0.75, label=lab[c])
ax.axvline(1, color=INK, lw=1, ls="--")
ax.set_xlabel("確かめた誤差 ÷ 本当の先の誤差"); ax.set_ylabel("回数（60回中）")
ax.set_title("ランダムフォレスト・自己相関0.9：60回の分布"); ax.legend(fontsize=9)
save(fig, "a576_dist.png", SRC)

# 図3：例の1回、ランダム分割で当てている日と、先の180日
df = make_series(np.random.default_rng([576, 5, 0]), 0.5)
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df.t, df.y, color=GRAY, lw=0.6)
ax.axvspan(N_DAYS, N_DAYS + N_FUT, color=ORANGE, alpha=0.12)
ax.text(N_DAYS + 5, df.y.max(), "本当に当てたい\n先の180日", color=ORANGE, fontsize=9, va="top")
ax.axvspan(int((N_DAYS - 7) * 0.8) + 7, N_DAYS, color=BLUE, alpha=0.10)
ax.text(int((N_DAYS - 7) * 0.8) + 12, df.y.min(), "時間順の確かめ用", color=BLUE, fontsize=9)
ax.set_xlabel("日（0〜1,281日目）"); ax.set_ylabel("値")
ax.set_title("時間順の確かめ用の期間と、本当に当てたい先の180日")
save(fig, "a576_series.png", SRC + "。自己相関0.5の例")

main = {"n_sim": N_SIM, "n_days": N_DAYS, "n_future": N_FUT, "sql_matches_python": ok,
        "summary": summ.round(4).to_dict(orient="records")}
json.dump(main, open(RES / "a576_main.json", "w"), ensure_ascii=False, indent=1)
print(summ.round(3).to_string()); print("sql ok", ok)
