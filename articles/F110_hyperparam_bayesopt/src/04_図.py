"""F110 集計と図"""
import json
from common import *
P = ["learning_rate", "num_leaves", "min_child_samples", "feature_fraction", "bagging_fraction", "lambda_l2"]
TASK_LABEL = {"power": "電力需要（東京・日次）", "land": "地価公示（全国）"}


def best_so_far(t, n):
    """手法×乱数ごとの「そこまでの最良の検証誤差」を試行回数 1..n でそろえる（グリッドは36回で打ち止め）"""
    out = []
    for (m, s), g in t.groupby(["method", "seed"]):
        g = g.sort_values("trial"); b = np.minimum.accumulate(g.valid_rmse.values)
        b = np.concatenate([b, np.repeat(b[-1], max(0, n - len(b)))])[:n]
        out.append(pd.DataFrame({"method": m, "seed": s, "trial": np.arange(1, n + 1), "best": b}))
    return pd.concat(out)


summary = {}
tabs = {k: pd.read_csv(RES / f"trials_{k}.csv") for k in ["power_main", "land_main", "power_narrow", "power_long"]}
noise = pd.read_csv(RES / "refit_noise.csv")

# 既定値の検証誤差（学習の乱数5つの平均）
dflt = noise[(noise.config == "default") & (noise.split.isna() | (noise.split == SEED))].groupby("task").valid_rmse.mean()
dflt_test = noise[(noise.config == "default") & (noise.split.isna() | (noise.split == SEED))].groupby("task").test_rmse.mean()

# ---- 図1 最良の検証誤差の推移
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
curves = {}
for ax, (task, tag) in zip(axes, [("power", "power_main"), ("land", "land_main")]):
    t = tabs[tag]; bs = best_so_far(t, 40); curves[task] = bs
    for m in METHODS:
        g = bs[bs.method == m].groupby("trial").best
        ax.plot(g.mean().index, g.mean().values, color=METHOD_COLOR[m], lw=2, label=METHOD_LABEL[m])
        ax.fill_between(g.min().index, g.min().values, g.max().values, color=METHOD_COLOR[m], alpha=0.12)
    ax.axhline(dflt[task], color=INK, ls="--", lw=1); ax.text(40, dflt[task], " 既定値", va="bottom", ha="right", fontsize=9)
    lo = bs.best.min(); ax.set_ylim(lo * 0.98, max(dflt[task] * 1.05, bs[bs.trial == 5].best.max()))
    ax.set_title(TASK_LABEL[task]); ax.set_xlabel("試した設定の数"); ax.set_ylabel("それまでで最良の検証誤差（log RMSE）")
axes[0].legend(fontsize=9, frameon=False)
fig.suptitle("試す回数を増やしたときの、最良の検証誤差（線は乱数を変えた平均、帯は最小〜最大）", fontsize=12, y=1.02)
save(fig, "f110_best_so_far.png")

# ---- 各手法の最終成績・目標に届く回数
rows = []
for task, tag in [("power", "power_main"), ("land", "land_main")]:
    t = tabs[tag]; bs = curves[task]
    gbest = t.valid_rmse.min()
    for m in METHODS:
        for s, g in bs[bs.method == m].groupby("seed"):
            row = dict(task=task, method=m, seed=s, best10=g[g.trial == 10].best.iloc[0], best20=g[g.trial == 20].best.iloc[0],
                       best40=g[g.trial == 40].best.iloc[0])
            for pct in (1, 2, 5):
                hit = g[g.best <= gbest * (1 + pct / 100)]
                row[f"reach{pct}"] = int(hit.trial.min()) if len(hit) else np.nan
            for share in (50, 80, 90):  # 既定値から全体の最良までの改善幅のうち、何割に届いたか
                thr = dflt[task] - (dflt[task] - gbest) * share / 100
                hit = g[g.best <= thr]
                row[f"gain{share}"] = int(hit.trial.min()) if len(hit) else np.nan
            tt = t[(t.method == m) & (t.seed == s)].sort_values("valid_rmse").iloc[0]
            row["test_of_best"] = tt.test_rmse; row["sec"] = t[(t.method == m) & (t.seed == s)].sec.sum()
            rows.append(row)
