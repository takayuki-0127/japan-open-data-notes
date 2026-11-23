"""1096 変更の多いファイルほどバグが多いのは、変更のせいか、ファイルの大きさのせいか？（架空のデータ）

架空のアプリのソースのファイル500本。ファイルの大きさ（行数）と、1年の機能の変更の回数を作成者が置き、
バグの数を「大きさの分」と「変更1回ごとの分」の足し算で乱数から作る。見つかったバグには直しの変更が1回ずつ入る。
本当の「変更1回あたりのバグ」（作成者が置いた値）に対して、次の数え方がどれだけ当たるかを数える。
 ① 記録の変更の回数（直しの変更も入る）とバグの数の傾き
 ② 直しの変更を除いた変更の回数とバグの数の傾き
 ③ ②に行数もいっしょに入れて当てはめたときの、変更の回数の傾き
 ④ 行数で10の組に分け、組の中で引いた傾きを件数で重みを付けて平均したもの
 ⑤ ①に行数もいっしょに入れたもの（直しの変更が入ったまま）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1096
SRC = "架空のアプリのソースのファイルと変更・バグ（作成者が置いた大きさ・変更の回数・起こしやすさからの乱数、seed 1096）"
N_FILES = 500
BASE = {"median_lines": 300, "sigma_lines": 1.0, "c0": 8.0, "alpha": 0.8, "cv_u": 0.7,
        "b0": 3.0, "gamma": 1.0}
B1_MAIN = [0.0, 0.05]           # 本当の「変更1回あたりのバグ」
REPS = 300
GRID_B1 = [0.0, 0.05, 0.1]
GRID_ALPHA = [0.5, 0.8, 1.1]    # 大きいファイルほど変更が多い度合い（行数の何乗に比例するか）
GRID_TAU = [0.0, 0.3, 0.6]      # 記録の行数が本当の大きさからずれる大きさ（対数の標準偏差）
GRID_REPS = 100
N_BANDS = 10
METHODS = ["m1_all_changes", "m2_feature_changes", "m3_with_lines", "m4_size_bands", "m5_all_changes_with_lines"]
MLAB = {"m1_all_changes": "① 記録の変更（直しも入る）",
        "m2_feature_changes": "② 直しを除いた変更",
        "m3_with_lines": "③ ②＋行数もいっしょに",
        "m4_size_bands": "④ 行数の10の組の中で",
        "m5_all_changes_with_lines": "⑤ ①＋行数もいっしょに"}


def r(x, d=4):
    return round(float(x), d)


def make_files(rng, b1, alpha=BASE["alpha"], tau=0.0, gamma=BASE["gamma"], n=N_FILES):
    """本当の大きさ size が変更の回数とバグの両方を決める。記録の行数 lines は size から tau だけずれる（tau=0 なら同じ）"""
    size = np.clip(np.exp(rng.normal(np.log(BASE["median_lines"]), BASE["sigma_lines"], n)), 20, 20000)
    lines = np.round(size * np.exp(rng.normal(0, tau, n))) if tau > 0 else np.round(size)
    k = 1 / BASE["cv_u"] ** 2
    u = rng.gamma(k, 1 / k, n)
    feat = rng.poisson(BASE["c0"] * (size / BASE["median_lines"]) ** alpha * u)
    lam_size = BASE["b0"] * (size / 1000) ** gamma
    bugs = rng.poisson(lam_size + b1 * feat)
    return pd.DataFrame({"lines": lines.astype(int), "feature_changes": feat, "fix_changes": bugs,
                         "changes_recorded": feat + bugs, "bugs": bugs})


def slope(y, xs):
    X = np.column_stack([np.ones(len(y))] + list(xs))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(beta[1])


def band_slope(df):
    q = pd.qcut(df.lines.rank(method="first"), N_BANDS, labels=False)
    num = den = 0.0
    for b in range(N_BANDS):
        d = df[q == b]
        x = d.feature_changes.values.astype(float)
        if x.var() == 0:
            continue
        s = np.cov(x, d.bugs.values)[0, 1] / x.var(ddof=1)
        w = len(d) * x.var(ddof=1)            # 組の中の変更の回数の散らばりで重みを付ける
        num += s * w; den += w
    return num / den


def estimates(df):
    y = df.bugs.values.astype(float)
    return {"m1_all_changes": slope(y, [df.changes_recorded.values]),
            "m2_feature_changes": slope(y, [df.feature_changes.values]),
            "m3_with_lines": slope(y, [df.feature_changes.values, df.lines.values]),
            "m4_size_bands": band_slope(df),
            "m5_all_changes_with_lines": slope(y, [df.changes_recorded.values, df.lines.values])}


def describe(df):
    top = df.changes_recorded.rank(method="first", ascending=False) <= len(df) * 0.2
    topf = df.feature_changes.rank(method="first", ascending=False) <= len(df) * 0.2
    return {"rank_corr_changes_bugs": float(df.changes_recorded.rank().corr(df.bugs.rank())),
            "rank_corr_feature_changes_bugs": float(df.feature_changes.rank().corr(df.bugs.rank())),
            "rank_corr_lines_feature_changes": float(df.lines.rank().corr(df.feature_changes.rank())),
            "share_bugs_in_top20pct_changes": float(df.bugs[top].sum() / df.bugs.sum()),
            "share_lines_in_top20pct_changes": float(df.lines[top].sum() / df.lines.sum()),
            "share_bugs_in_top20pct_feature_changes": float(df.bugs[topf].sum() / df.bugs.sum()),
            "share_lines_in_top20pct_feature_changes": float(df.lines[topf].sum() / df.lines.sum()),
            "bugs_per_kloc_top20pct_feature": float(df.bugs[topf].sum() / df.lines[topf].sum() * 1000),
            "bugs_per_kloc_rest": float(df.bugs[~topf].sum() / df.lines[~topf].sum() * 1000)}


def main():
    t0 = time.time()
    # 1) 基本の置き方で、本当の変更1回あたりのバグ 0 と 0.05
    rows, drows = [], []
    one = None
    for b1 in B1_MAIN:
        rng = np.random.default_rng(SEED + int(b1 * 1000))
        for rep in range(REPS):
            df = make_files(rng, b1)
            if b1 == 0.0 and rep == 0:
                one = df.copy()
            rows.append({"b1_true": b1, "rep": rep, **estimates(df)})
            drows.append({"b1_true": b1, "rep": rep, **describe(df)})
    est = pd.DataFrame(rows)
    des = pd.DataFrame(drows)
    summ = []
    for b1 in B1_MAIN:
        e = est[est.b1_true == b1]
        for m in METHODS:
            summ.append({"b1_true": b1, "method": m, "mean": r(e[m].mean()), "p10": r(e[m].quantile(0.1)),
                         "p90": r(e[m].quantile(0.9)), "bias": r(e[m].mean() - b1)})
    summ = pd.DataFrame(summ)
    summ.to_csv(RES / "estimates_base.csv", index=False)
    dsum = des.groupby("b1_true").mean(numeric_only=True).drop(columns="rep").round(4)
    dsum.to_csv(RES / "describe_base.csv")

    # 2) 確かめ：b1 × alpha × tau（27通り）
    grid = []
    for b1 in GRID_B1:
        for al in GRID_ALPHA:
            for ta in GRID_TAU:
                g = np.random.default_rng(SEED * 1000 + GRID_B1.index(b1) * 100 + GRID_ALPHA.index(al) * 10 + GRID_TAU.index(ta))
                vals = [estimates(make_files(g, b1, al, ta)) for _ in range(GRID_REPS)]
                row = {"b1_true": b1, "alpha": al, "tau": ta}
                for m in METHODS:
                    row[m] = r(np.mean([v[m] for v in vals]))
                    row[f"bias_{m}"] = r(row[m] - b1)
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gt = {t: grid[grid.tau == t] for t in GRID_TAU}

    one.insert(0, "file", [f"F{i:03d}" for i in range(1, len(one) + 1)])
    one.to_csv(DATA / "files_b1_0_one_run.csv", index=False)

    base_tab = {f"b1_{b1}": {m: summ[(summ.b1_true == b1) & (summ.method == m)].iloc[0][["mean", "p10", "p90", "bias"]].to_dict()
                             for m in METHODS} for b1 in B1_MAIN}
    out = {
        "settings": {**BASE, "n_files": N_FILES, "b1_main": B1_MAIN, "reps": REPS, "grid_b1": GRID_B1,
                     "grid_alpha": GRID_ALPHA, "grid_tau": GRID_TAU, "grid_reps": GRID_REPS, "n_bands": N_BANDS,
                     "seed": SEED},
        "estimates_base": base_tab,
        "describe_base": {f"b1_{k}": {kk: r(vv) for kk, vv in v.items()} for k, v in dsum.to_dict("index").items()},
        "one_run_b1_0": {"files": len(one), "lines_median": float(one.lines.median()), "lines_max": int(one.lines.max()),
                         "feature_changes_total": int(one.feature_changes.sum()), "bugs_total": int(one.bugs.sum())},
        "grid_27": grid.to_dict("records"),
        "grid_bias_ranges": {m: [r(grid[f"bias_{m}"].min()), r(grid[f"bias_{m}"].max())] for m in METHODS},
        "grid_bias_ranges_by_tau": {f"tau_{t}": {m: [r(d[f"bias_{m}"].min()), r(d[f"bias_{m}"].max())] for m in METHODS}
                                    for t, d in gt.items()},
        "grid_max_abs_bias": {m: r(grid[f"bias_{m}"].abs().max()) for m in METHODS},
        "grid_b1_0_m2_range": [r(grid[grid.b1_true == 0].m2_feature_changes.min()), r(grid[grid.b1_true == 0].m2_feature_changes.max())],
    }
    json.dump(out, open(RES / "a1096_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：変更でバグが増えないと置いた1回分（b1=0）
    fig, axs = plt.subplots(1, 2, figsize=(11.4, 4.3))
    jit = np.random.default_rng(SEED + 5)
    xj = one.feature_changes + jit.uniform(-0.3, 0.3, len(one))
    yj = one.bugs + jit.uniform(-0.3, 0.3, len(one))
    sc = axs[0].scatter(xj, yj, c=np.log10(one.lines), cmap="viridis", s=12, alpha=0.8)
    cb = fig.colorbar(sc, ax=axs[0]); cb.set_label("ファイルの行数（10の何乗）")
    axs[0].set_xlabel("1年の機能の変更の回数（直しは除く）"); axs[0].set_ylabel("1年に見つかったバグ（件）")
    axs[0].set_title("色の明るい（行数の多い）ファイルが右上に集まる", fontsize=11)
    d = dsum.loc[0.0]
    labs = ["変更の多い上位20%の\nファイルの行数の割合", "変更の多い上位20%の\nファイルのバグの割合"]
    vals = [d.share_lines_in_top20pct_feature_changes * 100, d.share_bugs_in_top20pct_feature_changes * 100]
    axs[1].bar(labs, vals, color=[GRAY, ORANGE], width=0.55)
    for i, v in enumerate(vals):
        axs[1].text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=10)
    axs[1].set_ylim(0, 100); axs[1].set_ylabel(f"全体に占める割合（%、{REPS}回の平均）")
    axs[1].set_title("バグの割合は、行数の割合とほぼ同じ", fontsize=11)
    fig.suptitle("変更1回ではバグが増えないと置いた架空のファイル500本でも、変更の多いファイルほどバグが多く見える", fontsize=12, y=1.02)
    save(fig, "a1096_scatter.png", SRC, y=-0.03)

    # 図2：5つの数え方の「変更1回あたりのバグ」（点は300回の平均、線は10〜90%）
    fig, axs = plt.subplots(1, 2, figsize=(11.6, 4.0), sharey=True)
    for ax, b1 in zip(axs, B1_MAIN):
        s = summ[summ.b1_true == b1].set_index("method").loc[METHODS[::-1]]
        y = np.arange(len(METHODS))
        ax.errorbar(s["mean"], y, xerr=[s["mean"] - s.p10, s.p90 - s["mean"]], fmt="o", color=BLUE, ecolor=LIGHT, elinewidth=3)
        ax.axvline(b1, color=ORANGE, lw=1.5)
        ax.text(b1 + 0.002, len(METHODS) - 0.45, f"置いた本当の値 {b1:g}", color=ORANGE, fontsize=9, ha="left")
        for yi, v in zip(y, s["mean"]):
            ax.text(v, yi + 0.22, f"{v + 0.0:.3f}".replace("-0.000", "0.000"), ha="center", fontsize=8.5)
        ax.set_yticks(y); ax.set_yticklabels([MLAB[m] for m in METHODS[::-1]])
        ax.set_xlabel("変更1回ふえたときのバグの増え方（件）")
        ax.set_title(f"本当の値を {b1:g} と置いたとき", fontsize=11)
        ax.set_ylim(-0.6, len(METHODS) - 0.1)
    fig.suptitle("行数もいっしょに入れた③だけが置いた本当の値に近い（作りどおり。点は300回の平均、線は10〜90%）", fontsize=12, y=1.03)
    save(fig, "a1096_estimates.png", SRC, y=-0.04)

    # 図3：確かめ（27通り）のずれ
    fig, ax = plt.subplots(figsize=(10.4, 4.4))
    xg = np.arange(len(grid))
    mk = {"m2_feature_changes": ("o", ORANGE), "m3_with_lines": ("s", BLUE), "m4_size_bands": ("^", GREEN)}
    ax.axhline(0, color=GRAY, lw=1)
    for m, (sym, c) in mk.items():
        ax.plot(xg, grid[f"bias_{m}"], sym, color=c, label=MLAB[m])
    ax.set_xticks(xg)
    ax.set_xticklabels([f"{row.b1_true:g}\n{row.alpha:g}\n{row.tau:g}" for row in grid.itertuples()], fontsize=7)
    ax.set_xlabel("上から：置いた本当の値・変更の回数が大きさの何乗に比例するか・記録の行数のずれ（0はずれなし）")
    ax.set_ylabel("数え方の値 − 置いた本当の値（件）")
    ax.set_ylim(-0.01, 0.135)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3)
    ax.set_title("27通りの置き方：記録の行数が本当の大きさからずれると、③にもずれが残る", fontsize=11)
    save(fig, "a1096_grid.png", SRC, y=-0.1)

    print(summ.to_string()); print(dsum.T.to_string())
    print(grid[["b1_true", "alpha", "tau"] + [f"bias_{m}" for m in METHODS]].to_string())
    print(json.dumps({k: out[k] for k in ["grid_bias_ranges", "grid_bias_ranges_by_tau", "grid_b1_0_m2_range"]}, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
