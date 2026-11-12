"""479 地域の平均どうしの相関は、1人ずつの相関とどれだけ違うのか（架空の地域と人、seed 479）"""
import json
import numpy as np, pandas as pd
from common import *

SEED = 479
SRC = "架空の地域と人（作成者が乱数で作成、seed 479）。実在の地域ではない"


def make(G, n, icc, rb, rw, rng):
    """G 地域×n 人。x・y とも、ばらつきのうち icc が地域ごとの差。地域の差どうしの相関 rb、地域の中での相関 rw"""
    cb = np.array([[1, rb], [rb, 1]]) * icc; cw = np.array([[1, rw], [rw, 1]]) * (1 - icc)
    a = rng.multivariate_normal([0, 0], cb, G)                      # 地域ごとの差
    e = rng.multivariate_normal([0, 0], cw, (G, n))                 # 人ごとの差
    return a[:, None, :] + e                                        # G×n×2


def three(z):
    G, n, _ = z.shape
    x, y = z[..., 0], z[..., 1]
    r_ind = np.corrcoef(x.ravel(), y.ravel())[0, 1]
    r_mean = np.corrcoef(x.mean(1), y.mean(1))[0, 1]
    xc, yc = x - x.mean(1, keepdims=True), y - y.mean(1, keepdims=True)
    r_within = (xc * yc).sum() / np.sqrt((xc ** 2).sum() * (yc ** 2).sum())
    return r_ind, r_mean, r_within


def theory(n, icc, rb, rw):
    r_ind = icc * rb + (1 - icc) * rw
    vb = icc + (1 - icc) / n
    r_mean = (icc * rb + (1 - icc) * rw / n) / vb
    return r_ind, r_mean


rng = np.random.default_rng(SEED)

# ---- 1. 式：設定ごとの、1人ずつの相関と平均どうしの相関 ----
ICC = [0.02, 0.05, 0.10, 0.20]; RB = [-0.8, -0.4, 0.0, 0.4, 0.8]; RW = [-0.3, -0.1, 0.0, 0.1, 0.3]
rows = []
for n in [30, 300, 3000]:
    for icc in ICC:
        for rb in RB:
            for rw in RW:
                ri, rm = theory(n, icc, rb, rw)
                rows.append(dict(一地域の人数=n, 地域の差の割合=icc, 地域の差どうしの相関=rb, 地域の中の相関=rw, 一人ずつの相関=round(ri, 3), 平均どうしの相関=round(rm, 3),
                                 向きが逆=bool(ri * rm < -1e-9), 絶対値の倍率=round(abs(rm) / abs(ri), 2) if abs(ri) > 1e-9 else np.nan))
grid = pd.DataFrame(rows); grid.to_csv(RES / "theory_grid.csv", index=False)
summ = []
for n, g in grid.groupby("一地域の人数"):
    nz = g[(g.一人ずつの相関.abs() > 0.005)]
    summ.append(dict(一地域の人数=n, 設定の数=len(g), 向きが逆の設定=int(g.向きが逆.sum()), 向きが逆の割合=round(g.向きが逆.mean() * 100, 1),
                     平均どうしが2倍以上の設定の割合=round((nz.絶対値の倍率 >= 2).mean() * 100, 1), 倍率の中央値=round(nz.絶対値の倍率.median(), 2),
                     平均どうしが05以上で一人ずつが02未満=int(((g.平均どうしの相関.abs() >= 0.5) & (g.一人ずつの相関.abs() < 0.2)).sum())))
summ = pd.DataFrame(summ); summ.to_csv(RES / "theory_summary.csv", index=False)

# ---- 2. 代表の場面を乱数で確かめる（50地域×300人、1,000回）----
SCEN = [("A 地域の差どうしは強く、地域の中はほとんど関係なし", 0.05, 0.8, 0.02), ("B 地域の差どうしはプラス、地域の中はマイナス", 0.10, 0.8, -0.2),
        ("C 地域の差どうしは関係なし、地域の中はプラス", 0.05, 0.0, 0.3), ("D どちらも同じ向きで同じ強さ", 0.10, 0.3, 0.3),
        ("E 地域ごとの差がごく小さい", 0.005, 0.8, 0.1)]
