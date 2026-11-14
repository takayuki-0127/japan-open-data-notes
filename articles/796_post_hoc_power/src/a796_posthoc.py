"""796 有意にならなかった結果から検出力を後で計算すると、何を言っていることになるのか

架空のデータ。2つの群（各30件）の平均の差を t 検定で調べる。本当の効果（標準偏差を1とした差 d）を 0・0.2・0.5 に変え、各4,000回。
毎回、観測された差をそのまま「本当の効果」とみなして検出力を計算する（後で計算した検出力）。
それが p値とどう対応するか、本当の検出力とどれだけ違うかを見る。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 796）"
rng = np.random.default_rng(796)
N, R, A = 30, 4000, 0.05
DS = [0.0, 0.2, 0.5]
df = 2 * N - 2; tc = stats.t.ppf(1 - A / 2, df)


def power(d):
    nc = np.abs(d) * np.sqrt(N / 2)
    return stats.nct.sf(tc, df, nc) + stats.nct.cdf(-tc, df, nc)


rows = []
for d in DS:
    a = rng.standard_normal((R, N)); b = rng.standard_normal((R, N)) + d
    t, p = stats.ttest_ind(b, a, axis=1)
    sp = np.sqrt((a.var(1, ddof=1) + b.var(1, ddof=1)) / 2)
    dobs = (b.mean(1) - a.mean(1)) / sp
    rows.append(pd.DataFrame({"true_d": d, "p": p, "d_obs": dobs, "obs_power": power(dobs), "true_power": power(d)}))
D = pd.concat(rows, ignore_index=True); D["sig"] = D.p < A
D.to_csv(RES / "sims.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
S = D.groupby("true_d").agg(true_power=("true_power", "first"), sig_rate=("sig", "mean"),
                            obs_power_ns_mean=("obs_power", lambda s: s[~D.loc[s.index, "sig"]].mean()),
                            obs_power_ns_max=("obs_power", lambda s: s[~D.loc[s.index, "sig"]].max()),
                            obs_power_sig_min=("obs_power", lambda s: s[D.loc[s.index, "sig"]].min()),
                            obs_power_mean=("obs_power", "mean")).reset_index()
S.to_csv(RES / "summary.csv", index=False)
# p値 0.05 のときの後で計算した検出力（理論）
z = stats.t.ppf(1 - .05 / 2, df); d_at05 = z / np.sqrt(N / 2); pw_at05 = float(power(d_at05))
corr = float(stats.spearmanr(D.p, D.obs_power)[0])
g = lambda d, c: float(S[S.true_d == d][c].iloc[0])
out = {"n_per_group": N, "reps": R, "alpha": A, "power_at_p005": pw_at05, "spearman_p_vs_obs_power": corr,
       "true_power": {str(d): g(d, "true_power") for d in DS}, "sig_rate": {str(d): g(d, "sig_rate") for d in DS},
       "obs_power_ns_mean": {str(d): g(d, "obs_power_ns_mean") for d in DS}, "obs_power_ns_max": float(D[~D.sig].obs_power.max()),
       "obs_power_sig_min": float(D[D.sig].obs_power.min()), "n_for_80_d05": int(np.ceil(2 * ((stats.norm.ppf(.975) + stats.norm.ppf(.8)) / .5) ** 2))}
json.dump(out, open(RES / "a796_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：p値と後で計算した検出力
fig, ax = plt.subplots(figsize=(8.5, 4.6)); s = D.sample(3000, random_state=1)
ax.scatter(s.p, s.obs_power, s=6, color=np.where(s.sig, BLUE, ORANGE), alpha=.6)
ax.axvline(.05, color=GRAY, ls="--", lw=.8); ax.axhline(pw_at05, color=GRAY, ls=":", lw=.8)
ax.text(.06, pw_at05 + .02, f"p＝0.05 のとき {pw_at05:.0%}", fontsize=9, color=GRAY)
ax.set_xlabel("p値"); ax.set_ylabel("後で計算した検出力")
ax.set_title("後で計算した検出力は、p値を言い換えただけ（点はすべて1本の線の上に乗る）")
save(fig, "a796_p_vs_power.png", SRC)

# 図2：有意でなかった回の、後で計算した検出力の分布と本当の検出力
fig, axs = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
for ax, d in zip(axs, DS):
    v = D[(D.true_d == d) & (~D.sig)].obs_power
    ax.hist(v, bins=np.linspace(0, .55, 23), color=ORANGE)
    ax.axvline(g(d, "true_power"), color="#0b0b0b", lw=2); ax.text(g(d, "true_power"), ax.get_ylim()[1] * .9 if False else 10, " 本当の検出力", fontsize=8)
    ax.set_title(f"本当の効果 d＝{d}\n本当の検出力 {g(d,'true_power'):.0%}", fontsize=10); ax.set_xlabel("後で計算した検出力")
axs[0].set_ylabel("有意でなかった回の数")
fig.suptitle("有意でなかった回では、後で計算した検出力はいつも約50%以下。本当の検出力とは関係なく決まる", y=1.04)
save(fig, "a796_ns_hist.png", SRC, y=-0.06)

# 図3：前もって決める検出力（件数と効果）
ns = np.arange(5, 201, 5)
fig, ax = plt.subplots(figsize=(8.5, 4.4))
for d, c in zip([0.2, 0.5, 0.8], [GRAY, ORANGE, BLUE]):
    pw = [stats.nct.sf(stats.t.ppf(.975, 2 * n - 2), 2 * n - 2, d * np.sqrt(n / 2)) for n in ns]
    ax.plot(ns, pw, color=c, label=f"効果 d＝{d}")
ax.axhline(.8, color=GRAY, ls="--", lw=.8); ax.axvline(N, color=GRAY, ls=":", lw=.8); ax.text(N + 2, .05, "今回の30件", fontsize=9, color=GRAY)
ax.set_xlabel("1群の件数"); ax.set_ylabel("検出力（前もって計算）"); ax.legend(frameon=False)
ax.set_title("検出力は、調べる前に「見つけたい効果の大きさ」を決めて計算するもの")
save(fig, "a796_planned.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1)); print(S)
