"""586 裾の重いデータで平均の差を比べると、t検定と順位の検定で検出力はどれだけ違うか（seed 586）"""
import json
import numpy as np, pandas as pd, duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(586)
SRC = "架空のデータ（作成者が乱数で作成、seed 586）"
SIMS = 4000
DISTS = ["normal", "t3", "contam", "lognorm"]
LAB = {"normal": "正規分布", "t3": "t分布（自由度3）", "contam": "外れ値まじり（5%が10倍の散らばり）", "lognorm": "対数正規分布（右に裾が長い）"}


def draw(d, size):
    """どの分布も平均0・標準偏差1にそろえる（位置をずらすのは後で）"""
    if d == "normal":
        z = rng.normal(0, 1, size)
    elif d == "t3":
        z = rng.standard_t(3, size) / np.sqrt(3.0)
    elif d == "contam":
        z = np.where(rng.random(size) < 0.05, rng.normal(0, 10, size), rng.normal(0, 1, size)) / np.sqrt(0.95 + 0.05 * 100)
    else:
        s = 1.0
        m, v = np.exp(s ** 2 / 2), (np.exp(s ** 2) - 1) * np.exp(s ** 2)
        z = (rng.lognormal(0, s, size) - m) / np.sqrt(v)
    return z


def rates(d, n, delta, sims=SIMS):
    a = draw(d, (sims, n)); b = draw(d, (sims, n)) + delta
    pt = stats.ttest_ind(a, b, axis=1, equal_var=False).pvalue
    pw = stats.mannwhitneyu(a, b, axis=1, method="asymptotic").pvalue
    return float((pt < 0.05).mean()), float((pw < 0.05).mean())


# 1 検出力の曲線（各群30人）
rows = []
for d in DISTS:
    for delta in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        t, w = rates(d, 30, delta)
        rows.append({"dist": d, "n": 30, "delta": delta, "t_welch": t, "wilcoxon": w})
curve = pd.DataFrame(rows); curve.to_csv(RES / "power_curve_n30.csv", index=False)

# 2 差がないときに「差あり」と言う割合（人数を変える）
rows = []
for d in DISTS:
    for n in [10, 30, 100]:
        t, w = rates(d, n, 0.0)
        rows.append({"dist": d, "n": n, "t_welch": t, "wilcoxon": w})
size = pd.DataFrame(rows); size.to_csv(RES / "type1.csv", index=False)

# 3 差0.5を80%の確率で見つけるのに要る人数（各群）
NS = [8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 130, 160]
rows = []
for d in DISTS:
    for n in NS:
        t, w = rates(d, n, 0.5, sims=2000)
        rows.append({"dist": d, "n": n, "t_welch": t, "wilcoxon": w})
grid = pd.DataFrame(rows); grid.to_csv(RES / "power_by_n_delta05.csv", index=False)


def need(g, col):
    g = g.sort_values("n")
    ok = g[g[col] >= 0.8]
    if ok.empty:
        return None
    i = ok.index[0]; k = list(g.index).index(i)
    if k == 0:
        return int(g.loc[i, "n"])
    n0, p0 = g.iloc[k - 1]["n"], g.iloc[k - 1][col]; n1, p1 = g.iloc[k]["n"], g.iloc[k][col]
    return round(float(n0 + (0.8 - p0) * (n1 - n0) / (p1 - p0)))


need_rows = [{"dist": d, "t_welch": need(grid[grid.dist == d], "t_welch"), "wilcoxon": need(grid[grid.dist == d], "wilcoxon")} for d in DISTS]
needdf = pd.DataFrame(need_rows); needdf.to_csv(RES / "n_needed_80.csv", index=False)

# 4 例の1回（外れ値まじり・各群30人・差0.5）：順位の検定の U を DuckDB の SQL で出し直す
a = draw("contam", 30); b = draw("contam", 30) + 0.5
ex = pd.DataFrame({"grp": ["A"] * 30 + ["B"] * 30, "value": np.r_[a, b]})
ex.to_csv(DATA / "example_contam.csv", index=False)
u_py = float(stats.mannwhitneyu(a, b, method="asymptotic").statistic)
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("obs", ex)
u_sql = float(con.execute(open(SQL / "a586_rank_u.sql").read()).fetchone()[0])
pd.DataFrame([{"u_python": u_py, "u_duckdb": u_sql, "match": abs(u_py - u_sql) < 1e-9,
               "p_t_welch": float(stats.ttest_ind(a, b, equal_var=False).pvalue),
               "p_wilcoxon": float(stats.mannwhitneyu(a, b, method="asymptotic").pvalue)}]).to_csv(RES / "sql_example.csv", index=False)

