"""589 階級に区切った度数分布表から平均と中央値を出すと、元のデータの値とどれだけずれるか（seed 589）"""
import json
import numpy as np, pandas as pd, duckdb
from scipy import stats, optimize
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(589)
SRC = "架空のデータ（作成者が乱数で作成、seed 589）"
N, REPS = 5000, 200
# 例：1か月の購入額（千円）。右に裾の長い対数正規分布。σ が大きいほど裾が長い
DISTS = ["mild", "long", "gamma", "mix"]
DLAB = {"mild": "対数正規（σ=0.6）", "long": "対数正規（σ=0.9）", "gamma": "ガンマ（形1.5）", "mix": "2つの山の混合"}
MED = 30.0                                   # 本当の中央値（千円）


def draw(d, n):
    if d == "mild":
        return np.exp(rng.normal(np.log(MED), 0.6, n))
    if d == "long":
        return np.exp(rng.normal(np.log(MED), 0.9, n))
    if d == "gamma":                                   # 対数正規より裾が短い。中央値をおよそ30にそろえる
        return rng.gamma(1.5, MED / 1.18, n)
    k = rng.random(n) < 0.15                           # 85%は中央値25の山、15%は中央値90の山
    return np.where(k, np.exp(rng.normal(np.log(90), 0.5, n)), np.exp(rng.normal(np.log(25), 0.6, n)))


def edges(width, top):
    return np.r_[np.arange(0, top, width), top]     # 最後の階級は「top 以上」


def table(x, e):
    c = np.histogram(x, bins=np.r_[e, np.inf])[0]
    return c


def mean_mid(c, e, top_value):
    mids = np.r_[(e[:-1] + e[1:]) / 2, top_value]
    return float((c * mids).sum() / c.sum())


def pareto_top(c, e):
    """上の2つの階級からパレートの傾きを出し、「以上」の階級の平均を置く（傾きが1以下なら幅を足す方法に戻す）"""
    lo, top = e[-2], e[-1]
    f1, f2 = c[-2] + c[-1], c[-1]                    # lo 以上の数、top 以上の数
    if f2 == 0 or f1 <= f2:
        return top + (top - lo) / 2
    a = np.log(f1 / f2) / np.log(top / lo)
    return top * a / (a - 1) if a > 1.05 else top + (top - lo) / 2


def median_interp(c, e, w):
    cum = np.cumsum(c); h = cum[-1] / 2; k = int(np.searchsorted(cum, h))
    below = cum[k - 1] if k > 0 else 0
    lo = e[k]; width = (e[k + 1] - e[k]) if k < len(e) - 1 else w
    return float(lo + (h - below) / c[k] * width)


def median_mid(c, e, w):
    cum = np.cumsum(c); k = int(np.searchsorted(cum, cum[-1] / 2))
    return float(e[k] + ((e[k + 1] - e[k]) if k < len(e) - 1 else w) / 2)


def lognorm_fit(c, e):
    b = np.r_[e, np.inf]
    def nll(p):
        mu, ls = p; s = np.exp(ls)
        cdf = stats.norm.cdf((np.log(np.maximum(b, 1e-12)) - mu) / s); cdf[0] = 0.0
        pr = np.clip(np.diff(cdf), 1e-300, None)
        return -(c * np.log(pr)).sum()
    r = optimize.minimize(nll, [np.log(MED), np.log(0.8)], method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-7, "maxiter": 4000})
    mu, s = r.x[0], np.exp(r.x[1])
    return float(np.exp(mu + s * s / 2)), float(np.exp(mu))


def estimates(x, w, top):
    e = edges(w, top); c = table(x, e)
    return {"raw_mean": float(x.mean()), "raw_median": float(np.median(x)),
            "mean_mid_same": mean_mid(c, e, top + w / 2), "mean_mid_pareto": mean_mid(c, e, pareto_top(c, e)),
            "mean_lognorm": lognorm_fit(c, e)[0], "median_interp": median_interp(c, e, w),
            "median_mid": median_mid(c, e, w), "median_lognorm": lognorm_fit(c, e)[1],
            "top_share": float(c[-1] / c.sum()), "top_amount_share": float(x[x >= top].sum() / x.sum())}


