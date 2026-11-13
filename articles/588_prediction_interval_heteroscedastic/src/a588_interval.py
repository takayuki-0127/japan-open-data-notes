"""588 散らばりが水準で変わるデータで、予測の区間を「残差の標準偏差×2」で作ると、何%の回が外れるか（seed 588）"""
import json
import numpy as np, pandas as pd, duckdb
from sklearn.linear_model import QuantileRegressor
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(588)
SRC = "架空のデータ（作成者が乱数で作成、seed 588）"
N, NNEW, REPS = 1000, 20000, 30
METH = {"const": "残差の標準偏差×2（一定幅）", "log": "対数で作って戻す", "quant": "分位点回帰（2.5%と97.5%）"}


def make(n, hetero):
    x = rng.uniform(1, 10, n)               # 例：店の売場面積（百㎡）
    mu = 20 + 10 * x                        # 平均の売上（万円/日）
    sd = 0.15 * mu if hetero else np.full(n, 0.15 * 75)   # 散らばりが水準に比例／一定（平均的な大きさにそろえる）
    return x, mu + sd * rng.standard_normal(n)


def fit(x, y):
    X = np.c_[np.ones_like(x), x]
    b = np.linalg.lstsq(X, y, rcond=None)[0]; s = np.std(y - X @ b, ddof=2)
    ly = np.log(y); bl = np.linalg.lstsq(X, ly, rcond=None)[0]; sl = np.std(ly - X @ bl, ddof=2)
    q = {a: QuantileRegressor(quantile=a, alpha=0, solver="highs").fit(x[:, None], y) for a in (0.025, 0.975)}

    def band(xn):
        Xn = np.c_[np.ones_like(xn), xn]
        return {"const": (Xn @ b - 2 * s, Xn @ b + 2 * s),
                "log": (np.exp(Xn @ bl - 2 * sl), np.exp(Xn @ bl + 2 * sl)),
                "quant": (q[0.025].predict(xn[:, None]), q[0.975].predict(xn[:, None]))}
    return band, s


rows, cover = [], []
for hetero in [True, False]:
    for r in range(REPS):
        x, y = make(N, hetero); band, s = fit(x, y)
        xn, yn = make(NNEW, hetero); B = band(xn)
        dec = np.minimum((xn - 1) // 0.9, 9).astype(int)       # 面積を10等分した帯
        for m, (lo, hi) in B.items():
            miss = (yn < lo) | (yn > hi)
            rows.append({"hetero": hetero, "rep": r, "method": m, "miss": float(miss.mean()), "width": float((hi - lo).mean())})
            for d in range(10):
                k = dec == d
                cover.append({"hetero": hetero, "rep": r, "method": m, "band": d, "miss": float(miss[k].mean()),
                              "miss_low": float((yn[k] < lo[k]).mean()), "miss_high": float((yn[k] > hi[k]).mean()),
                              "width": float((hi[k] - lo[k]).mean())})
sim = pd.DataFrame(rows); sim.to_csv(RES / "simulation.csv", index=False)
cv = pd.DataFrame(cover)
byband = cv.groupby(["hetero", "method", "band"])[["miss", "miss_low", "miss_high", "width"]].mean().reset_index().round(4)
byband.to_csv(RES / "miss_by_band.csv", index=False)
overall = sim.groupby(["hetero", "method"])[["miss", "width"]].mean().reset_index().round(4)
overall.to_csv(RES / "overall.csv", index=False)

# 例の1回（散らばりが水準に比例）：新しいデータの外れを、帯ごとに DuckDB の SQL で数え直す
x, y = make(N, True); band, s = fit(x, y)
xn, yn = make(5000, True); lo, hi = band(xn)["const"]
ex = pd.DataFrame({"area": xn.round(4), "sales": yn.round(4), "lo": lo.round(4), "hi": hi.round(4)})
ex.to_csv(DATA / "example_new_const.csv", index=False)
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("pred", ex)
sq = con.execute(open(SQL / "a588_miss_by_band.sql").read()).df()
dec = np.minimum((ex.area.values - 1) // 0.9, 9).astype(int)
py = pd.Series(((ex.sales < ex.lo) | (ex.sales > ex.hi)).values).groupby(dec).mean().values
sq["miss_python"] = py; sq["match"] = np.abs(sq.miss_rate - py) < 1e-12
sq.to_csv(RES / "sql_example.csv", index=False)

mid = 1.45 + 0.9 * np.arange(10)
# 図1 帯ごとの外れの割合
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, h, ttl in [(axs[0], True, "散らばりが水準に比例するデータ"), (axs[1], False, "散らばりが一定のデータ")]:
    for m, c in [("const", ORANGE), ("log", BLUE), ("quant", GREEN)]:
        g = byband[(byband.hetero == h) & (byband.method == m)]
        ax.plot(mid, g.miss * 100, "-o", color=c, ms=4, label=METH[m])
    ax.axhline(4.55, color=INK, lw=0.8, ls=":")
    ax.set_title(ttl, fontsize=11); ax.set_xlabel("売場面積（百㎡）"); ax.grid(alpha=0.3)
axs[0].set_ylabel("区間から外れた割合（%）"); axs[0].legend(fontsize=9)
fig.suptitle("一定幅の区間は、小さい店では外れず、大きい店でよく外れる（各30回の平均）", fontsize=13, y=1.03)
save(fig, "a588_miss_by_band.png", "出典：" + SRC + "。点線は±2標準偏差の名目の外れ4.6%")

# 図2 データと3つの区間（例の1回）
x, y = make(600, True); band, s = fit(x, y)
xs = np.linspace(1, 10, 100); B = band(xs)
fig, ax = plt.subplots(figsize=(9, 5))
ax.scatter(x, y, s=6, color=GRAY, alpha=0.5)
for m, c in [("const", ORANGE), ("log", BLUE), ("quant", GREEN)]:
    ax.plot(xs, B[m][0], color=c, lw=1.6, label=METH[m]); ax.plot(xs, B[m][1], color=c, lw=1.6)
ax.set_xlabel("売場面積（百㎡）"); ax.set_ylabel("1日の売上（万円）"); ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=0.3)
ax.set_title("一定幅の区間（橙）は、散らばりの広がりについていけない")
save(fig, "a588_bands.png", "出典：" + SRC)

# 図3 区間の幅（散らばり比例）
fig, ax = plt.subplots(figsize=(9, 4.4))
for m, c in [("const", ORANGE), ("log", BLUE), ("quant", GREEN)]:
    g = byband[(byband.hetero) & (byband.method == m)]
    ax.plot(mid, g.width, "-o", color=c, ms=4, label=METH[m])
tw = 2 * 1.96 * 0.15 * (20 + 10 * mid)
ax.plot(mid, tw, ":", color=INK, lw=1.2, label="本当の95%の幅（置いた散らばりから計算）")
ax.set_xlabel("売場面積（百㎡）"); ax.set_ylabel("区間の幅（万円）"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
ax.set_title("一定幅の区間は、小さい店では広すぎ、大きい店では狭すぎる")
save(fig, "a588_width.png", "出典：" + SRC)

main = {"overall": overall.to_dict("records"),
        "const_hetero_band": byband[(byband.hetero) & (byband.method == "const")][["band", "miss", "width"]].to_dict("records"),
        "sql_match": bool(sq.match.all())}
json.dump(main, open(RES / "a588_main.json", "w"), ensure_ascii=False, indent=1)
print(overall.to_string()); print(byband[byband.hetero].pivot(index="band", columns="method", values="miss").to_string())
print(byband[byband.hetero].pivot(index="band", columns="method", values="width").to_string())
print(sq.to_string())
