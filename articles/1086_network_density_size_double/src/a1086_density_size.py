"""1086 人数が倍になると、つながりの密度はどう変わるのか？（架空のデータ）

架空の会員制の趣味のコミュニティ。会員ごとに「1か月に送るやり取りの回数」（活発さ）と「相手に選ばれやすさ」を
作成者が置き、やり取りの回数を乱数で作る。2人の間のやり取りが月に T 回以上あれば「つながりあり」と数え、
会員の数（人数）を倍にしたときの密度（つながりのある組 ÷ ありうる組）と、1人あたりの相手の数の変わり方を数える。
さらに人数の違うコミュニティ120か所を並べ、密度で「活発なコミュニティ」を選べるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1086
SRC = "架空の会員コミュニティのやり取り（作成者が置いた活発さ・選ばれやすさからの乱数、seed 1086）"
SIZES = [50, 100, 200, 400, 800]
GS = [0.0, 0.5, 0.9]          # やり取りのうち、小グループ（25人）の中の相手に送る割合
TS = [1, 3, 5]                # 「つながりあり」とする月のやり取りの回数
BASE = {"A": 20.0, "cv_a": 0.8, "cv_w": 1.0, "g": 0.5, "group": 25}
REPS_SIZE = 10
N_COMM = 120
REPS_COMM = 10
GRID_CV_A_COMM = [0.2, 0.4, 0.8]
GRID_REPS = 5


def r(x, d=4):
    return round(float(x), d)


def gamma(rng, mean, cv, n):
    k = 1 / cv ** 2
    return rng.gamma(k, mean / k, n)


def community(rng, n, A, g, cv_a=BASE["cv_a"], cv_w=BASE["cv_w"], G=BASE["group"]):
    """やり取りの回数の行列（i→j の回数）を返す。i は月に平均 a_i 回送り、相手は選ばれやすさ w に比例して選ぶ。
    割合 g は同じ小グループ（G人）の中から、残りはコミュニティ全体（自分以外）から選ぶ。"""
    a = gamma(rng, A, cv_a, n)
    w = gamma(rng, 1.0, cv_w, n)
    grp = np.arange(n) // G
    same = (grp[:, None] == grp[None, :]).astype(float)
    np.fill_diagonal(same, 0)
    other = np.ones((n, n)); np.fill_diagonal(other, 0)
    ws = same * w[None, :]; wo = other * w[None, :]
    lam = a[:, None] * (g * ws / ws.sum(1, keepdims=True) + (1 - g) * wo / wo.sum(1, keepdims=True))
    c = rng.poisson(lam)
    return c, a


def measure(c, ts=TS):
    n = c.shape[0]
    m = c + c.T
    iu = np.triu_indices(n, 1)
    pair = m[iu]
    out = {"msgs_per_member": c.sum() / n}
    for t in ts:
        e = (pair >= t).sum()
        out[f"density_T{t}"] = e / len(pair)
        out[f"mean_deg_T{t}"] = 2 * e / n
    return out


def precision(score, truth, k=10):
    top_t = set(np.argsort(-truth)[:k])
    top_s = set(np.argsort(-score, kind="stable")[:k])
    return len(top_t & top_s) / k


def spearman(x, y):
    return float(pd.Series(x).rank().corr(pd.Series(y).rank()))


def comm_set(rng, g=BASE["g"], cv_A=0.4):
    ns = (np.round(np.exp(rng.uniform(np.log(50), np.log(800), N_COMM)) / 25) * 25).astype(int)
    As = gamma(rng, BASE["A"], cv_A, N_COMM)
    rows = []
    for n, A in zip(ns, As):
        c, _ = community(rng, n, A, g)
        mm = measure(c, ts=[1, 3])
        rows.append({"n": int(n), "true_activity": A, **mm})
    return pd.DataFrame(rows)


def evaluate(df):
    t = df.true_activity.values
    out = {}
    for key in ["density_T1", "mean_deg_T1", "mean_deg_T3", "msgs_per_member"]:
        out[key] = {"prec10": precision(df[key].values, t), "rho_truth": spearman(df[key], t),
                    "rho_n": spearman(df[key], df.n)}
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 人数ごとの密度・相手の数（小グループの割合 g を3通り、各10回）
    rows = []
    for g in GS:
        for n in SIZES:
            for rep in range(REPS_SIZE):
                c, _ = community(rng, n, BASE["A"], g)
                rows.append({"g": g, "n": n, "rep": rep, **measure(c)})
    raw = pd.DataFrame(rows)
    sizes = raw.groupby(["g", "n"]).mean(numeric_only=True).drop(columns="rep").reset_index()
    sizes.round(6).to_csv(RES / "by_size.csv", index=False)

    def ratio(g, n1, n2, key):
        s = sizes.set_index(["g", "n"])
        return float(s.loc[(g, n2), key] / s.loc[(g, n1), key])

    dbl = []
    for g in GS:
        for n1 in SIZES[:-1]:
            n2 = n1 * 2
            row = {"g": g, "n_from": n1, "n_to": n2,
                   "formula_same_partners": r((n1 - 1) / (n2 - 1)),
                   "msgs_per_member_ratio": r(ratio(g, n1, n2, "msgs_per_member"))}
            for t in TS:
                row[f"density_ratio_T{t}"] = r(ratio(g, n1, n2, f"density_T{t}"))
                row[f"mean_deg_ratio_T{t}"] = r(ratio(g, n1, n2, f"mean_deg_T{t}"))
            dbl.append(row)
    dbl = pd.DataFrame(dbl)
    dbl.to_csv(RES / "doubling.csv", index=False)
    base_d = dbl[(dbl.g == BASE["g"]) & (dbl.n_from == 200)].iloc[0].to_dict()
    sb = sizes[sizes.g == BASE["g"]].set_index("n")

    # 2) 人数の違うコミュニティ120か所：密度で「活発なコミュニティ」を選べるか（10回）
    ev = []
    one = None
    for rep in range(REPS_COMM):
        df = comm_set(np.random.default_rng(SEED * 100 + rep))
        if rep == 0:
            one = df
        e = evaluate(df)
        for k, v in e.items():
            ev.append({"rep": rep, "measure": k, **v,
                       "top10_median_n": float(df.n.values[np.argsort(-df[k].values, kind="stable")[:10]].mean())})
    ev = pd.DataFrame(ev)
    comm = ev.groupby("measure", sort=False).mean(numeric_only=True).drop(columns="rep")
    comm = comm.rename(columns={"top10_median_n": "top10_mean_n"}).round(4)
    comm.to_csv(RES / "communities_measures.csv")
    one.insert(0, "community", [f"C{i:03d}" for i in range(1, len(one) + 1)])
    one.round(5).to_csv(DATA / "communities_one_run.csv", index=False)

    # 3) 確かめ：小グループの割合 g × コミュニティどうしの活発さの差 cv_A（9通り、各5回）
    grid = []
    for g in GS:
        for cvA in GRID_CV_A_COMM:
            vals = []
            for rep in range(GRID_REPS):
                df = comm_set(np.random.default_rng(SEED * 1000 + int(g * 10) * 100 + int(cvA * 10) * 10 + rep), g, cvA)
                vals.append(evaluate(df))
            row = {"g": g, "cv_A": cvA}
            for k in ["density_T1", "mean_deg_T1", "mean_deg_T3", "msgs_per_member"]:
                row[f"prec10_{k}"] = r(np.mean([v[k]["prec10"] for v in vals]))
                row[f"rho_n_{k}"] = r(np.mean([v[k]["rho_n"] for v in vals]))
            grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # 1回分の n=200 のコミュニティ（data）
    c, a = community(np.random.default_rng(SEED + 7), 200, BASE["A"], BASE["g"])
    m = c + c.T
    ii, jj = np.triu_indices(200, 1)
    k = m[ii, jj] > 0
    pd.DataFrame({"member_a": [f"M{i:03d}" for i in ii[k]], "member_b": [f"M{j:03d}" for j in jj[k]],
                  "msgs_month": m[ii, jj][k]}).to_csv(DATA / "pairs_n200_one_run.csv", index=False)

    out = {
        "settings": {**BASE, "sizes": SIZES, "g_grid": GS, "T_grid": TS, "reps_size": REPS_SIZE,
                     "n_communities": N_COMM, "reps_communities": REPS_COMM, "seed": SEED},
        "base_by_size": {int(n): {k: r(v, 5) for k, v in row.items() if k != "g"} for n, row in sb.iterrows()},
        "possible_pairs": {int(n): n * (n - 1) // 2 for n in SIZES},
        "possible_pairs_ratio_200_to_400": r(400 * 399 / (200 * 199)),
        "base_doubling_200_to_400": {k: (r(v) if isinstance(v, float) else v) for k, v in base_d.items()},
        "doubling_ranges_all": {
            "density_ratio_T1": [r(dbl.density_ratio_T1.min()), r(dbl.density_ratio_T1.max())],
            "density_ratio_T3": [r(dbl.density_ratio_T3.min()), r(dbl.density_ratio_T3.max())],
            "density_ratio_T5": [r(dbl.density_ratio_T5.min()), r(dbl.density_ratio_T5.max())],
            "mean_deg_ratio_T1": [r(dbl.mean_deg_ratio_T1.min()), r(dbl.mean_deg_ratio_T1.max())],
            "mean_deg_ratio_T3": [r(dbl.mean_deg_ratio_T3.min()), r(dbl.mean_deg_ratio_T3.max())],
            "msgs_per_member_ratio": [r(dbl.msgs_per_member_ratio.min()), r(dbl.msgs_per_member_ratio.max())]},
        "doubling_200_400_by_g": dbl[dbl.n_from == 200].drop(columns=["n_from", "n_to"]).to_dict("records"),
        "communities_120_10reps": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in comm.to_dict("index").items()},
        "communities_one_run": {"n_min": int(one.n.min()), "n_max": int(one.n.max()),
                                "rho_density_n": r(spearman(one.density_T1, one.n)),
                                "rho_density_truth": r(spearman(one.density_T1, one.true_activity))},
        "grid_9": grid.to_dict("records"),
        "grid_ranges": {k: [r(grid[k].min()), r(grid[k].max())] for k in grid.columns if k.startswith("prec10")},
        "grid_density_worse_than_msgs_count": int((grid.prec10_density_T1 < grid.prec10_msgs_per_member).sum()),
        "grid_density_worse_than_deg1_count": int((grid.prec10_density_T1 < grid.prec10_mean_deg_T1).sum()),
    }
    json.dump(out, open(RES / "a1086_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：人数と密度・相手の数（基本 g=0.5）
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.0))
    cols = {1: BLUE, 3: ORANGE, 5: GREEN}
    for t in TS:
        axs[0].plot(sb.index, sb[f"density_T{t}"], "o-", color=cols[t], label=f"月{t}回以上で「つながり」")
        axs[1].plot(sb.index, sb[f"mean_deg_T{t}"], "o-", color=cols[t], label=f"月{t}回以上")
    for ax in axs:
        ax.set_xscale("log"); ax.set_xticks(SIZES); ax.set_xticklabels([str(s) for s in SIZES])
        ax.minorticks_off(); ax.set_xlabel("会員の数（人、対数の目盛り）"); ax.set_ylim(bottom=0)
    axs[0].set_ylabel("密度（つながりのある組 ÷ ありうる組）"); axs[0].legend(frameon=False, fontsize=8.5)
    axs[1].set_ylabel("1人あたりの相手の数（人）")
    axs[0].set_title("密度は人数が増えるほど下がる", fontsize=11.5)
    axs[1].set_title("1人あたりの相手の数は、数え方で増減が分かれる", fontsize=11.5)
    fig.suptitle(f"1人の月のやり取りの回数を同じに置いても、200人→400人で密度は{base_d['density_ratio_T1']:.2f}倍（月1回以上）", fontsize=12.5, y=1.02)
    save(fig, "a1086_by_size.png", SRC)

    # 図2：120か所を並べたときの上位10か所の当たり
    lab = {"density_T1": "密度（月1回以上）", "mean_deg_T1": "1人あたりの相手の数（月1回以上）",
           "mean_deg_T3": "1人あたりの相手の数（月3回以上）", "msgs_per_member": "1人あたりのやり取りの回数"}
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    keys = list(lab)[::-1]
    v = [comm.loc[k, "prec10"] * 100 for k in keys]
    ax.barh([lab[k] for k in keys], v, color=[BLUE if k == "msgs_per_member" else (ORANGE if k == "density_T1" else LIGHT) for k in keys])
    for i, x in enumerate(v):
        ax.text(x + 1, i, f"{x:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("上位10か所のうち、本当に活発な上位10か所に入っていた割合（%、10回の平均）")
    ax.set_title("人数50〜800人の120か所：密度で選ぶと、人数の少ないコミュニティが並ぶ")
    save(fig, "a1086_rank.png", SRC, y=-0.07)

    # 図3：確かめ（9通り）の上位10か所の当たり
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    xl = [f"g={row.g:g}\ncv={row.cv_A:g}" for row in grid.itertuples()]
    x = np.arange(len(grid)); wdt = 0.27
    ax.bar(x - wdt, grid.prec10_density_T1 * 100, wdt, color=ORANGE, label="密度（月1回以上）")
    ax.bar(x, grid.prec10_mean_deg_T1 * 100, wdt, color=LIGHT, label="相手の数（月1回以上）")
    ax.bar(x + wdt, grid.prec10_msgs_per_member * 100, wdt, color=BLUE, label="やり取りの回数")
    ax.set_xticks(x); ax.set_xticklabels(xl, fontsize=8.5); ax.set_ylim(0, 115); ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("上位10か所の当たり（%、各5回）")
    ax.set_xlabel("g：小グループの中の相手に送る割合　cv：コミュニティどうしの活発さの差")
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
    ax.set_title("9通りの置き方で、密度の当たりはどれも低いまま")
    save(fig, "a1086_robust.png", SRC, y=-0.08)

    print(json.dumps({k: out[k] for k in ["base_doubling_200_to_400", "doubling_ranges_all", "communities_120_10reps", "grid_ranges"]}, ensure_ascii=False, indent=1))
    print(sizes.round(4).to_string()); print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