fin = pd.DataFrame(rows); fin.to_csv(RES / "final_by_method.csv", index=False)
agg = fin.groupby(["task", "method"]).agg(best10=("best10", "mean"), best20=("best20", "mean"), best40=("best40", "mean"),
                                          reach1=("reach1", "median"), reach1_fail=("reach1", lambda x: int(x.isna().sum())),
                                          reach2=("reach2", "median"), reach5=("reach5", "median"),
                                          gain50=("gain50", "median"), gain80=("gain80", "median"),
                                          gain80_fail=("gain80", lambda x: int(x.isna().sum())), gain90=("gain90", "median"),
                                          gain90_fail=("gain90", lambda x: int(x.isna().sum())),
                                          test_of_best=("test_of_best", "mean"), sec=("sec", "mean")).reset_index()
agg["default_valid"] = agg.task.map(dflt); agg["default_test"] = agg.task.map(dflt_test)
agg.to_csv(RES / "summary_by_method.csv", index=False)
summary["agg"] = agg.round(5).to_dict("records")
summary["global_best"] = {task: float(tabs[tag].valid_rmse.min()) for task, tag in [("power", "power_main"), ("land", "land_main")]}

# ---- 図2 目標（全体の最良から2%以内）に届くまでの回数
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
fig.subplots_adjust(wspace=0.08)
for ax, task in zip(axes, ["power", "land"]):
    f = fin[fin.task == task]
    for i, m in enumerate(METHODS):
        v = f[f.method == m].gain80.values
        ok = v[~np.isnan(v)]; ng = np.isnan(v).sum()
        ax.scatter(ok, np.full(len(ok), i) + np.linspace(-0.12, 0.12, len(ok)), color=METHOD_COLOR[m], s=40, zorder=3)
        if len(ok): ax.plot([np.median(ok)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
        if ng: ax.text(41, i, f"届かず {ng}回", va="center", fontsize=9, color=METHOD_COLOR[m])
    ax.set_yticks(range(4)); ax.set_yticklabels([METHOD_LABEL[m] for m in METHODS]); ax.set_xlim(0, 48)
    ax.set_xlabel("改善幅の8割に届いた回数（40回まで）"); ax.set_title(TASK_LABEL[task])
axes[0].set_ylim(3.6, -0.6)
fig.suptitle("既定値から「見つかった最良」までの改善幅の8割に届くまで、何回試したか（点は乱数ごと、縦線は中央値）", fontsize=11.5, y=1.02)
save(fig, "f110_trials_to_reach.png")

# ---- 図3 検証で選んだ設定はテストでも良いか
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
corr = {}
for ax, (task, tag) in zip(axes, [("power", "power_main"), ("land", "land_main")]):
    t = tabs[tag]; q = t.valid_rmse.quantile(0.9)
    tt = t[t.valid_rmse <= q]
    ax.scatter(tt.valid_rmse, tt.test_rmse, s=6, color=GRAY, alpha=0.4, label="試した設定（検証誤差の下位90%）")
    for m in METHODS:
        b = fin[(fin.task == task) & (fin.method == m)]
        ax.scatter(b.best40, b.test_of_best, s=45, color=METHOD_COLOR[m], edgecolor="white", zorder=3, label=METHOD_LABEL[m] + "の最良")
    ax.scatter([dflt[task]], [dflt_test[task]], marker="*", s=180, color=INK, zorder=4, label="既定値")
    top = t.nsmallest(max(10, len(t) // 20), "valid_rmse")
    corr[task] = dict(all=float(np.corrcoef(t.valid_rmse, t.test_rmse)[0, 1]),
                      top5pct=float(np.corrcoef(top.valid_rmse, top.test_rmse)[0, 1]), n_top=len(top))
    ax.set_xlabel("検証誤差（選ぶのに使った）"); ax.set_ylabel("テスト誤差（その後の期間・別の地域）"); ax.set_title(TASK_LABEL[task])
axes[0].legend(fontsize=8, frameon=False, loc="lower right")
fig.suptitle("検証でよかった設定は、テストでもよいか", fontsize=12, y=1.02)
save(fig, "f110_valid_vs_test.png")
summary["corr_valid_test"] = corr

# ---- 図4 既定値と比べたテスト誤差の変化（同じ分け方・別の分け方）
fig, ax = plt.subplots(figsize=(10, 4.4))
nz = {}
noise["sp"] = noise.split.fillna(0).astype(int)
cols = [("power", 0, "電力\n（選んだ分け方）"), ("land", SEED, "地価\n（選んだ分け方）"),
        ("land", SEED + 1, "地価\n（別の分け方1）"), ("land", SEED + 2, "地価\n（別の分け方2）")]
off = dict(zip(METHODS, [-0.27, -0.09, 0.09, 0.27]))
for x, (task, sp, lab) in enumerate(cols):
    n = noise[(noise.task == task) & (noise.sp == sp)]
    base = n[n.config == "default"].test_rmse.mean()
    for m in METHODS:
        v = (n[n.config == m].test_rmse / base - 1) * 100
        ax.scatter(np.full(len(v), x + off[m]), v, color=METHOD_COLOR[m], s=22, alpha=0.7, label=METHOD_LABEL[m] if x == 0 else None)
        ax.plot([x + off[m] - 0.07, x + off[m] + 0.07], [v.mean()] * 2, color=METHOD_COLOR[m], lw=2.5)
        nz[f"{task}_{sp}_{m}"] = dict(mean=float(v.mean()), min=float(v.min()), max=float(v.max()))
ax.axhline(0, color=INK, lw=1, ls="--"); ax.text(3.45, 0.3, "既定値", fontsize=9, ha="right")
ax.set_xticks(range(len(cols))); ax.set_xticklabels([c[2] for c in cols])
ax.set_ylabel("既定値と比べたテスト誤差の変化（%）")
ax.legend(fontsize=8, frameon=False, ncol=4, loc="upper left")
ax.set_title("選んだ設定（乱数0の回）を学習し直したときのテスト誤差。点は学習の乱数、横線は平均", fontsize=11)
save(fig, "f110_refit.png")
summary["refit"] = nz
summary["refit_table"] = noise.groupby(["task", "sp", "config"]).agg(valid=("valid_rmse", "mean"), test=("test_rmse", "mean")).reset_index().round(5).to_dict("records")

# ---- 図5 頑健性：狭い探索範囲・100回まで
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
bs = best_so_far(tabs["power_narrow"], 40)
for m in METHODS:
    g = bs[bs.method == m].groupby("trial").best.mean()
    axes[0].plot(g.index, g.values, color=METHOD_COLOR[m], lw=2, label=METHOD_LABEL[m])
g0 = curves["power"].groupby(["method", "trial"]).best.mean().unstack(0)
axes[0].plot(g0.index, g0["random"].values, color=GRAY, lw=1, ls=":", label="ランダム（広い範囲）")
axes[0].plot(g0.index, g0["tpe"].values, color=ORANGE, lw=1, ls=":", label="TPE（広い範囲）")
axes[0].axhline(dflt["power"], color=INK, ls="--", lw=1)
axes[0].set_title("探索範囲を既定値のまわりに狭める（電力）"); axes[0].set_xlabel("試した設定の数"); axes[0].set_ylabel("最良の検証誤差")
bl = best_so_far(tabs["power_long"], 100)
for m in ["random", "tpe", "gp"]:
    g = bl[bl.method == m].groupby("trial").best
    axes[1].plot(g.mean().index, g.mean().values, color=METHOD_COLOR[m], lw=2, label=METHOD_LABEL[m])
    axes[1].fill_between(g.min().index, g.min().values, g.max().values, color=METHOD_COLOR[m], alpha=0.12)
axes[1].axhline(dflt["power"], color=INK, ls="--", lw=1)
axes[1].set_title("100回まで続ける（電力、別の乱数3つ）"); axes[1].set_xlabel("試した設定の数")
lo = bl.best.min(); axes[1].set_ylim(lo * 0.98, dflt["power"] * 1.05)
h, l = axes[0].get_legend_handles_labels()
axes[1].legend(h, l, fontsize=8, frameon=False, loc="center right", title="左の図の線", title_fontsize=8)
for ax in axes:
    ax.set_ylim(0.0272, 0.0385); ax.text(ax.get_xlim()[1], dflt["power"], "既定値 ", fontsize=9, ha="right", va="bottom")
save(fig, "f110_robustness.png")
rob = []
for tag, n in [("power_narrow", 40), ("power_long", 100)]:
    b = best_so_far(tabs[tag], n)
    for m, g in b.groupby("method"):
        r = dict(setting=tag, method=m)
        for k in (10, 20, 40, 100):
            if k <= n: r[f"best{k}"] = float(g[g.trial == k].best.mean())
        tt = tabs[tag][tabs[tag].method == m]
        r["test_of_best"] = float(tt.loc[tt.groupby("seed").valid_rmse.idxmin()].test_rmse.mean())
        rob.append(r)
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
summary["robust"] = rob
summary["default_valid"] = dflt.to_dict(); summary["default_test"] = dflt_test.to_dict()
# 最良の設定の中身
summary["best_params"] = {tag: tabs[tag].sort_values("valid_rmse").iloc[0][P + ["valid_rmse", "test_rmse", "best_iter"]].to_dict()
                          for tag in tabs}
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(summary, ensure_ascii=False, indent=1, default=float)[:6000])