# 図1 検出力の曲線
fig, axs = plt.subplots(2, 2, figsize=(10, 7.2), sharex=True, sharey=True)
for ax, d in zip(axs.flat, DISTS):
    g = curve[curve.dist == d]
    ax.plot(g.delta, g.t_welch, "-o", color=BLUE, ms=4, label="t検定（ウェルチ）")
    ax.plot(g.delta, g.wilcoxon, "-o", color=ORANGE, ms=4, label="順位の検定（Wilcoxon）")
    ax.axhline(0.05, color=GRAY, lw=0.8, ls=":")
    ax.set_title(LAB[d], fontsize=11); ax.set_ylim(0, 1.02); ax.grid(alpha=0.3)
for ax in axs[1]: ax.set_xlabel("2群の平均の差（標準偏差を1とした大きさ）")
for ax in axs[:, 0]: ax.set_ylabel("「差あり」と言った割合")
axs[0, 0].legend(fontsize=9, loc="lower right")
fig.suptitle("裾が重いほど、順位の検定のほうが差を見つける（各群30人・各4,000回）", fontsize=13)
save(fig, "a586_power_curve.png", "出典：" + SRC)

# 図2 必要な人数
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(DISTS)); wd = 0.36
tv = [needdf.loc[i, "t_welch"] for i in range(len(DISTS))]; wv = [needdf.loc[i, "wilcoxon"] for i in range(len(DISTS))]
b1 = ax.bar(x - wd / 2, [v if v else 0 for v in tv], wd, color=BLUE, label="t検定（ウェルチ）")
b2 = ax.bar(x + wd / 2, [v if v else 0 for v in wv], wd, color=ORANGE, label="順位の検定（Wilcoxon）")
for bars, vals in [(b1, tv), (b2, wv)]:
    for r, v in zip(bars, vals):
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1.5, f"{v}人" if v else "160人超", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([LAB[d].split("（")[0] for d in DISTS])
ax.set_ylabel("80%の確率で差を見つけるのに要る人数（各群）"); ax.set_ylim(0, 82); ax.legend(fontsize=9, ncol=2, loc="upper center"); ax.grid(axis="y", alpha=0.3)
ax.set_title("差0.5を見つけるのに要る人数（各群・各2,000回から補間）")
save(fig, "a586_n_needed.png", "出典：" + SRC)

# 図3 差がないときの「差あり」
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, col, ttl in [(axs[0], "t_welch", "t検定（ウェルチ）"), (axs[1], "wilcoxon", "順位の検定（Wilcoxon）")]:
    for j, n in enumerate([10, 30, 100]):
        g = size[size.n == n]
        ax.bar(np.arange(len(DISTS)) + (j - 1) * 0.26, g[col] * 100, 0.26, label=f"各群{n}人", color=[GRAY, BLUE, GREEN][j])
    ax.axhline(5, color=INK, lw=0.8, ls=":")
    ax.set_xticks(range(len(DISTS))); ax.set_xticklabels([LAB[d].split("（")[0] for d in DISTS], fontsize=9)
    ax.set_title(ttl); ax.grid(axis="y", alpha=0.3)
axs[0].set_ylabel("本当は差がないのに「差あり」と言った割合（%）"); axs[1].set_ylim(0, 7.5); axs[1].legend(fontsize=9, ncol=3, loc="upper center")
fig.suptitle("差がないとき：t検定は裾が重いと5%より少なめ、順位の検定は5%前後（各4,000回）", fontsize=12, y=1.03)
save(fig, "a586_type1.png", "出典：" + SRC)

main = {"power_n30_d05": curve[curve.delta == 0.5].set_index("dist")[["t_welch", "wilcoxon"]].round(3).to_dict("index"),
        "power_n30_d03": curve[curve.delta == 0.3].set_index("dist")[["t_welch", "wilcoxon"]].round(3).to_dict("index"),
        "n_needed": needdf.set_index("dist").to_dict("index"),
        "type1": size.round(4).to_dict("records")}
json.dump(main, open(RES / "a586_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(pd.read_csv(RES / "sql_example.csv").to_string())