rows = []
for d in DISTS:
    for w, top in [(10, 100), (20, 100), (50, 200), (10, 60)]:
        for r in range(REPS):
            x = draw(d, N)
            rows.append({"dist": d, "width": w, "top": top, "rep": r, **estimates(x, w, top)})
sim = pd.DataFrame(rows); sim.to_csv(RES / "simulation.csv", index=False)
M = ["mean_mid_same", "mean_mid_pareto", "mean_lognorm"]; D = ["median_interp", "median_mid", "median_lognorm"]
for k in M: sim["err_" + k] = sim[k] / sim.raw_mean - 1
for k in D: sim["err_" + k] = sim[k] / sim.raw_median - 1
cols = ["err_" + k for k in M + D] + ["top_share", "top_amount_share"]
summ = sim.groupby(["dist", "width", "top"])[cols].agg(["mean", "std"]).round(4)
summ.columns = [a + "_" + b for a, b in summ.columns]; summ = summ.reset_index(); summ.to_csv(RES / "summary.csv", index=False)

# 例の1回（裾が長い・10千円刻み・100千円以上）：度数表を保存し、中央値の補間を DuckDB の SQL で出し直す
x = draw("long", N)
e = edges(10, 100); c = table(x, e)
ft = pd.DataFrame({"lower": e, "upper": np.r_[e[1:], np.nan], "n": c})
ft.to_csv(DATA / "example_freq_table.csv", index=False)
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("freq", ft)
med_sql = float(con.execute(open(SQL / "a589_grouped_median.sql").read()).fetchone()[0])
med_py = median_interp(c, e, 10)
pd.DataFrame([{"median_python": med_py, "median_duckdb": med_sql, "match": abs(med_py - med_sql) < 1e-9,
               "raw_median": float(np.median(x)), "raw_mean": float(x.mean()), "mean_mid_same": mean_mid(c, e, 105.0)}]).to_csv(RES / "sql_example.csv", index=False)

# 図1 平均のずれ（10千円刻み・100千円以上）
g = summ[(summ.width == 10) & (summ.top == 100)].set_index("dist").loc[list(DISTS)]
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), sharey=False)
xx = np.arange(len(DISTS)); wd = 0.26
for ax, keys, labs, ttl in [(axs[0], M, ["階級値（「以上」は幅の半分を足す）", "階級値（「以上」はパレートで置く）", "対数正規を当てはめる"], "平均"),
                            (axs[1], D, ["階級の中は一様（補間）", "中央値の入る階級の真ん中", "対数正規を当てはめる"], "中央値")]:
    for j, (k, lb, cc) in enumerate(zip(keys, labs, [ORANGE, BLUE, GREEN])):
        v = g["err_" + k + "_mean"].values * 100
        bars = ax.bar(xx + (j - 1) * wd, v, wd, color=cc, label=lb)
        for r_, vv in zip(bars, v):
            ax.text(r_.get_x() + r_.get_width() / 2, vv + (0.3 if vv >= 0 else -0.3), f"{vv:+.1f}", ha="center", va="bottom" if vv >= 0 else "top", fontsize=8)
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xx); ax.set_xticklabels([DLAB[d] for d in DISTS], fontsize=8.5)
    ax.set_title(ttl + "：元のデータとのずれ（%）"); ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1, frameon=False); ax.grid(axis="y", alpha=0.3)
    lo_, hi_ = ax.get_ylim(); ax.set_ylim(lo_ - 1, hi_ + 1)
