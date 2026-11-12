"""448 曲線の次数を上げると、データの外の予測はどれだけ暴れるのか
x は 0〜10 に等間隔で30点。1次〜8次の多項式を当て、範囲の中（0〜10）と外（12・15）の誤差を測る。seed 448"""
import json
import numpy as np, pandas as pd
from common import *

rng = np.random.default_rng(448)
REP, N, SD = 2000, 30, 1.0
DEG = list(range(1, 9))
TRUTH = {"本当は直線": lambda x: 2 + 0.5 * x,
         "本当はゆるい曲線": lambda x: 2 + 3 * np.log1p(x)}
X_IN = np.linspace(0, 10, 101)
X_OUT = np.array([11.0, 12.0, 15.0])


def fit_predict(x, y, d, xs):
    # 0〜10 を −1〜1 に直してから当てる（桁あふれを避けるため。当てはまりは同じ）
    c = np.polynomial.polynomial.polyfit((x - 5) / 5, y, d)
    return np.polynomial.polynomial.polyval((np.asarray(xs) - 5) / 5, c)


def cv_degree(x, y, k=5):
    idx = rng.permutation(len(x)); folds = np.array_split(idx, k); best, bd = np.inf, 1
    for d in DEG:
        e = 0.0
        for f in folds:
            tr = np.setdiff1d(idx, f); e += ((fit_predict(x[tr], y[tr], d, x[f]) - y[f]) ** 2).sum()
        if e < best: best, bd = e, d
    return bd


def aic_degree(x, y):
    best, bd = np.inf, 1
    for d in DEG:
        rss = ((fit_predict(x, y, d, x) - y) ** 2).sum(); a = len(x) * np.log(rss / len(x)) + 2 * (d + 2)
        if a < best: best, bd = a, d
    return bd


rows, pick_rows, ex_rows = [], [], []
for name, f in TRUTH.items():
    for n in [N, 100]:
        e_in = np.zeros((REP, len(DEG))); e_out = np.zeros((REP, len(DEG), len(X_OUT))); e_fit = np.zeros((REP, len(DEG)))
        picks = {"確かめ用のデータ（5分割）": [], "AIC": []}; pe = {k: [] for k in picks}
        for r in range(REP):
            x = np.linspace(0, 10, n); y = f(x) + rng.normal(0, SD, n)   # x は等間隔
            for j, d in enumerate(DEG):
                e_fit[r, j] = np.sqrt(((fit_predict(x, y, d, x) - y) ** 2).mean())
                e_in[r, j] = np.sqrt(((fit_predict(x, y, d, X_IN) - f(X_IN)) ** 2).mean())
                e_out[r, j] = np.abs(fit_predict(x, y, d, X_OUT) - f(X_OUT))
            if n == N:
                for k, fn in [("確かめ用のデータ（5分割）", cv_degree), ("AIC", aic_degree)]:
                    d = fn(x, y); picks[k].append(d); pe[k].append(e_out[r, d - 1])
                if r == 0:
                    xs = np.linspace(0, 15, 151)
                    for d in [1, 2, 3, 5, 8]:
                        ex_rows += [dict(truth=name, degree=d, x=round(float(a), 2), pred=float(b), true=float(c)) for a, b, c in zip(xs, fit_predict(x, y, d, xs), f(xs))]
                    pd.DataFrame({"x": x, "y": y}).round(4).to_csv(DATA / f"example_{'line' if '直線' in name else 'curve'}.csv", index=False)
        for j, d in enumerate(DEG):
            rows.append(dict(truth=name, n=n, degree=d, fit_rmse=e_fit[:, j].mean(), in_rmse=np.sqrt((e_in[:, j] ** 2).mean()),
                             **{f"out{int(xo)}_rmse": np.sqrt((e_out[:, j, i] ** 2).mean()) for i, xo in enumerate(X_OUT)},
                             **{f"out{int(xo)}_median": np.median(e_out[:, j, i]) for i, xo in enumerate(X_OUT)},
                             out15_over5=float((e_out[:, j, 2] > 5).mean())))
        if n == N:
            for k in picks:
                p = np.array(picks[k]); e = np.array(pe[k])
                pick_rows.append(dict(truth=name, rule=k, **{f"share_deg{d}": float((p == d).mean()) for d in DEG},
                                      share_deg4plus=float((p >= 4).mean()),
                                      out12_median=float(np.median(e[:, 1])), out15_median=float(np.median(e[:, 2])),
                                      out15_rmse=float(np.sqrt((e[:, 2] ** 2).mean())), out15_over5=float((e[:, 2] > 5).mean())))
