"""577 2つの測り方の一致を、相関で見るか、差の平均と幅（Bland–Altman）で見るか（seed 577）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(577)
SRC = "架空のデータ（作成者が乱数で作成、seed 577）"
N = 200
NOISE_OLD, NOISE_NEW = 0.10, 0.15      # 1回測るときの誤差の標準偏差（kg）


def measure(true, bias=0.0, slope=1.0):
    old = true + rng.normal(0, NOISE_OLD, len(true))
    new = bias + slope * true + rng.normal(0, NOISE_NEW, len(true))
    return old.round(2), new.round(2)


def stats(old, new):
    d = new - old
    md, sd = d.mean(), d.std(ddof=1)
    m = (old + new) / 2
    b = np.polyfit(m, d, 1)[0]                       # 差が大きさで変わるか（差を平均に回帰した傾き）
    return {"r": float(np.corrcoef(old, new)[0, 1]), "mean_diff": float(md), "sd_diff": float(sd),
            "loa_low": float(md - 1.96 * sd), "loa_high": float(md + 1.96 * sd), "slope_diff_on_mean": float(b),
            "within_0_3": float(np.mean(np.abs(d) <= 0.3))}


# 4つの場面：荷物の重さ（kg）を、今の計量器と新しい計量器で1回ずつ測る
true_wide = rng.uniform(1, 30, N)
cases = {}
cases["A_一致"] = (true_wide, *measure(true_wide))
cases["B_一定のずれ"] = (true_wide, *measure(true_wide, bias=0.5))
cases["C_比例のずれ"] = (true_wide, *measure(true_wide, slope=1.03))
true_narrow = rng.uniform(5, 6, N)
cases["D_一致・狭い範囲"] = (true_narrow, *measure(true_narrow))
rows, frames = [], []
for k, (t, o, n) in cases.items():
    s = stats(o, n); s["case"] = k; rows.append(s)
    frames.append(pd.DataFrame({"case": k, "item": np.arange(N), "old_kg": o, "new_kg": n}))
summ = pd.DataFrame(rows)[["case", "r", "mean_diff", "sd_diff", "loa_low", "loa_high", "slope_diff_on_mean", "within_0_3"]]
summ.to_csv(RES / "cases_summary.csv", index=False)
paired = pd.concat(frames)
DATA.mkdir(exist_ok=True); paired.to_csv(DATA / "paired_measurements.csv", index=False)

# SQL で同じ値を出す
con = duckdb.connect(); con.execute("SET threads=1")
con.register("paired", paired)
sq = con.execute(open(SQL / "a577_agreement.sql", encoding="utf-8").read()).df()
sq.to_csv(RES / "sql_agreement.csv", index=False)
m = summ.set_index("case").join(sq.set_index("case"), rsuffix="_sql")
ok = bool(np.allclose(m.r, m.r_sql) and np.allclose(m.mean_diff, m.mean_diff_sql) and np.allclose(m.loa_low, m.loa_low_sql) and np.allclose(m.loa_high, m.loa_high_sql))

# 範囲の広さを変える：同じ2台（ずれなし）で、荷物の重さの範囲だけを変えて500回ずつ
widths = [0.5, 1, 2, 5, 10, 29]
rep = []
for w in widths:
    for s in range(500):
        t = rng.uniform(5, 5 + w, N); o, n = measure(t); st = stats(o, n); st.update(width=w, sim=s); rep.append(st)
rep = pd.DataFrame(rep)
rw = rep.groupby("width").agg(r_med=("r", "median"), r_p05=("r", lambda x: x.quantile(.05)), r_p95=("r", lambda x: x.quantile(.95)),
                              loa_half_med=("sd_diff", lambda x: float(np.median(1.96 * x))), r_over_095=("r", lambda x: float((x > 0.95).mean()))).reset_index()
rw.to_csv(RES / "range_width.csv", index=False)
true_loa_half = 1.96 * np.sqrt(NOISE_OLD ** 2 + NOISE_NEW ** 2)

# 図1：散布図
fig, axes = plt.subplots(1, 4, figsize=(14, 3.9))
for ax, (k, (t, o, n)), s in zip(axes, cases.items(), rows):
    ax.scatter(o, n, s=8, color=BLUE, alpha=0.6)
    lo, hi = min(o.min(), n.min()), max(o.max(), n.max())
    ax.plot([lo, hi], [lo, hi], color=INK, lw=1, ls="--")
    ax.set_title(k.split("_", 1)[1] + f"\n相関 {s['r']:.4f}", fontsize=11)
    ax.set_xlabel("今の計量器（kg）")
axes[0].set_ylabel("新しい計量器（kg）")
save(fig, "a577_scatter.png", SRC + "。点線は2台が同じ値になる線")

# 図2：Bland–Altman 図（差と平均）
fig, axes = plt.subplots(1, 4, figsize=(14, 3.9), sharey=True)
for ax, (k, (t, o, n)), s in zip(axes, cases.items(), rows):
    mm, d = (o + n) / 2, n - o
    ax.scatter(mm, d, s=8, color=ORANGE, alpha=0.6)
    ax.axhline(s["mean_diff"], color=INK, lw=1)
    for v in [s["loa_low"], s["loa_high"]]: ax.axhline(v, color=GRAY, lw=1, ls="--")
    ax.axhline(0, color=GREEN, lw=0.8, ls=":")
    ax.set_title(k.split("_", 1)[1] + f"\n差の平均 {s['mean_diff']:+.2f}、幅 {s['loa_low']:+.2f}〜{s['loa_high']:+.2f}", fontsize=10)
    ax.set_xlabel("2台の平均（kg）")
axes[0].set_ylabel("新しい − 今（kg）")
save(fig, "a577_bland_altman.png", SRC + "。実線は差の平均、破線は一致の幅（平均±1.96×差の標準偏差）")

# 図3：範囲の広さと相関・一致の幅
fig, ax1 = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(widths))
ax1.plot(x, rw.r_med, "o-", color=BLUE, label="相関（中央値）")
ax1.fill_between(x, rw.r_p05, rw.r_p95, color=BLUE, alpha=0.15)
ax1.set_ylim(0, 1.02); ax1.set_ylabel("相関", color=BLUE)
ax1.set_xticks(x, [f"{w}kg" for w in widths]); ax1.set_xlabel("荷物の重さの範囲の広さ（5kg〜5kg＋この幅）")
ax2 = ax1.twinx(); ax2.plot(x, rw.loa_half_med, "s-", color=ORANGE, label="一致の幅の半分（中央値）")
ax2.set_ylim(0, 0.6); ax2.set_ylabel("一致の幅の半分（kg）", color=ORANGE); ax2.spines["right"].set_visible(True)
for xx, r, l in zip(x, rw.r_med, rw.loa_half_med):
    ax1.text(xx + 0.12, r - 0.07, f"{r:.2f}", ha="left", color=BLUE, fontsize=9)
    ax2.text(xx, l - 0.05, f"±{l:.2f}", ha="center", color=ORANGE, fontsize=9)
ax1.set_title("同じ2台でも、測る物の範囲が狭いと相関は低く出る")
save(fig, "a577_range.png", SRC + "。2台のずれなし。各500回、帯は相関の5〜95%")

main = {"n_items": N, "noise_old": NOISE_OLD, "noise_new": NOISE_NEW, "true_loa_half": float(true_loa_half),
        "sql_matches_python": ok, "cases": summ.round(4).to_dict(orient="records"), "range": rw.round(4).to_dict(orient="records")}
json.dump(main, open(RES / "a577_main.json", "w"), ensure_ascii=False, indent=1)
print(summ.round(3).to_string()); print(rw.round(3).to_string()); print("true half", round(true_loa_half, 3), "sql ok", ok)
