"""A499 めったに起きない出来事の回帰では、係数はどれだけ大きく出るのか
架空の設備データ（故障するかどうか）で、ふつうのロジスティック回帰と Firth の補正つきを比べる（seed 499）"""
import json
import numpy as np
import pandas as pd
from scipy import optimize
from common import plt, save, DATA, RES, BLUE, ORANGE, GRAY, GREEN

SRC = "架空の設備データ（作成者が乱数で作成、seed 499）"
rng = np.random.default_rng(499)
BETA = np.array([0.5, 0.5, 0.0])      # 3つの条件（標準化した値）の本当の係数。3つ目は効いていない
REPS = 1000


def intercept_for(rate):
    """全体の故障の割合が rate になる切片を探す"""
    z = rng.standard_normal((200_000, 3)) @ BETA
    return optimize.brentq(lambda c: (1 / (1 + np.exp(-(c + z)))).mean() - rate, -15, 5)


def fit(X, y, firth=False, it=60):
    """ニュートン法。firth=True なら Jeffreys の事前分布で罰則をつけた（Firth の）推定"""
    b = np.zeros(X.shape[1]); ok = True
    for _ in range(it):
        eta = np.clip(X @ b, -30, 30); p = 1 / (1 + np.exp(-eta)); w = p * (1 - p)
        I = X.T @ (X * w[:, None])
        try:
            Ii = np.linalg.inv(I)
        except np.linalg.LinAlgError:
            return b, False
        if firth:
            h = np.einsum("ij,jk,ik->i", X * np.sqrt(w)[:, None], Ii, X * np.sqrt(w)[:, None])
            g = X.T @ (y - p + h * (0.5 - p))
        else:
            g = X.T @ (y - p)
        step = Ii @ g
        m = np.max(np.abs(step))
        if m > 5:
            step *= 5 / m
        b = b + step
        if np.max(np.abs(step)) < 1e-8:
            break
    if not firth and (np.max(np.abs(b)) > 15 or not np.isfinite(b).all()):
        ok = False                       # 分離（ある条件で故障が0件か全件）で係数が発散した
    return b, ok


rows, keep = [], {}
for rate in (0.005, 0.01, 0.02, 0.05, 0.2):
    c = intercept_for(rate)
    for n in (500, 1000, 2000, 5000, 20000):
        ml, fi, ev, bad = [], [], [], 0
        for _ in range(REPS):
            Z = rng.standard_normal((n, 3))
            y = (rng.random(n) < 1 / (1 + np.exp(-(c + Z @ BETA)))).astype(float)
            X = np.column_stack([np.ones(n), Z])
            ev.append(y.sum())
            if y.sum() < 2:
                bad += 1; continue
            b1, ok = fit(X, y); b2, _ = fit(X, y, firth=True)
            if not ok:
                bad += 1
            else:
                ml.append(b1[1:])
            fi.append(b2[1:])
        ml, fi = np.array(ml), np.array(fi)
        rec = dict(rate=rate, n=n, events_median=float(np.median(ev)), failed_ml=bad / REPS)
        for nm, B in (("ml", ml), ("firth", fi)):
            rec[f"{nm}_b1_mean"] = B[:, 0].mean(); rec[f"{nm}_b1_median"] = np.median(B[:, 0])
            rec[f"{nm}_b1_bias_pct"] = (B[:, 0].mean() / BETA[0] - 1) * 100
            rec[f"{nm}_b1_rmse"] = np.sqrt(np.mean((B[:, 0] - BETA[0]) ** 2))
            rec[f"{nm}_b1_or_mean"] = np.exp(B[:, 0]).mean()            # オッズ比（本当は e^0.5=1.65）
            rec[f"{nm}_b3_sd"] = B[:, 2].std()
            rec[f"{nm}_b3_abs_over_05"] = (np.abs(B[:, 2]) > 0.5).mean()  # 効いていない条件が ±0.5 を超えた割合
        rows.append(rec)
        if rate == 0.01 and n == 1000:
            keep = {"ml": ml[:, 0], "firth": fi[:, 0]}
        print(rate, n, round(rec["ml_b1_bias_pct"], 1), round(rec["firth_b1_bias_pct"], 1), rec["events_median"], rec["failed_ml"], flush=True)
df = pd.DataFrame(rows); df.to_csv(RES / "bias_by_rate_and_n.csv", index=False, float_format="%.4f")
L = min(len(keep["ml"]), len(keep["firth"]))
pd.DataFrame({"ml_b1": keep["ml"][:L], "firth_b1": keep["firth"][:L]}).to_csv(RES / "b1_rate1pct_n1000.csv", index=False, float_format="%.4f")
df["events_per_var"] = df.events_median / 3

