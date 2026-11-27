"""1310 一部のデータに読み書きの1割が集まると、台数を増やしても、いちばん忙しい1台の負荷はどこから下がらなくなるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ10万件と、1日の読み書き。
読み書きの割合 h（基本10%）が、人気の k 件（基本1件）に同じ割合ずつ集まる。
残り（1−h）は、ほかのデータに r 番目の多さが 1÷r^a に比例する偏り（基本 a=0.5）で分かれる（順番は乱数で並べかえ）。
データは1件ずつ、どの台にも同じ確率になる乱数で台に置く（番号から決まる振り分けを乱数で表したもの）。
1件のデータは1台にだけ置き、その読み書きは分けられないと置く（写しに読みを分けることは入れない）。
台の負荷＝その台に置いたデータの読み書きの割合の合計。いちばん忙しい1台の負荷を、台数（1〜200台）ごとに500回数える。
目安の式：いちばん忙しい1台 ≒ h＋（1−h）÷台数（人気の1件の台が、残りも平均どおり受け持つとき）。
全体で扱える量（1台が扱える量を1としたとき）＝1÷いちばん忙しい1台の負荷。上限は1÷h。
確かめ：h（1・5・10・20・30%）×k（1・3・10・100件）×a（0・0.5・0.8）の60通り、台数5・10・20・50・100、各100回。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1310
SRC = "架空のアプリの読み書き（作成者が置いた人気のデータへの集まり方・偏り・台数と、振り分けの乱数、seed 1310）"
N = 100_000
NS = [1, 2, 3, 4, 5, 8, 10, 15, 20, 30, 50, 100, 200]
NS_GRID = [5, 10, 20, 50, 100]
TRIALS = 500
TRIALS_GRID = 100


def weights(rng, h, k, a):
    rest = np.arange(1, N - k + 1, dtype=float) ** (-a)
    rest = rest / rest.sum() * (1 - h)
    rng.shuffle(rest)
    w = np.concatenate([np.full(k, h / k), rest])   # 先頭の k 件が人気のデータ
    return w


def busiest(rng, w, k, n, trials):
    out = np.empty((trials, 3))
    for t in range(trials):
        srv = rng.integers(0, n, size=len(w))
        load = np.bincount(srv, weights=w, minlength=n)
        b = int(np.argmax(load))
        hot_on_b = float(w[:k][srv[:k] == b].sum())
        out[t] = (load[b], hot_on_b, load.mean())
    return out


def formula(h, n):
    return h + (1 - h) / n


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # ---- 基本：h=10%・人気1件・a=0.5、と人気なし（h=0） ----
    rows = []
    for label, h in [("人気の1件に1割", 0.10), ("人気のデータなし", 0.0)]:
        w = weights(rng, h, 1, 0.5)
        for n in NS:
            r = busiest(rng, w, 1, n, TRIALS)
            share = r[:, 0]
            rows.append(dict(case=label, hot_share=h, servers=n,
                             busiest_mean_pct=round(share.mean() * 100, 3),
                             busiest_p10_pct=round(float(np.quantile(share, 0.1)) * 100, 3),
                             busiest_p90_pct=round(float(np.quantile(share, 0.9)) * 100, 3),
                             formula_pct=round(formula(h, n) * 100, 3),
                             even_pct=round(100 / n, 3),
                             busiest_vs_even=round(share.mean() * n, 3),
                             hot_part_of_busiest_pct=round(float((r[:, 1] / r[:, 0]).mean()) * 100, 2),
                             capacity_servers=round(float((1 / share).mean()), 3),
                             formula_capacity=round(1 / formula(h, n), 3)))
    base_df = pd.DataFrame(rows)
    base_df.to_csv(RES / "by_servers.csv", index=False)

    hot = base_df[base_df.case == "人気の1件に1割"].set_index("servers")
    cold = base_df[base_df.case == "人気のデータなし"].set_index("servers")
    # 台数を2倍にしたときの、いちばん忙しい1台の下がり方
    dbl = []
    for n in [5, 10, 50, 100]:
        dbl.append(dict(servers_from=n, servers_to=2 * n,
                        hot_drop_pct=round((1 - hot.loc[2 * n, "busiest_mean_pct"] / hot.loc[n, "busiest_mean_pct"]) * 100, 2),
                        cold_drop_pct=round((1 - cold.loc[2 * n, "busiest_mean_pct"] / cold.loc[n, "busiest_mean_pct"]) * 100, 2)))
    dbl = pd.DataFrame(dbl)
    dbl.to_csv(RES / "doubling.csv", index=False)

    h = 0.10
    base = dict(
        n_keys=N, hot_share_pct=10.0, hot_items=1, rest_skew_a=0.5, trials=TRIALS,
        floor_pct=10.0, capacity_limit=round(1 / h, 3),
        formula_half_point_servers=round((1 - h) / h, 3),
        formula_within_10pct_of_floor_servers=round((1 - h) / (0.1 * h), 3),
        hot={str(n): dict(busiest_mean_pct=float(hot.loc[n, "busiest_mean_pct"]),
                          formula_pct=float(hot.loc[n, "formula_pct"]),
                          hot_part_pct=float(hot.loc[n, "hot_part_of_busiest_pct"]),
                          capacity=float(hot.loc[n, "capacity_servers"])) for n in NS},
        cold={str(n): dict(busiest_mean_pct=float(cold.loc[n, "busiest_mean_pct"]),
                           capacity=float(cold.loc[n, "capacity_servers"])) for n in NS},
        first_servers_hot_part_over_half=int(hot[hot.hot_part_of_busiest_pct > 50].index.min()),
        first_servers_busiest_within_10pct_floor=int(hot[hot.busiest_mean_pct <= 11.0].index.min()),
        max_abs_diff_from_formula_pt=round(float((hot.busiest_mean_pct - hot.formula_pct).abs().max()), 3),
    )

    # データ：基本の置き方で台数10・1回分の台ごとの負荷
    w = weights(np.random.default_rng(SEED + 1), 0.10, 1, 0.5)
    r2 = np.random.default_rng(SEED + 2)
    srv = r2.integers(0, 10, size=N)
    load = np.bincount(srv, weights=w, minlength=10)
    hotload = np.bincount(srv[:1], weights=w[:1], minlength=10)
    ex = pd.DataFrame(dict(server=np.arange(1, 11), load_pct=np.round(load * 100, 3),
                           hot_part_pct=np.round(hotload * 100, 3)))
    ex.to_csv(DATA / "example_10_servers.csv", index=False)
    base["example_busiest_pct"] = float(ex.load_pct.max())
    base["example_second_pct"] = float(np.sort(ex.load_pct)[-2])

    # ---- 確かめ：60通り ----
    grid = []
    for hh in [0.01, 0.05, 0.10, 0.20, 0.30]:
        for k in [1, 3, 10, 100]:
            for a in [0.0, 0.5, 0.8]:
                w = weights(rng, hh, k, a)
                for n in NS_GRID:
                    r = busiest(rng, w, k, n, TRIALS_GRID)
                    grid.append(dict(hot_share=hh, hot_items=k, rest_skew_a=a, servers=n,
                                     busiest_mean_pct=round(r[:, 0].mean() * 100, 3),
                                     formula_k1_pct=round(formula(hh, n) * 100, 3),
                                     even_pct=round(100 / n, 3),
                                     hot_part_of_busiest_pct=round(float((r[:, 1] / r[:, 0]).mean()) * 100, 2),
                                     capacity_servers=round(float((1 / r[:, 0]).mean()), 3)))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g1 = grid[grid.hot_items == 1]
    g100 = grid[(grid.servers == 100)]
    piv = g100.groupby("hot_items").busiest_mean_pct.agg(["min", "max"]).round(3)
    # 100台→ 50台からの下がり方
    def drop(df):
        a5 = df[df.servers == 50].set_index(["hot_share", "hot_items", "rest_skew_a"]).busiest_mean_pct
        a10 = df[df.servers == 100].set_index(["hot_share", "hot_items", "rest_skew_a"]).busiest_mean_pct
        return (1 - a10 / a5) * 100
    dr = drop(grid).round(2).reset_index(name="drop_50_to_100_pct")
    dr.to_csv(RES / "grid_drop_50_to_100.csv", index=False)
    robust = dict(
        k1_max_abs_diff_from_formula_pt=round(float((g1.busiest_mean_pct - g1.formula_k1_pct).abs().max()), 3),
        k1_a0_5_max_abs_diff_pt=round(float((g1[g1.rest_skew_a <= 0.5].busiest_mean_pct - g1[g1.rest_skew_a <= 0.5].formula_k1_pct).abs().max()), 3),
        servers100_busiest_by_hot_items={str(k): [float(piv.loc[k, "min"]), float(piv.loc[k, "max"])] for k in piv.index},
        drop_50_to_100_by_hot_share={str(hh): [round(float(s.drop_50_to_100_pct.min()), 2), round(float(s.drop_50_to_100_pct.max()), 2)]
                                     for hh, s in dr[dr.hot_items == 1].groupby("hot_share")},
        drop_50_to_100_k100={str(hh): [round(float(s.drop_50_to_100_pct.min()), 2), round(float(s.drop_50_to_100_pct.max()), 2)]
                             for hh, s in dr[dr.hot_items == 100].groupby("hot_share")},
    )

    # 残り（1−h）の中でいちばん多いデータの割合（式）
    robust["rest_top_item_pct_h1pct"] = {str(a): round(float(0.99 / np.sum(np.arange(1, N, dtype=float) ** (-a))) * 100, 3)
                                         for a in [0.0, 0.5, 0.8]}

    # ---- 図 ----
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    ax.fill_between(hot.index, hot.busiest_p10_pct, hot.busiest_p90_pct, color=LIGHT, alpha=0.6)
    ax.plot(hot.index, hot.busiest_mean_pct, "o-", color=BLUE, ms=4, label="人気の1件に読み書きの1割")
    ax.plot(cold.index, cold.busiest_mean_pct, "o-", color=GRAY, ms=4, label="人気のデータなし")
    ax.plot(hot.index, hot.formula_pct, ":", color=INK, label="目安の式 10%＋90%÷台数")
    ax.axhline(10, color=ORANGE, ls="--", lw=1)
    ax.text(1.1, 9.5, "人気の1件の10%", color=ORANGE, fontsize=8, va="top", ha="left")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(NS, [str(n) for n in NS], fontsize=8)
    ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100], ["0.5", "1", "2", "5", "10", "20", "50", "100"])
    ax.set_xlabel("台数")
    ax.set_ylabel("いちばん忙しい1台の負荷（全体の%）")
    ax.set_title("人気の1件があると、10台あたりから下がり方がにぶる")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1310_busiest.png", SRC)

    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    sel = [5, 10, 20, 50, 100, 200]
    hp = [hot.loc[n, "busiest_mean_pct"] * hot.loc[n, "hot_part_of_busiest_pct"] / 100 for n in sel]
    rp = [hot.loc[n, "busiest_mean_pct"] - x for n, x in zip(sel, hp)]
    x = np.arange(len(sel))
    ax.bar(x, hp, color=ORANGE, label="人気の1件の分")
    ax.bar(x, rp, bottom=hp, color=BLUE, label="ほかのデータの分")
    ax.set_xticks(x, [f"{n}台" for n in sel])
    ax.set_ylim(0, None)
    ax.set_ylabel("いちばん忙しい1台の負荷（全体の%）")
    ax.set_title("いちばん忙しい1台の中身：台を増やして減るのは青の分だけ")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1310_breakdown.png", SRC)

    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    for hh, col in [(0.01, LIGHT), (0.05, GREEN), (0.10, BLUE), (0.20, INK)]:
        s = grid[(grid.hot_share == hh) & (grid.hot_items == 1) & (grid.rest_skew_a == 0.5)]
        ax.plot(s.servers, s.capacity_servers, "o-", color=col, ms=4, label=f"人気の1件に{int(hh*100)}%")
    ax.plot(NS_GRID, NS_GRID, ":", color=GRAY, label="偏りがまったくないとき（台数どおり）")
    ax.set_xticks(NS_GRID, [str(n) for n in NS_GRID])
    ax.set_xlim(0, None)
    ax.set_ylim(0, None)
    ax.set_xlabel("台数")
    ax.set_ylabel("全体で扱える量（1台分を1として）")
    ax.set_title("全体で扱える量は、1÷人気の1件の割合で頭打ちになる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1310_capacity.png", SRC)

    main_json = dict(base=base, robust=robust)
    (RES / "a1310_main.json").write_text(json.dumps(main_json, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(base_df.to_string()); print(dbl.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
