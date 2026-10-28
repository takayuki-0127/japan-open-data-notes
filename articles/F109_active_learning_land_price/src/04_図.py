"""F109 図と集計表"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, RES, save, STRAT_LABEL, STRAT_COLOR, GRAY, INK, BLUE, ORANGE, LIGHT

D = load()
m = pd.read_csv(RES / "al_main.csv")
full = pd.read_csv(RES / "al_full_pool.csv") if (RES / "al_full_pool.csv").exists() else None
S = ["random", "uncertainty", "diversity", "hybrid"]

# ---- 集計：n ごとの平均と、ランダムとの差（同じ seed どうしの差の平均と、seed 間の 95% 区間）
g = m.groupby(["strategy", "n"])[["rmse", "median_ape", "within20", "rmse_top10", "rmse_bottom10", "share_comm_labeled", "y_sd_labeled"]].mean().reset_index()
g.to_csv(RES / "curve_mean.csv", index=False)
base = m[m.strategy == "random"].set_index(["seed", "n"])
rows = []
for s in S[1:]:
    x = m[m.strategy == s].set_index(["seed", "n"])
    for col in ("rmse", "median_ape", "rmse_top10", "rmse_bottom10"):
        dd = (x[col] - base[col]).dropna().reset_index()
        for n, grp in dd.groupby("n"):
            v = grp[col].values
            se = v.std(ddof=1) / np.sqrt(len(v))
            rows.append(dict(strategy=s, metric=col, n=n, diff=v.mean(), lo=v.mean() - 2.365 * se, hi=v.mean() + 2.365 * se, k=len(v)))
diff = pd.DataFrame(rows); diff.to_csv(RES / "diff_vs_random.csv", index=False)


def n_to_reach(curve_n, curve_v, target):
    """曲線（n 昇順）が target 以下になる最初の n を線形補間で"""
    for i in range(len(curve_n)):
        if curve_v[i] <= target:
            if i == 0: return curve_n[0]
            n0, n1, v0, v1 = curve_n[i - 1], curve_n[i], curve_v[i - 1], curve_v[i]
            return n0 + (v0 - target) / (v0 - v1) * (n1 - n0)
    return np.nan


reach = []
for target_n in (1000, 2000, 3000):
    tgt = g[(g.strategy == "random") & (g.n == target_n)]["rmse"].item()
    for s in S:
        c = g[g.strategy == s].sort_values("n")
        reach.append(dict(target=f"ランダム{target_n}地点の誤差", rmse_target=tgt, strategy=s,
                          n_needed=n_to_reach(c.n.values, c.rmse.values, tgt)))
pd.DataFrame(reach).to_csv(RES / "points_to_reach.csv", index=False)

# ---- 図1 学習曲線
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for s in S:
    c = m[m.strategy == s].groupby("n")["rmse"].agg(["mean", "min", "max"])
    ax[0].plot(c.index, c["mean"], color=STRAT_COLOR[s], lw=2, label=STRAT_LABEL[s])
    ax[0].fill_between(c.index, c["min"], c["max"], color=STRAT_COLOR[s], alpha=0.12, lw=0)
if full is not None:
    fv = full[(full.test == "random") & (full.model == "lgb")]["rmse"].mean()
    ax[0].axhline(fv, color=INK, ls=":", lw=1); ax[0].text(3000, fv + 0.005, f"全部（約2万地点）で学習：{fv:.3f}", ha="right", va="bottom", fontsize=9)
ax[0].set_xlabel("値段を知っている地点の数"); ax[0].set_ylabel("評価用の誤差（log の RMSE）")
ax[0].set_title("地点を足すほど誤差は下がる"); ax[0].legend(frameon=False, fontsize=9)
for s in S[1:]:
    dd = diff[(diff.strategy == s) & (diff.metric == "rmse")]
    ax[1].plot(dd.n, dd["diff"], color=STRAT_COLOR[s], lw=2, label=STRAT_LABEL[s])
    ax[1].fill_between(dd.n, dd.lo, dd.hi, color=STRAT_COLOR[s], alpha=0.15, lw=0)
ax[1].axhline(0, color=GRAY, lw=1); ax[1].set_xlabel("値段を知っている地点の数"); ax[1].set_ylabel("ランダムとの差（マイナス＝よい）")
ax[1].set_title("ランダムと比べた誤差の差（8回の平均と95%区間）")
fig.suptitle("地価公示：200地点から始めて200地点ずつ足したときの誤差", fontsize=13, y=1.02)
save(fig, "f109_learning_curves.png")

# ---- 図2 何地点で追いつくか（ランダムの1,000・2,000・3,000地点と同じ誤差に必要な数）
r = pd.DataFrame(reach)
fig, ax = plt.subplots(figsize=(8.5, 4))
tg = ["ランダム1000地点の誤差", "ランダム2000地点の誤差", "ランダム3000地点の誤差"]
w = 0.2
for i, s in enumerate(S):
    v = [r[(r.target == t) & (r.strategy == s)]["n_needed"].item() for t in tg]
    b = ax.bar(np.arange(3) + (i - 1.5) * w, np.nan_to_num(v, nan=0), w, color=STRAT_COLOR[s], label=STRAT_LABEL[s])
    for x, val in zip(np.arange(3) + (i - 1.5) * w, v):
        ax.text(x, (0 if np.isnan(val) else val) + 40, "届かず" if np.isnan(val) else f"{val:,.0f}", ha="center", fontsize=8)
ax.set_xticks(range(3)); ax.set_xticklabels(["ランダムで1,000地点", "ランダムで2,000地点", "ランダムで3,000地点"])
ax.set_ylabel("同じ誤差に届くのに必要な地点の数"); ax.legend(frameon=False, fontsize=9, ncol=2)
ax.set_title("ランダムと同じ誤差に届くまでに、何地点の値段が必要か（8回の平均の曲線から）")
save(fig, "f109_points_to_reach.png")

# ---- 図3 選ばれた地点の中身（seed 0、3,000地点）：価格の分布と商業地の割合
sel = json.load(open(RES / "selected_seed0.json"))
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.6, 1]})
bins = np.linspace(D.y.min(), D.y.max(), 40)
ax[0].hist(D.y, bins=bins, density=True, color=LIGHT, label="全地点")
for s in S:
    ax[0].hist(D.y.values[sel[s]], bins=bins, density=True, histtype="step", lw=1.8, color=STRAT_COLOR[s], label=STRAT_LABEL[s])
tk = [1e3, 1e4, 1e5, 1e6, 1e7]
ax[0].set_xticks(np.log(tk)); ax[0].set_xticklabels(["1千", "1万", "10万", "100万", "1000万"])
ax[0].set_xlabel("地価（円/㎡、対数目盛）"); ax[0].set_ylabel("密度"); ax[0].legend(frameon=False, fontsize=8)
ax[0].set_title("選ばれた3,000地点の価格の分布（1回目）")
fin = m[m.n == m.n.max()].groupby("strategy")["share_comm_labeled"].mean().reindex(S)
ax[1].barh([STRAT_LABEL[s] for s in S][::-1], fin.values[::-1] * 100, color=[STRAT_COLOR[s] for s in S][::-1])
ax[1].axvline((D.land_use_class == "商業地").mean() * 100, color=INK, ls=":", lw=1)
ax[1].text((D.land_use_class == "商業地").mean() * 100 + 0.5, -0.62, "全地点の割合", fontsize=8, ha="left", color=INK)
for i, v in enumerate(fin.values[::-1]): ax[1].text(v * 100 + 0.5, i, f"{v*100:.0f}%", va="center", fontsize=9)
ax[1].set_xlabel("選ばれた地点に占める商業地（%）"); ax[1].set_title("商業地の割合（8回の平均）")
save(fig, "f109_selected_profile.png")

# ---- 図4 誤差を価格帯別に（上位10%・下位10%の地点の RMSE、3,000地点時点）
fin = m[m.n == m.n.max()].groupby("strategy")[["rmse", "rmse_top10", "rmse_bottom10", "median_ape"]].mean().reindex(S)
fin.to_csv(RES / "final_by_strategy.csv")
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.7, 1]})
ax = axs[0]
cols = [("rmse_bottom10", "価格の下位10%"), ("rmse", "全体"), ("rmse_top10", "価格の上位10%")]
for i, s in enumerate(S):
    ax.bar(np.arange(3) + (i - 1.5) * w, [fin.loc[s, c] for c, _ in cols], w, color=STRAT_COLOR[s], label=STRAT_LABEL[s])
    for j, (c, _) in enumerate(cols): ax.text(j + (i - 1.5) * w, fin.loc[s, c] + 0.005, f"{fin.loc[s, c]:.2f}", ha="center", fontsize=7)
ax.set_xticks(range(3)); ax.set_xticklabels([l for _, l in cols]); ax.set_ylabel("評価用の誤差（log の RMSE）")
ax.set_ylim(0, 0.66); ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center"); ax.set_title("外れやすい地点の誤差は下がった")
ax = axs[1]
SHORT = {"random": "ランダム", "uncertainty": "不確実性", "diversity": "多様性", "hybrid": "不確実性＋多様性"}
ax.barh([SHORT[s] for s in S][::-1], fin["median_ape"].values[::-1] * 100, color=[STRAT_COLOR[s] for s in S][::-1])
for i, v in enumerate(fin["median_ape"].values[::-1]): ax.text(v * 100 + 0.2, i, f"{v*100:.1f}%", va="center", fontsize=9)
ax.set_xlim(0, 24); ax.set_xlabel("予測のずれの中央値（%）"); ax.set_title("ふつうの地点のずれは広がった")
fig.suptitle("3,000地点の時点の誤差（8回の平均）", fontsize=13, y=1.02)
save(fig, "f109_error_by_price.png")

# ---- 図5 頑健性：設定ごとの、ランダムとの差（最後の n、4回の平均と範囲）
if (RES / "al_robust.csv").exists():
    rb = pd.read_csv(RES / "al_robust.csv")
    main4 = m[m.seed < 4].copy(); main4["setting"] = "基本（初期200地点・1回200地点）"
    allr = pd.concat([main4, rb])
    out = []
    for st, grp in allr.groupby("setting", sort=False):
        nmax = grp.n.max()
        f = grp[grp.n == nmax]
        b = f[f.strategy == "random"].set_index("seed")["rmse"]
        for s in S[1:]:
            v = (f[f.strategy == s].set_index("seed")["rmse"] - b).dropna()
            out.append(dict(setting=st, n=nmax, strategy=s, diff=v.mean(), lo=v.min(), hi=v.max(),
                            rmse_random=b.mean(), rel=v.mean() / b.mean()))
    out = pd.DataFrame(out); out.to_csv(RES / "robust_summary.csv", index=False)
    order = list(dict.fromkeys(out.setting))
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(order) + 1.3))
    for k, s in enumerate(S[1:]):
        o = out[out.strategy == s].set_index("setting").reindex(order)
        yy = np.arange(len(order)) + (k - 1) * 0.22
        ax.errorbar(o["rel"] * 100, yy, xerr=[(o["diff"] - o["lo"]) / o["rmse_random"] * 100, (o["hi"] - o["diff"]) / o["rmse_random"] * 100],
                    fmt="o", color=STRAT_COLOR[s], label=STRAT_LABEL[s], ms=5, capsize=0)
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{x}（{int(out[out.setting==x].n.iloc[0]):,}地点）" for x in order], fontsize=9)
    ax.invert_yaxis(); ax.set_xlabel("ランダムと比べた誤差の差（%、マイナス＝よい。点は平均、線は4回の範囲）")
    ax.legend(frameon=False, fontsize=8, loc="lower right"); ax.set_title("設定を変えても、選び方の良し悪しは同じか")
    save(fig, "f109_robustness.png")
print(pd.DataFrame(reach)); print(fin)