rows = []
for name, icc, rb, rw in SCEN:
    R = np.array([three(make(50, 300, icc, rb, rw, rng)) for _ in range(1000)])
    ti, tm = theory(300, icc, rb, rw)
    rows.append(dict(場面=name, 地域の差の割合=icc, 地域の差どうしの相関=rb, 地域の中の相関=rw, 式_一人ずつ=round(ti, 3), 式_平均どうし=round(tm, 3),
                     一人ずつの相関=round(R[:, 0].mean(), 3), 平均どうしの相関=round(R[:, 1].mean(), 3), 地域の中だけの相関=round(R[:, 2].mean(), 3),
                     平均どうしの標準偏差=round(R[:, 1].std(), 3), 一人ずつの標準偏差=round(R[:, 0].std(), 3),
                     平均どうしと一人ずつの向きが逆の回=round((R[:, 0] * R[:, 1] < 0).mean() * 100, 1)))
scen = pd.DataFrame(rows); scen.to_csv(RES / "scenarios.csv", index=False)

# ---- 3. 地域の数と人数による、平均どうしの相関の振れ（場面A）----
rows = []
for G in [20, 50, 100, 200]:
    for n in [30, 300, 3000]:
        R = np.array([three(make(G, n, 0.05, 0.8, 0.02, rng)) for _ in range(400 if G * n > 100000 else 1000)])
        rows.append(dict(地域の数=G, 一地域の人数=n, 式_平均どうし=round(theory(n, 0.05, 0.8, 0.02)[1], 3), 平均どうしの相関の平均=round(R[:, 1].mean(), 3), 標準偏差=round(R[:, 1].std(), 3),
                         下から5パーセント=round(np.quantile(R[:, 1], 0.05), 3), 上から5パーセント=round(np.quantile(R[:, 1], 0.95), 3), 一人ずつの相関の平均=round(R[:, 0].mean(), 3)))
spread = pd.DataFrame(rows); spread.to_csv(RES / "spread_by_regions.csv", index=False)

# ---- 4. 本当は関係がないのに、平均どうしで相関が出る割合（地域の差も地域の中も相関0）----
rows = []
for G in [10, 20, 50, 200]:
    R = np.array([three(make(G, 300, 0.05, 0.0, 0.0, rng))[1] for _ in range(2000)])
    rows.append(dict(地域の数=G, 平均どうしの相関の標準偏差=round(R.std(), 3), 絶対値が03以上の回=round((np.abs(R) >= 0.3).mean() * 100, 1), 絶対値が05以上の回=round((np.abs(R) >= 0.5).mean() * 100, 1)))
null = pd.DataFrame(rows); null.to_csv(RES / "null_by_regions.csv", index=False)

# ---- 例のデータと図 ----
rg = np.random.default_rng(SEED + 1)
z = make(12, 150, 0.25, 0.9, -0.45, rg)
ex = pd.DataFrame(dict(地域=np.repeat(np.arange(1, 13), 150), x=z[..., 0].ravel().round(3), y=z[..., 1].ravel().round(3))); ex.to_csv(DATA / "example_12_regions.csv", index=False)
ri, rm, rw_ = three(z)
fig, ax = plt.subplots(figsize=(7.6, 4.9))
ax.scatter(z[..., 0].ravel(), z[..., 1].ravel(), s=5, color=LIGHT, alpha=0.6, label=f"1人ずつ（相関 {ri:+.2f}、地域の中だけなら {rw_:+.2f}）")
mx, my = z[..., 0].mean(1), z[..., 1].mean(1)
ax.scatter(mx, my, s=70, color=ORANGE, edgecolor=INK, zorder=3, label=f"地域の平均（相関 {rm:+.2f}）")
b = np.polyfit(mx, my, 1); xx = np.array([mx.min() - 0.2, mx.max() + 0.2]); ax.plot(xx, b[0] * xx + b[1], color=ORANGE, lw=2)
for g in range(12):
    bb = np.polyfit(z[g, :, 0], z[g, :, 1], 1); xg = np.array([z[g, :, 0].mean() - 0.9, z[g, :, 0].mean() + 0.9]); ax.plot(xg, bb[0] * xg + bb[1], color=BLUE, lw=0.9, alpha=0.8)