res = pd.DataFrame(rows); res["out15_over_in"] = res.out15_rmse / res.in_rmse
res.round(4).to_csv(RES / "error_by_degree.csv", index=False)
pk = pd.DataFrame(pick_rows); pk.round(4).to_csv(RES / "degree_chosen.csv", index=False)
exd = pd.DataFrame(ex_rows); exd.round(4).to_csv(RES / "example_curves.csv", index=False)

q = lambda t, n, c: {int(r.degree): round(float(getattr(r, c)), 3) for r in res[(res.truth == t) & (res.n == n)].itertuples()}
main = dict(rep=REP, n=N, noise_sd=SD,
            **{f"{'line' if '直線' in t else 'curve'}_n{n}": dict(fit_rmse=q(t, n, "fit_rmse"), in_rmse=q(t, n, "in_rmse"), out11_rmse=q(t, n, "out11_rmse"),
                                                                   out12_rmse=q(t, n, "out12_rmse"), out15_rmse=q(t, n, "out15_rmse"), out15_median=q(t, n, "out15_median"),
                                                                   out15_over5=q(t, n, "out15_over5"))
               for t in TRUTH for n in [N, 100]},
            degree_chosen=pk.round(3).to_dict("records"))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

SRC = "架空のデータ（作成者が乱数で作成、seed 448）。x は0〜10に等間隔で30点、誤差の標準偏差1"
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4), sharey=True)
dc = {1: INK, 2: BLUE, 3: GREEN, 5: ORANGE, 8: "#c0392b"}
for ax, (name, f) in zip(axes, TRUTH.items()):
    d0 = pd.read_csv(DATA / f"example_{'line' if '直線' in name else 'curve'}.csv")
    ax.axvspan(10, 15, color="#f2f0ea"); ax.plot(d0.x, d0.y, "o", color=GRAY, ms=4)
    xs = np.linspace(0, 15, 151); ax.plot(xs, f(xs), "--", color=GRAY, lw=1.2, label="本当の形")
    for d in [1, 2, 3, 5, 8]:
        e = exd[(exd.truth == name) & (exd.degree == d)]; ax.plot(e.x, e.pred, color=dc[d], lw=1.4, label=f"{d}次")
    ax.set_ylim(-6, 22); ax.set_title(name); ax.set_xlabel("x（色のついた部分はデータの外）")
axes[0].legend(frameon=False, fontsize=9, ncol=2); axes[0].set_ylabel("y")
fig.suptitle("データのある範囲ではどの次数も近いが、外に出ると高い次数ほど離れていく（1回分の例）", y=1.02)
save(fig, "a448_example_fits.png", SRC)

fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4), sharey=True)
for ax, name in zip(axes, TRUTH):
    d = res[(res.truth == name) & (res.n == N)]
    ax.plot(d.degree, d.fit_rmse, "o:", color=GRAY, label="当てはめに使った点とのずれ")
    ax.plot(d.degree, d.in_rmse, "o-", color=BLUE, label="範囲の中（0〜10）の本当の形とのずれ")
    ax.plot(d.degree, d.out12_rmse, "o-", color=ORANGE, label="範囲の外（x=12）")
    ax.plot(d.degree, d.out15_rmse, "o-", color="#c0392b", label="範囲の外（x=15）")
    ax.set_yscale("log"); ax.set_xlabel("多項式の次数"); ax.set_title(name)
axes[0].set_ylabel("ずれ（RMSE、対数の目盛り）"); axes[0].legend(frameon=False, fontsize=8.5)
fig.suptitle("次数を上げると、当てはめのずれは小さくなり、外の予測のずれは桁で大きくなる", y=1.02)
save(fig, "a448_error_by_degree.png", SRC + "。2,000回")

fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2), sharey=True)
for ax, name in zip(axes, TRUTH):
    w = 0.38
    for i, (k, c) in enumerate([("確かめ用のデータ（5分割）", BLUE), ("AIC", ORANGE)]):
        r = pk[(pk.truth == name) & (pk.rule == k)].iloc[0]
        ax.bar(np.array(DEG) + (i - 0.5) * w, [r[f"share_deg{d}"] * 100 for d in DEG], w, color=c, label=k)
    ax.set_xticks(DEG); ax.set_xlabel("選ばれた次数"); ax.set_title(name)
axes[0].set_ylabel("選ばれた割合（%）"); axes[0].legend(frameon=False, fontsize=9)
fig.suptitle("データの中だけで次数を選ぶと、ときどき高い次数が選ばれる", y=1.02)
save(fig, "a448_degree_chosen.png", SRC + "。2,000回")
print(json.dumps(main, ensure_ascii=False)[:2600])