c = intercept_for(0.01); Z = rng.standard_normal((1000, 3))
y = (rng.random(1000) < 1 / (1 + np.exp(-(c + Z @ BETA)))).astype(int)
pd.DataFrame(np.column_stack([Z, y]), columns=["x1", "x2", "x3", "failed"]).to_csv(DATA / "example_rate1pct_n1000.csv", index=False, float_format="%.4f")

# --- 図1：故障の件数（1つの条件あたり）ごとの係数の偏り
fig, ax = plt.subplots(figsize=(8, 4.4))
for rate, mk in zip((0.005, 0.01, 0.02, 0.05, 0.2), "ovs^D"):
    s = df[df.rate == rate]
    ax.plot(s.events_per_var, s.ml_b1_bias_pct, mk + "-", color=ORANGE, alpha=0.85)
    ax.plot(s.events_per_var, s.firth_b1_bias_pct, mk + "--", color=BLUE, alpha=0.85)
ax.plot([], [], "-", color=ORANGE, label="ふつうの推定"); ax.plot([], [], "--", color=BLUE, label="Firth の補正つき")
ax.axhline(0, color=GRAY, lw=1); ax.set_xscale("log"); ax.set_xticks([1, 3, 10, 30, 100, 300, 1000]); ax.set_xticklabels(["1", "3", "10", "30", "100", "300", "1000"]); ax.set_xlabel("故障の件数 ÷ 条件の数（中央値、対数目盛り）")
ax.set_ylabel("係数の偏り（%、本当は0.5）"); ax.legend(frameon=False); ax.set_title("故障が少ないほど、ふつうの推定は係数を大きく出す")
save(fig, "a499_bias_by_events.png", "出典：" + SRC + "。記号の違いは故障の割合（0.5%〜20%）")

# --- 図2：割合1%・1,000件の推定の散らばり
fig, ax = plt.subplots(figsize=(8, 4.2))
bins = np.linspace(-1, 2.5, 50)
ax.hist(np.clip(keep["ml"], -1, 2.5), bins, color=ORANGE, alpha=0.55, label="ふつうの推定")
ax.hist(np.clip(keep["firth"], -1, 2.5), bins, color=BLUE, alpha=0.55, label="Firth の補正つき")
ax.axvline(BETA[0], color="k", ls="--"); ax.set_xlabel("条件1の係数の推定（本当は0.5）"); ax.set_ylabel("回数")
ax.legend(frameon=False); ax.set_title("故障の割合1%・1,000台（故障はおよそ10件）で1,000回")
save(fig, "a499_hist_rate1pct.png", "出典：" + SRC)

# --- 図3：効いていない条件が大きく見える割合と、推定できなかった割合
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4))
s = df[df.n == 1000]
x = np.arange(len(s)); w = 0.38
ax[0].bar(x - w / 2, s.ml_b3_abs_over_05 * 100, w, color=ORANGE, label="ふつう"); ax[0].bar(x + w / 2, s.firth_b3_abs_over_05 * 100, w, color=BLUE, label="Firth")
ax[0].set_xticks(x); ax[0].set_xticklabels([f"{r*100:g}%" for r in s.rate]); ax[0].set_xlabel("故障の割合（1,000台）")
ax[0].set_title("効いていない条件の係数が ±0.5 を超えた回（%）"); ax[0].legend(frameon=False)
for n, c in zip((500, 1000, 2000), (ORANGE, GREEN, BLUE)):
    s2 = df[df.n == n]; ax[1].plot(s2.rate * 100, s2.failed_ml * 100, "o-", color=c, label=f"{n}台")
ax[1].set_xscale("log"); ax[1].set_xticks([0.5, 1, 2, 5, 20]); ax[1].set_xticklabels(["0.5", "1", "2", "5", "20"]); ax[1].set_xlabel("故障の割合（%）"); ax[1].set_title("ふつうの推定ができなかった回（%）"); ax[1].legend(frameon=False)
save(fig, "a499_null_and_fail.png", "出典：" + SRC)

json.dump({"rows": df.to_dict("records")}, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(df[["rate", "n", "events_median", "failed_ml", "ml_b1_bias_pct", "firth_b1_bias_pct", "ml_b1_rmse", "firth_b1_rmse", "ml_b1_or_mean", "firth_b1_or_mean", "ml_b3_abs_over_05", "firth_b3_abs_over_05"]].round(3).to_string())