ax.set_xlabel("x（架空の指標）"); ax.set_ylabel("y（架空の指標）"); ax.legend(fontsize=9, frameon=False, loc="upper left")
ax.set_title("地域の平均は右上がり、地域の中の1人ずつは右下がり", loc="left")
save(fig, "a479_example_scatter.png", f"出典：{SRC}。12地域×150人。青い線は地域ごとの傾き")

fig, ax = plt.subplots(figsize=(7.6, 4.9))
g = grid[grid.一地域の人数 == 300]
ax.scatter(g[~g.向きが逆].一人ずつの相関, g[~g.向きが逆].平均どうしの相関, s=22, color=BLUE, label="向きが同じ")
ax.scatter(g[g.向きが逆].一人ずつの相関, g[g.向きが逆].平均どうしの相関, s=26, color=ORANGE, label="向きが逆")
ax.plot([-0.5, 0.5], [-0.5, 0.5], color=GRAY, lw=1); ax.axhline(0, color=INK, lw=0.6); ax.axvline(0, color=INK, lw=0.6)
ax.set_xlim(-0.5, 0.5); ax.set_ylim(-1, 1); ax.set_xlabel("1人ずつの相関"); ax.set_ylabel("地域の平均どうしの相関"); ax.legend(fontsize=9, frameon=False)
ax.set_title("100通りの設定で、1人ずつの相関と平均どうしの相関を並べる", loc="left")
save(fig, "a479_grid.png", f"出典：式から計算（1地域300人）。灰色の線の上なら、2つの相関は同じ")

fig, ax = plt.subplots(figsize=(7.6, 4.6))
for n, c in zip([30, 300, 3000], [LIGHT, BLUE, "#14427a"]):
    s = spread[spread.一地域の人数 == n]
    ax.errorbar(np.arange(len(s)) + (np.log10(n) - 2.5) * 0.18, s.平均どうしの相関の平均, yerr=[s.平均どうしの相関の平均 - s.下から5パーセント, s.上から5パーセント - s.平均どうしの相関の平均],
                fmt="o", color=c, capsize=4, lw=2, label=f"1地域 {n:,}人")
ax.axhline(float(spread.一人ずつの相関の平均.mean()), color=ORANGE, lw=1.2); ax.text(-0.4, float(spread.一人ずつの相関の平均.mean()) + 0.02, "1人ずつの相関（約0.06）", color=ORANGE, fontsize=9, ha="left")
ax.set_xticks(np.arange(4)); ax.set_xticklabels(["20地域", "50地域", "100地域", "200地域"]); ax.set_ylabel("地域の平均どうしの相関（点＝平均、線＝90%の幅）")
ax.set_title("地域の数が少ないほど、平均どうしの相関は振れる", loc="left"); ax.legend(fontsize=9, frameon=False, loc="lower center", bbox_to_anchor=(0.62, 0.08))
save(fig, "a479_spread.png", f"出典：{SRC}。場面A（地域の差の割合5%、地域の差どうしの相関0.8、地域の中の相関0.02）")

main = dict(seed=SEED, 例の相関=dict(一人ずつ=round(float(ri), 3), 平均どうし=round(float(rm), 3), 地域の中だけ=round(float(rw_), 3)))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(summ.to_string()); print(scen.to_string()); print(spread.to_string()); print(null.to_string()); print(main)