fig.suptitle("10千円刻み・「100千円以上」でまとめた表から出した値（各200回の平均）", fontsize=12, y=1.02)
save(fig, "a589_bias.png", "出典：" + SRC, y=-0.2)

# 図2 階級の区切り方で平均のずれはどう変わるか（対数正規σ=0.9 とガンマ）
sets = [(10, 60), (10, 100), (20, 100), (50, 200)]
lab = ["10刻み\n60以上", "10刻み\n100以上", "20刻み\n100以上", "50刻み\n200以上"]
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
xx = np.arange(len(sets))
for ax, d in zip(axs, ["long", "gamma"]):
    gg = summ[summ.dist == d].set_index(["width", "top"])
    for j, (k, lb, cc) in enumerate(zip(M, ["階級値（「以上」は幅の半分を足す）", "階級値（「以上」はパレートで置く）", "対数正規を当てはめる"], [ORANGE, BLUE, GREEN])):
        v = [gg.loc[s_, "err_" + k + "_mean"] * 100 for s_ in sets]
        bars = ax.bar(xx + (j - 1) * wd, v, wd, color=cc, label=lb)
        for r_, vv in zip(bars, v):
            ax.text(r_.get_x() + r_.get_width() / 2, vv + (0.8 if vv >= 0 else -0.8), f"{vv:+.0f}", ha="center", va="bottom" if vv >= 0 else "top", fontsize=7.5)
    sh = [gg.loc[s_, "top_amount_share_mean"] * 100 for s_ in sets]
    ax.set_xticks(xx); ax.set_xticklabels([l_ + f"\n（以上の金額{v_:.0f}%）" for l_, v_ in zip(lab, sh)], fontsize=8.5)
    ax.axhline(0, color=INK, lw=0.8); ax.grid(axis="y", alpha=0.3); ax.set_title(DLAB[d])
axs[0].set_ylabel("平均のずれ（%）")
h1, l1 = axs[0].get_legend_handles_labels(); fig.legend(h1, l1, fontsize=9, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.06), frameon=False)
fig.suptitle("平均のずれは、「以上」の階級の置き方と、分布の形の仮定で決まる（各200回）", fontsize=12, y=1.02)
save(fig, "a589_by_scheme.png", "出典：" + SRC + "。単位は千円。括弧内は「以上」の階級が金額に占める割合", y=-0.1)

# 図3 例の度数表とヒストグラム
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(e[:-1] + 5, c[:-1], 9.5, color=BLUE, alpha=0.8, label="度数（10千円刻み）")
ax.bar(105, c[-1], 9.5, color=ORANGE, alpha=0.9, label=f"100千円以上（{c[-1]}人、最大{x.max():.0f}千円）")
ax.axvline(np.median(x), color=INK, lw=1, label=f"元のデータの中央値 {np.median(x):.1f}")
ax.axvline(med_py, color=GREEN, lw=1, ls="--", label=f"表からの中央値（補間） {med_py:.1f}")
ax.axvline(x.mean(), color=GRAY, lw=1, label=f"元のデータの平均 {x.mean():.1f}")
ax.axvline(mean_mid(c, e, 105.0), color=ORANGE, lw=1, ls="--", label=f"表からの平均（階級値） {mean_mid(c, e, 105.0):.1f}")
ax.set_xlabel("1か月の購入額（千円）"); ax.set_ylabel("人数"); ax.legend(fontsize=8.5); ax.grid(axis="y", alpha=0.3)
ax.set_title("例の1回（5,000人・裾が長い）：表にすると「100千円以上」の中身が見えない")
save(fig, "a589_example.png", "出典：" + SRC)

json.dump({"summary": summ.to_dict("records"), "sql": pd.read_csv(RES / "sql_example.csv").to_dict("records")},
          open(RES / "a589_main.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250)
print(summ[["dist", "width", "top"] + [c_ for c_ in summ.columns if c_.endswith("_mean")]].to_string())
print(pd.read_csv(RES / "sql_example.csv").to_string())
