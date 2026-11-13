"""A496 外れ値が1点あると、相関係数はどれだけ動くのか（架空の2変数、seed 496）"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from common import plt, save, DATA, RES, BLUE, ORANGE, GRAY, GREEN

SRC = "架空の2変数（作成者が乱数で作成、seed 496）"
rng = np.random.default_rng(496)
REPS = 2000


def sample(n, rho):
    z = rng.standard_normal((n, 2))
    x = z[:, 0]
    y = rho * z[:, 0] + np.sqrt(1 - rho ** 2) * z[:, 1]
    return x, y


def corr_pair(x, y):
    """ピアソンと、順位どうしのピアソン（＝スピアマン）"""
    return np.corrcoef(x, y)[0, 1], np.corrcoef(stats.rankdata(x), stats.rankdata(y))[0, 1]


def pval(r, n):
    """相関が0かどうかの両側 p 値（t 分布、scipy の pearsonr・spearmanr と同じ式）"""
    t = r * np.sqrt((n - 2) / max(1e-15, 1 - r * r))
    return 2 * stats.t.sf(abs(t), n - 2)


rows = []
# 外れ値の置き方：「逆向き」(+k, −k)、「同じ向き」(+k, +k)、「片方だけ」(+k, 0)
PLACES = {"逆向き": (1, -1), "同じ向き": (1, 1), "片方だけ": (1, 0)}
for n in (20, 50, 200):
    for rho in (0.0, 0.3, 0.5, 0.8):
        for k in (3, 5, 10):
            for pname, (sx, sy) in PLACES.items():
                d_p, d_s, flip_p, flip_s, sig_p0, sig_p1, sig_s0, sig_s1 = [], [], 0, 0, 0, 0, 0, 0
                for _ in range(REPS):
                    x, y = sample(n, rho)
                    p0, s0 = corr_pair(x, y)
                    x1 = np.append(x, sx * k); y1 = np.append(y, sy * k)
                    p1, s1 = corr_pair(x1, y1)
                    d_p.append(p1 - p0); d_s.append(s1 - s0)
                    if rho > 0:
                        flip_p += (p1 < 0) and (p0 > 0); flip_s += (s1 < 0) and (s0 > 0)
                    # 5%で「相関あり」と出るか（両側、ピアソンの t 検定・スピアマン）
                    sig_p0 += pval(p0, n) < 0.05; sig_p1 += pval(p1, n + 1) < 0.05
                    sig_s0 += pval(s0, n) < 0.05; sig_s1 += pval(s1, n + 1) < 0.05
                d_p, d_s = np.array(d_p), np.array(d_s)
                rows.append(dict(n=n, rho=rho, k=k, place=pname,
                                 pearson_mean_change=d_p.mean(), pearson_abs_change_median=np.median(np.abs(d_p)),
                                 spearman_mean_change=d_s.mean(), spearman_abs_change_median=np.median(np.abs(d_s)),
                                 pearson_sign_flip=flip_p / REPS, spearman_sign_flip=flip_s / REPS,
                                 pearson_sig_before=sig_p0 / REPS, pearson_sig_after=sig_p1 / REPS,
                                 spearman_sig_before=sig_s0 / REPS, spearman_sig_after=sig_s1 / REPS))
df = pd.DataFrame(rows)
df.to_csv(RES / "change_by_setting.csv", index=False, float_format="%.4f")

# 例のデータ（n=50, rho=0.5）と、外れ値の位置を動かしたときの相関の地図
x, y = sample(50, 0.5)
pd.DataFrame({"x": x, "y": y}).to_csv(DATA / "example_n50_rho05.csv", index=False, float_format="%.4f")
grid = np.linspace(-10, 10, 81)
P0, S0 = corr_pair(x, y)
mp = np.zeros((81, 81)); ms = np.zeros((81, 81))
for i, gy in enumerate(grid):
    for j, gx in enumerate(grid):
        mp[i, j], ms[i, j] = corr_pair(np.append(x, gx), np.append(y, gy))

# --- 図1：外れ値の強さ k ごとの相関の変化（n=50、逆向き）
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for a, rho in zip(ax, (0.3, 0.8)):
    s = df[(df.n == 50) & (df.rho == rho) & (df.place == "逆向き")]
    a.plot(s.k, rho + s.pearson_mean_change, "o-", color=BLUE, label="ピアソン")
    a.plot(s.k, rho + s.spearman_mean_change, "s-", color=ORANGE, label="スピアマン")
    a.axhline(rho, color=GRAY, ls="--", lw=1); a.axhline(0, color="k", lw=0.6)
    a.set_title(f"もとの相関 {rho}（50件＋逆向きの1点）"); a.set_xlabel("外れ値の大きさ（標準偏差の何倍）")
    a.set_xticks([3, 5, 10])
ax[0].set_ylabel("足したあとの相関（もとの相関＋平均の変化）"); ax[0].legend(frameon=False)
fig.suptitle("逆向きの1点で、ピアソンの相関は0を越えて下がる", y=1.02)
save(fig, "a496_change_by_k.png", "出典：" + SRC)

# --- 図2：件数ごとの、符号が逆になる割合（rho=0.3, 逆向き, k=5,10）
fig, ax = plt.subplots(figsize=(7.5, 4.2))
w = 0.2
for i, k in enumerate((5, 10)):
    s = df[(df.rho == 0.3) & (df.place == "逆向き") & (df.k == k)]
    xs = np.arange(3)
    ax.bar(xs + (2 * i - 1.5) * w, s.pearson_sign_flip * 100, w, color=BLUE, alpha=0.55 + 0.45 * i, label=f"ピアソン k={k}")
    ax.bar(xs + (2 * i - 0.5) * w, s.spearman_sign_flip * 100, w, color=ORANGE, alpha=0.55 + 0.45 * i, label=f"スピアマン k={k}")
ax.set_xticks(np.arange(3)); ax.set_xticklabels(["20件", "50件", "200件"])
ax.set_ylabel("相関の向きが逆になった回（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
ax.set_title("もとの相関0.3、逆向きの1点を足したとき")
save(fig, "a496_sign_flip.png", "出典：" + SRC + "。もとの相関が正で、1点を足したあと負になった回の割合", y=-0.18)

# --- 図3：外れ値を置く位置ごとの相関（n=50, rho=0.5 の例）
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.6))
fig.subplots_adjust(wspace=0.4)
for a, m, t, v0 in zip(ax, (mp, ms), ("ピアソン", "スピアマン"), (P0, S0)):
    im = a.imshow(m, origin="lower", extent=(-10, 10, -10, 10), cmap="RdBu_r", vmin=-0.8, vmax=0.8)
    a.contour(grid, grid, m, levels=[0], colors="k", linewidths=1)
    a.scatter(x, y, s=6, color="k"); a.set_title(f"{t}（1点を足す前は {v0:.2f}）")
    a.set_xlabel("足した1点の x"); a.set_ylabel("足した1点の y")
fig.colorbar(im, ax=ax, shrink=0.8, label="1点を足したあとの相関")
fig.suptitle("黒い線の外側に1点置くと、ピアソンの相関は負になる", y=1.0)
save(fig, "a496_position_map.png", "出典：" + SRC)

key = lambda n, rho, k, p: df[(df.n == n) & (df.rho == rho) & (df.k == k) & (df.place == p)].iloc[0].to_dict()
main = {"example_n50_rho05": {"pearson": P0, "spearman": S0,
                              "pearson_min_over_grid": float(mp.min()), "spearman_min_over_grid": float(ms.min()),
                              "share_grid_pearson_negative": float((mp < 0).mean()), "share_grid_spearman_negative": float((ms < 0).mean())},
        "n50_rho05_opp_k5": key(50, 0.5, 5, "逆向き"), "n50_rho05_opp_k10": key(50, 0.5, 10, "逆向き"),
        "n50_rho0_same_k5": key(50, 0.0, 5, "同じ向き"), "n50_rho0_same_k10": key(50, 0.0, 10, "同じ向き"),
        "n20_rho03_opp_k5": key(20, 0.3, 5, "逆向き"), "n200_rho03_opp_k10": key(200, 0.3, 10, "逆向き"),
        "n50_rho08_opp_k10": key(50, 0.8, 10, "逆向き"), "n50_rho05_one_k10": key(50, 0.5, 10, "片方だけ")}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(main, ensure_ascii=False, indent=1, default=float))
