"""556 同じ分母で割った2つの比率は、もとの数に関係がなくてもどれだけ相関するのか（正解の分かるデータで試す）

架空の店 200店。分子 X（問い合わせ件数）、分子 Y（返品件数）、分母 Z（来店客数）を互いに独立に作る。
X と Y は関係がない（正解：相関 0）。比率 X/Z と Y/Z の相関を数える。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import save, RES, BLUE, ORANGE, GRAY, INK, GREEN

SEED, N, REPS = 556, 200, 2000
rng = np.random.default_rng(SEED)
SRC = "架空のデータ（作成者が乱数で作成、seed 556）"


def lognorm(mean, cv, size):
    s2 = np.log(1 + cv ** 2)
    return rng.lognormal(np.log(mean) - s2 / 2, np.sqrt(s2), size)


def one(cv_z, cv_x=0.3, cv_y=0.3, n=N):
    x = lognorm(120, cv_x, n); y = lognorm(80, cv_y, n); z = lognorm(20000, cv_z, n)
    return x, y, z


def pearson_approx(cx, cy, cz):
    # Pearson (1897) の近似式
    return cz ** 2 / np.sqrt((cx ** 2 + cz ** 2) * (cy ** 2 + cz ** 2))


# ---- 1. 分母の振れ（CV）を変える
rows = []
for cz in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]:
    r_raw, r_rat, sig_raw, sig_rat, b_ratio, b_log, sig_log, r_part = [], [], [], [], [], [], [], []
    for _ in range(REPS):
        x, y, z = one(cz)
        a, b = x / z, y / z
        rr, pr = stats.pearsonr(x, y); rq, pq = stats.pearsonr(a, b)
        r_raw.append(rr); sig_raw.append(pr < 0.05); r_rat.append(rq); sig_rat.append(pq < 0.05)
        # 対数で分母を入れる回帰：log Y = a + b log X + c log Z
        Xm = np.column_stack([np.ones(len(x)), np.log(x), np.log(z)])
        coef, res, *_ = np.linalg.lstsq(Xm, np.log(y), rcond=None)
        e = np.log(y) - Xm @ coef; s2 = e @ e / (len(x) - 3)
        se = np.sqrt(s2 * np.linalg.inv(Xm.T @ Xm)[1, 1])
        b_log.append(coef[1]); sig_log.append(abs(coef[1] / se) > stats.t.ppf(0.975, len(x) - 3))
    rows.append(dict(cv_z=cz, r_raw=np.mean(r_raw), r_ratio=np.mean(r_rat), r_ratio_p05=np.percentile(r_rat, 5),
                     r_ratio_p95=np.percentile(r_rat, 95), approx=pearson_approx(0.3, 0.3, cz) if cz > 0 else 0.0,
                     sig_raw=np.mean(sig_raw), sig_ratio=np.mean(sig_rat),
                     b_log=np.mean(b_log), sig_log=np.mean(sig_log)))
cv = pd.DataFrame(rows)
cv.round(4).to_csv(RES / "by_cv_z.csv", index=False)

# ---- 2. 分子の振れを変える（分母の CV 0.5 で固定）
rows = []
for cx in [0.1, 0.3, 0.5, 1.0]:
    rr = []
    for _ in range(REPS // 2):
        x = lognorm(120, cx, N); y = lognorm(80, cx, N); z = lognorm(20000, 0.5, N)
        rr.append(stats.pearsonr(x / z, y / z)[0])
    rows.append(dict(cv_x=cx, cv_z=0.5, r_ratio=np.mean(rr), approx=pearson_approx(cx, cx, 0.5)))
num = pd.DataFrame(rows)
num.round(4).to_csv(RES / "by_cv_x.csv", index=False)

# ---- 3. 本当に関係があるとき（真の弾力性 0.3）に、方法ごとの推定。分母の CV 0.5
#  A：分子が店の大きさ（来店客数）と関係しない　B：分子が来店客数に比例する
rows = []
for case in ["A", "B"]:
    est = {"比率どうし": [], "対数で分母を入れる": [], "もとの数どうし": []}
    for _ in range(REPS // 2):
        z = lognorm(20000, 0.5, N); size = z / 20000 if case == "B" else 1.0
        x = 120 * size * lognorm(1, 0.3, N)
        y = 80 * size * (x / (120 * size)) ** 0.3 * lognorm(1, 0.25, N)
        a, b = np.log(x / z), np.log(y / z)
        est["比率どうし"].append(np.polyfit(a, b, 1)[0])
        Xm = np.column_stack([np.ones(N), np.log(x), np.log(z)])
        est["対数で分母を入れる"].append(np.linalg.lstsq(Xm, np.log(y), rcond=None)[0][1])
        est["もとの数どうし"].append(np.polyfit(np.log(x), np.log(y), 1)[0])
    for k, v in est.items():
        rows.append(dict(case=case, method=k, mean=np.mean(v), p05=np.percentile(v, 5), p95=np.percentile(v, 95)))
true_eff = pd.DataFrame(rows)
true_eff.round(4).to_csv(RES / "true_effect.csv", index=False)

# ---- 例の1回（CV 0.5）
rng2 = np.random.default_rng(SEED + 1)
s2 = lambda cv_: np.log(1 + cv_ ** 2)
x = rng2.lognormal(np.log(120) - s2(0.3) / 2, np.sqrt(s2(0.3)), N)
y = rng2.lognormal(np.log(80) - s2(0.3) / 2, np.sqrt(s2(0.3)), N)
z = rng2.lognormal(np.log(20000) - s2(0.5) / 2, np.sqrt(s2(0.5)), N)
ex = pd.DataFrame(dict(store=np.arange(1, N + 1), inquiries=x.round().astype(int), returns=y.round().astype(int), visitors=z.round().astype(int)))
ex.to_csv(RES / "example_stores.csv", index=False)
ex_r_raw = stats.pearsonr(ex.inquiries, ex.returns)[0]
ex_r_rat = stats.pearsonr(ex.inquiries / ex.visitors, ex.returns / ex.visitors)[0]

# ---- SQL（DuckDB、1スレッド）で例の1回の相関を確かめる
import duckdb
con = duckdb.connect(); con.execute("SET threads TO 1")
con.register("stores", ex)
q = open(RES.parent / "src" / "a556_ratio_corr.sql", encoding="utf-8").read()
sql_r = con.execute(q).fetchdf()
sql_ok = bool(abs(sql_r.r_raw[0] - ex_r_raw) < 1e-9 and abs(sql_r.r_ratio[0] - ex_r_rat) < 1e-9)

main = dict(seed=SEED, n_stores=N, reps=REPS,
            by_cv_z=cv.round(4).to_dict("records"), by_cv_x=num.round(4).to_dict("records"),
            true_effect=true_eff.round(4).to_dict("records"),
            example=dict(r_raw=round(ex_r_raw, 4), r_ratio=round(ex_r_rat, 4)), sql_matches_python=sql_ok)
json.dump(main, open(RES / "a556_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1：例の散布図
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
ax[0].scatter(ex.inquiries, ex.returns, s=12, color=GRAY)
ax[0].set_title(f"もとの件数どうし　相関 {ex_r_raw:.2f}"); ax[0].set_xlabel("問い合わせ件数"); ax[0].set_ylabel("返品件数")
ax[1].scatter(ex.inquiries / ex.visitors * 1000, ex.returns / ex.visitors * 1000, s=12, color=ORANGE)
ax[1].set_title(f"来店客1,000人あたりどうし　相関 {ex_r_rat:.2f}"); ax[1].set_xlabel("問い合わせ（1,000人あたり）"); ax[1].set_ylabel("返品（1,000人あたり）")
fig.suptitle("関係のない2つの件数も、同じ来店客数で割ると相関が出る（架空の200店、来店客数の CV 0.5）", fontsize=12, y=1.03)
save(fig, "a556_scatter.png", SRC)

# ---- 図2：分母の振れと相関
fig, ax = plt.subplots(figsize=(7.5, 4.4))
ax.fill_between(cv.cv_z, cv.r_ratio_p05, cv.r_ratio_p95, color=ORANGE, alpha=0.18, label="比率どうし 90%の範囲")
ax.plot(cv.cv_z, cv.r_ratio, "o-", color=ORANGE, label="比率どうしの相関（平均）")
ax.plot(cv.cv_z, cv.approx, "--", color=INK, lw=1, label="近似式（Pearson）")
ax.plot(cv.cv_z, cv.r_raw, "s-", color=GRAY, label="もとの件数どうし")
for _, r in cv.iterrows():
    ax.annotate(f"{r.r_ratio:.2f}", (r.cv_z, r.r_ratio), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9, color=ORANGE)
ax.set_xlabel("分母（来店客数）の変動係数"); ax.set_ylabel("相関係数"); ax.set_ylim(-0.12, 1.0)
ax.set_title("分母の振れが大きいほど、比率どうしの相関は高く出る（分子の CV は0.3）"); ax.legend(fontsize=9, loc="upper left")
save(fig, "a556_by_cv.png", SRC)

# ---- 図3：方法ごとの「有意」の割合と、本当に効果があるときの推定
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
w = 0.27; xs = np.arange(len(cv))
ax[0].bar(xs - w, cv.sig_raw * 100, w, color=GRAY, label="もとの件数どうし")
ax[0].bar(xs, cv.sig_ratio * 100, w, color=ORANGE, label="比率どうし")
ax[0].bar(xs + w, cv.sig_log * 100, w, color=BLUE, label="対数で分母を入れた回帰")
ax[0].axhline(5, color=INK, lw=0.8, ls=":"); ax[0].set_xticks(xs, [f"{c:.1f}" for c in cv.cv_z])
ax[0].set_xlabel("分母の変動係数"); ax[0].set_ylabel("p<0.05 になった割合（%）"); ax[0].set_title("関係がないのに「有意」になる割合"); ax[0].legend(fontsize=8)
te = true_eff.pivot(index="case", columns="method", values="mean")
cols = {"もとの数どうし": GRAY, "比率どうし": ORANGE, "対数で分母を入れる": BLUE}
xs2 = np.arange(len(te))
for i, (k, c) in enumerate(cols.items()):
    ax[1].bar(xs2 + (i - 1) * w, te[k], w, color=c, label=k)
ax[1].axhline(0.3, color=INK, lw=1, ls="--"); ax[1].text(len(te) - 0.5, 0.31, "本当の値 0.3", ha="right", fontsize=9)
ax[1].set_xticks(xs2, ["A 分子が店の大きさと無関係", "B 分子が来店客数に比例"]); ax[1].set_xlabel(""); ax[1].set_ylabel("推定した効き方（弾力性）")
ax[1].set_title("本当に効いているとき（0.3）の推定（分母の CV 0.5）"); ax[1].set_ylim(0, 1.05); ax[1].legend(fontsize=8, loc="upper center", ncol=3)
save(fig, "a556_methods.png", SRC)
print(cv.round(3).to_string()); print(num.round(3).to_string()); print(true_eff.round(3).to_string()); print(main["example"], sql_ok)
