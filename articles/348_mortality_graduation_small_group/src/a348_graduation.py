"""A348 小さな集団の年齢ごとの死亡率は、なめらかにすると真の値にどれだけ近づくか（架空の集団、seed 348）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

SEED = 348
REPS = 500
SIZES = [10_000, 100_000, 1_000_000]
LAMS = np.logspace(-1, 6, 15)

std = pd.read_csv(DATA / "standard_qx_2024_male.csv")      # 真の死亡率：令和6年簡易生命表（男）30〜89歳
AGE = std.age.values; Q = std.qx.values; NA = len(AGE)
W_AGE = np.where(AGE <= 64, 1.0, 1.0 - 0.7 * (AGE - 64) / 25)   # 集団の年齢の形：64歳まで一定、89歳で0.3
W_AGE = W_AGE / W_AGE.sum()
D2 = np.diff(np.eye(NA), 2, axis=0); P2 = D2.T @ D2
BANDS = {"30〜49歳": (30, 49), "50〜69歳": (50, 69), "70〜89歳": (70, 89)}

def crude(d, n): return d / n
def moving(d, n, h=2):
    out = np.empty(NA)
    for i in range(NA):
        a, b = max(0, i - h), min(NA, i + h + 1)
        out[i] = d[a:b].sum() / n[a:b].sum()
    return out
def gompertz(d, n):
    """log(死亡率)=a+b×年齢 のポアソン回帰"""
    X = np.c_[np.ones(NA), AGE - 60.0]; beta = np.array([np.log(max(d.sum(), 0.5) / n.sum()), 0.09])
    for _ in range(50):
        mu = n * np.exp(X @ beta); g = X.T @ (d - mu); H = X.T @ (X * mu[:, None])
        step = np.linalg.solve(H, g); beta = beta + step
        if np.abs(step).max() < 1e-10: break
    return np.exp(X @ beta)
def whittaker(d, n, lams=LAMS):
    """ウィテカー法の考え方を対数の死亡率に当てる（ポアソンの尤度＋2階差分の罰則）。λ は AIC で選ぶ"""
    g0 = np.log(gompertz(d, n)); best = None
    for lam in lams:
        th = g0.copy()
        for _ in range(60):
            mu = n * np.exp(th); z = th + (d - mu) / mu
            new = np.linalg.solve(np.diag(mu) + lam * P2, mu * z)
            if np.abs(new - th).max() < 1e-8: th = new; break
            th = new
        mu = n * np.exp(th)
        dev = 2 * np.sum(np.where(d > 0, d * np.log(np.where(d > 0, d, 1) / mu), 0) - (d - mu))
        edf = np.trace(np.linalg.solve(np.diag(mu) + lam * P2, np.diag(mu)))
        aic = dev + 2 * edf
        if best is None or aic < best[0]: best = (aic, lam, np.exp(th), edf)
    return best[2], best[1], best[3]

METHODS = ["粗い死亡率", "5歳の移動平均", "ウィテカー法", "ゴンペルツ曲線"]

def one(rng, N):
    n = np.maximum(np.round(N * W_AGE), 1); d = rng.binomial(n.astype(int), Q).astype(float)
    wh, lam, edf = whittaker(d, n)
    return n, d, {"粗い死亡率": crude(d, n), "5歳の移動平均": moving(d, n), "ウィテカー法": wh, "ゴンペルツ曲線": gompertz(d, n)}, lam, edf

def main():
    rng = np.random.default_rng(SEED)
    rows = []; band_rows = []; lam_rows = []
    for N in SIZES:
        err = {m: np.empty((REPS, NA)) for m in METHODS}; lams = []; edfs = []; deaths = []; zero = []
        for r in range(REPS):
            n, d, est, lam, edf = one(rng, N)
            for m in METHODS: err[m][r] = est[m] / Q - 1
            lams.append(lam); edfs.append(edf); deaths.append(d.sum()); zero.append((d == 0).mean())
        for m in METHODS:
            e = err[m]
            rows.append(dict(size=N, method=m, rmse_pct=float(np.sqrt((e ** 2).mean()) * 100),
                             bias_pct=float(np.abs(e.mean(axis=0)).mean() * 100),
                             within10=float((np.abs(e) <= 0.10).mean())))
            for b, (a0, a1) in BANDS.items():
                k = (AGE >= a0) & (AGE <= a1)
                band_rows.append(dict(size=N, method=m, band=b, rmse_pct=float(np.sqrt((e[:, k] ** 2).mean()) * 100),
                                      mean_err_pct=float(e[:, k].mean() * 100)))
        lam_rows.append(dict(size=N, deaths_mean=float(np.mean(deaths)), zero_age_share=float(np.mean(zero)),
                             lam_median=float(np.median(lams)), edf_median=float(np.median(edfs)),
                             deaths_30_49=float((np.round(N * W_AGE) * Q)[AGE <= 49].sum())))
    df = pd.DataFrame(rows); db = pd.DataFrame(band_rows); dl = pd.DataFrame(lam_rows)
    df.to_csv(RES / "error_by_method.csv", index=False); db.to_csv(RES / "error_by_band.csv", index=False); dl.to_csv(RES / "sizes.csv", index=False)

    # ゴンペルツ曲線そのもののずれ（データが無限にあるとき）：真の死亡率に重みつきで当てた曲線と真の値の差
    n_inf = 1e9 * W_AGE; g_inf = gompertz(n_inf * Q, n_inf)
    gomp_floor = float(np.sqrt(((g_inf / Q - 1) ** 2).mean()) * 100)
    gomp_by_band = {b: float(np.sqrt(((g_inf / Q - 1)[(AGE >= a0) & (AGE <= a1)] ** 2).mean()) * 100) for b, (a0, a1) in BANDS.items()}

    # 例のデータ（1万人、1回分）
    r2 = np.random.default_rng(SEED + 1)
    n, d, est, lam, edf = one(r2, 10_000)
    ex = pd.DataFrame({"age": AGE, "people": n.astype(int), "deaths": d.astype(int), "true_qx": Q,
                       **{m: np.round(est[m], 6) for m in METHODS}})
    ex.to_csv(DATA / "example_group_10000.csv", index=False)
    json.dump(dict(seed=SEED, reps=REPS, sizes=SIZES, by_method=df.to_dict("records"), by_band=db.to_dict("records"),
                   sizes_info=dl.to_dict("records"), gompertz_floor_rmse_pct=gomp_floor, gompertz_floor_by_band=gomp_by_band,
                   example_lambda=float(lam), example_edf=float(edf)), open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    src = "真の死亡率：厚生労働省「令和6年簡易生命表」（男、30〜89歳）。集団は架空（作成者が乱数で作成、seed 348）"
    col = {"粗い死亡率": GRAY, "5歳の移動平均": GREEN, "ウィテカー法": ORANGE, "ゴンペルツ曲線": BLUE}
    # 図1：1万人の例
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(AGE, Q * 1000, color=INK, lw=2, label="真の死亡率")
    cz = est["粗い死亡率"] > 0
    ax.plot(AGE[cz], est["粗い死亡率"][cz] * 1000, "o", color=GRAY, ms=4, label="粗い死亡率（死亡0人の年齢は図の下端）")
    ax.plot(AGE[~cz], np.full((~cz).sum(), 0.12), "v", color=GRAY, ms=4)
    ax.plot(AGE, est["ウィテカー法"] * 1000, color=ORANGE, lw=1.8, label="ウィテカー法")
    ax.plot(AGE, est["ゴンペルツ曲線"] * 1000, color=BLUE, lw=1.4, ls="--", label="ゴンペルツ曲線")
    ax.set_yscale("log"); ax.set_ylim(0.1, 400); ax.set_xlabel("年齢"); ax.set_ylabel("1,000人あたりの年間の死亡（対数の目盛り）")
    ax.legend(fontsize=9, frameon=False, loc="upper left"); ax.set_title(f"1万人の集団・1年分（死亡{int(d.sum())}人）の例")
    save(fig, "a348_example_10000.png", src)

    # 図2：方法×人数の誤差
    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = np.arange(len(SIZES)); w = 0.2
    for i, m in enumerate(METHODS):
        v = [df[(df["size"] == N) & (df.method == m)].rmse_pct.iloc[0] for N in SIZES]
        bars = ax.bar(x + (i - 1.5) * w, v, w, color=col[m], label=m)
        for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, min(vv, 118) + 1.5, f"{vv:.0f}%" if vv >= 9.5 else f"{vv:.1f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(["1万人", "10万人", "100万人"]); ax.set_ylim(0, 128)
    ax.set_ylabel("年齢ごとの死亡率のずれ（真の値に対する%、RMSE）"); ax.legend(fontsize=9, frameon=False)
    ax.set_title("なめらかにすると、1万人の集団で誤差は数分の1になる")
    save(fig, "a348_error_by_method.png", src)

    # 図3：年齢の帯ごと（1万人と100万人）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=False)
    for ax, N, ttl in zip(axes, (10_000, 1_000_000), ("1万人", "100万人")):
        xb = np.arange(len(BANDS))
        for i, m in enumerate(METHODS):
            v = [db[(db["size"] == N) & (db.method == m) & (db.band == b)].rmse_pct.iloc[0] for b in BANDS]
            ax.bar(xb + (i - 1.5) * w, v, w, color=col[m], label=m)
            for xx, vv in zip(xb + (i - 1.5) * w, v): ax.text(xx, vv * 1.02 + 0.2, f"{vv:.0f}" if vv >= 9.5 else f"{vv:.1f}", ha="center", fontsize=7.5)
        ax.set_xticks(xb); ax.set_xticklabels(list(BANDS)); ax.set_title(ttl); ax.set_ylabel("ずれ（%、RMSE）")
    axes[0].legend(fontsize=8.5, frameon=False)
    fig.suptitle("人数が少ないうちは曲線が強く、多くなると曲線の形のずれが残る", y=1.02, fontsize=13)
    save(fig, "a348_error_by_band.png", src, y=-0.03)
    print(df.round(2).to_string()); print(db.round(2).to_string()); print(dl.round(3).to_string()); print(gomp_floor, gomp_by_band, lam, edf)

if __name__ == "__main__":
    main()
