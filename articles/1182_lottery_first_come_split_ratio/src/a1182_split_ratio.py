"""1182 先着の枠と抽選の枠に分けると、抽選の枠の倍率はどう見えるのか？（架空のデータ）

作成者が置いた架空の講座（席1,000）。席を「先着の枠」と「抽選の枠」に分ける。
行きたい人の数は平均3,000人（1人ずつ独立に来る数の乱数）で、全体の倍率（行きたい人÷席）はおよそ3倍。
1人ひとりが、抽選に申し込むか（確率 P_LOT）、先着に挑むか（確率 P_TRY）を乱数で決める。
順番は2通り：
  先着が先：先着に挑んだ人のうち早い順に先着の枠が埋まる。先着で取れなかった人と挑まなかった人が、P_LOT で抽選に申し込む
  抽選が先：行きたい人が P_LOT で抽選に申し込み、抽選の枠を当てる。外れた人と申し込まなかった人が、P_TRY で先着に挑む
「抽選の枠の倍率」＝抽選に申し込んだ人÷抽選の枠。これに全部の席を掛けた値を「行きたい人の見込み」として、本当の行きたい人と比べる。
(1) 基本（先着の割合40%、P_LOT=0.9、P_TRY=0.6）を各2,000回
(2) 先着の割合 0〜80% を各2,000回
(3) 確かめ：全体の倍率（1.2・2・3・6倍）×先着の割合（0・20・40・60・80%）×P_LOT（0.7・0.9・1.0）×P_TRY（0.3・0.6・0.9）×順番2通り＝360通り（各200回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1182
SRC = "架空の講座の先着と抽選（作成者が置いた申し込み方からの乱数、seed 1182）"
SEATS = 1000
WANT = 3000
P_LOT, P_TRY, SHARE = 0.9, 0.6, 0.4
R_MAIN, R_GRID = 2000, 200
ORDERS = {"first": "先着が先", "lottery": "抽選が先"}
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def run(rng, n, want_mean, share, p_lot, p_try, order):
    """n 回分を、人数の数え上げ（何人のうち何人かをまとめて引く乱数）で回す。1人ひとりを乱数で決めるのと同じ分布"""
    w = rng.poisson(want_mean, n)
    s_first = int(round(SEATS * share))
    s_lot = SEATS - s_first
    if order == "first":
        tries = rng.binomial(w, p_try)
        got_first = np.minimum(tries, s_first)
        rest = w - got_first                      # 先着で取れなかった人＋挑まなかった人
        apps = rng.binomial(rest, p_lot)
        won = np.minimum(apps, s_lot)
    else:
        apps = rng.binomial(w, p_lot)
        won = np.minimum(apps, s_lot)
        rest = w - won                            # 外れた人＋申し込まなかった人
        tries = rng.binomial(rest, p_try)
        got_first = np.minimum(tries, s_first)
    with np.errstate(divide="ignore", invalid="ignore"):
        lot_ratio = np.where(s_lot > 0, apps / max(s_lot, 1), np.nan)
    return pd.DataFrame({
        "want": w, "lottery_apps": apps, "lottery_won": won, "first_tries": tries, "first_got": got_first,
        "overall_ratio": w / SEATS, "lottery_ratio": lot_ratio,
        "est_want": lot_ratio * SEATS, "est_over_true": lot_ratio * SEATS / w,
        "seated_share": (won + got_first) / w, "empty_seats": SEATS - won - got_first,
        "lottery_win_rate": np.where(apps > 0, won / np.maximum(apps, 1), np.nan),
    })


def summarize(df):
    q = df["lottery_ratio"].quantile([0.1, 0.9])
    return {
        "overall_ratio": r(df["overall_ratio"].mean()),
        "lottery_ratio": r(df["lottery_ratio"].mean()),
        "lottery_ratio_p10": r(q.iloc[0]), "lottery_ratio_p90": r(q.iloc[1]),
        "lottery_over_overall": r((df["lottery_ratio"] / df["overall_ratio"]).mean()),
        "est_want": r(df["est_want"].mean(), 1),
        "est_over_true": r(df["est_over_true"].mean()),
        "seated_share": r(df["seated_share"].mean()),
        "lottery_win_rate": r(df["lottery_win_rate"].mean()),
        "first_tries": r(df["first_tries"].mean(), 1),
        "lottery_apps": r(df["lottery_apps"].mean(), 1),
        "empty_seats": r(df["empty_seats"].mean(), 2),
    }


def formula(want, share, p_lot, p_try, order):
    """先着が埋まる・抽選が埋まる場合の式の値（申し込みの見込みの数）"""
    s_first = SEATS * share
    s_lot = SEATS - s_first
    if s_lot == 0:
        return np.nan
    if order == "first":
        got = min(want * p_try, s_first)
        apps = (want - got) * p_lot
    else:
        apps = want * p_lot
    return apps / s_lot


def person_example(rng):
    """基本の1回を、1人ひとりの乱数で回した記録（data 用）"""
    w = rng.poisson(WANT)
    tri = rng.random(w) < P_TRY
    arrival = rng.permutation(w)
    s_first = int(SEATS * SHARE)
    order_idx = np.argsort(np.where(tri, arrival, w + arrival))
    got = np.zeros(w, bool)
    got[order_idx[:min(tri.sum(), s_first)]] = True
    app = (~got) & (rng.random(w) < P_LOT)
    won = np.zeros(w, bool)
    ids = np.flatnonzero(app)
    won[rng.choice(ids, min(len(ids), SEATS - s_first), replace=False)] = True
    return pd.DataFrame({"person_id": np.arange(1, w + 1), "tried_first": tri.astype(int), "got_first": got.astype(int),
                         "applied_lottery": app.astype(int), "won_lottery": won.astype(int)})


def main():
    rng = np.random.default_rng(SEED)
    ex = person_example(np.random.default_rng(SEED + 1))
    ex.to_csv(DATA / "persons_example.csv", index=False)
    ex_sum = {"want": int(len(ex)), "got_first": int(ex.got_first.sum()), "applied_lottery": int(ex.applied_lottery.sum()),
              "won_lottery": int(ex.won_lottery.sum()),
              "lottery_ratio": r(ex.applied_lottery.sum() / (SEATS - SEATS * SHARE))}

    # (1) 基本
    base = {}
    for o, name in ORDERS.items():
        df = run(rng, R_MAIN, WANT, SHARE, P_LOT, P_TRY, o)
        s = summarize(df)
        s["formula_lottery_ratio"] = r(formula(WANT, SHARE, P_LOT, P_TRY, o))
        s["order"] = name
        base[o] = s

    # (2) 先着の割合
    rows = []
    for share in [0.0, 0.2, 0.4, 0.6, 0.8]:
        for o, name in ORDERS.items():
            df = run(rng, R_MAIN, WANT, share, P_LOT, P_TRY, o)
            s = summarize(df)
            s.update({"order": name, "first_share_pct": int(share * 100),
                      "formula_lottery_ratio": r(formula(WANT, share, P_LOT, P_TRY, o))})
            rows.append(s)
    by_share = pd.DataFrame(rows)
    cols = ["order", "first_share_pct"] + [c for c in by_share.columns if c not in ("order", "first_share_pct")]
    by_share = by_share[cols]
    by_share.to_csv(RES / "by_first_share.csv", index=False)

    # (3) 確かめ 360通り
    rows = []
    for ratio in [1.2, 2, 3, 6]:
        for share in [0.0, 0.2, 0.4, 0.6, 0.8]:
            for pl in [0.7, 0.9, 1.0]:
                for pt in [0.3, 0.6, 0.9]:
                    for o, name in ORDERS.items():
                        df = run(rng, R_GRID, ratio * SEATS, share, pl, pt, o)
                        s = summarize(df)
                        s.update({"order": name, "overall_ratio_set": ratio, "first_share_pct": int(share * 100),
                                  "p_lottery": pl, "p_first": pt,
                                  "formula_lottery_ratio": r(formula(ratio * SEATS, share, pl, pt, o))})
                        rows.append(s)
    grid = pd.DataFrame(rows)
    gcols = ["order", "overall_ratio_set", "first_share_pct", "p_lottery", "p_first"]
    grid = grid[gcols + [c for c in grid.columns if c not in gcols]]
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid.copy()
    g["gap_formula"] = (g["lottery_ratio"] - g["formula_lottery_ratio"]).abs()
    robust = {
        "n": int(len(g)),
        "est_over_true_min": r(g.est_over_true.min()), "est_over_true_max": r(g.est_over_true.max()),
        "est_over_true_median": r(g.est_over_true.median()),
        "share_over_1_1": r((g.est_over_true > 1.1).mean() * 100, 2),
        "share_under_0_9": r((g.est_over_true < 0.9).mean() * 100, 2),
        "by_order": {ORDERS[o]: {"min": r(x.est_over_true.min()), "median": r(x.est_over_true.median()),
                                  "max": r(x.est_over_true.max())}
                     for o, x in ((o, g[g.order == ORDERS[o]]) for o in ORDERS)},
        "share0_min": r(g[g.first_share_pct == 0].est_over_true.min()),
        "share0_max": r(g[g.first_share_pct == 0].est_over_true.max()),
        "share_pos_lottery_first_min": r(g[(g.first_share_pct > 0) & (g.order == "抽選が先")].est_over_true.min()),
        "share_pos_first_first_under1_pct": r(((g.first_share_pct > 0) & (g.order == "先着が先") & (g.est_over_true < 1)).sum()
                                              / ((g.first_share_pct > 0) & (g.order == "先着が先")).sum() * 100, 2),
        "max_gap_formula_when_full": r(g[(g.empty_seats < 0.5)]["gap_formula"].max()),
        "n_with_empty_seats": int((g.empty_seats >= 0.5).sum()),
        "n_ratio_over2_empty_over100": int(((g.lottery_ratio > 2) & (g.empty_seats >= 100)).sum()),
    }
    ex_e = g[(g.order == "抽選が先") & (g.overall_ratio_set == 1.2) & (g.first_share_pct == 80)
             & (g.p_lottery == 0.9) & (g.p_first == 0.3)].iloc[0]
    robust["empty_example"] = {"order": "抽選が先", "overall_ratio_set": 1.2, "first_share_pct": 80, "p_lottery": 0.9,
                               "p_first": 0.3, "lottery_ratio": r(ex_e.lottery_ratio), "empty_seats": r(ex_e.empty_seats, 2),
                               "seated_share": r(ex_e.seated_share)}
    by_share_s = g.groupby("first_share_pct")["est_over_true"].agg(["min", "median", "max"]).round(4).reset_index()
    robust["by_share"] = by_share_s.to_dict("records")

    bs = by_share.set_index(["order", "first_share_pct"])
    headline = {
        "base_overall_ratio": base["first"]["overall_ratio"],
        "base_first_first_lottery_ratio": base["first"]["lottery_ratio"],
        "base_lottery_first_lottery_ratio": base["lottery"]["lottery_ratio"],
        "base_first_first_est_over_true": base["first"]["est_over_true"],
        "base_lottery_first_est_over_true": base["lottery"]["est_over_true"],
        "share80_lottery_first_ratio": r(bs.loc[("抽選が先", 80), "lottery_ratio"]),
        "share80_first_first_ratio": r(bs.loc[("先着が先", 80), "lottery_ratio"]),
        "share0_lottery_ratio": r(bs.loc[("抽選が先", 0), "lottery_ratio"]),
        "robust_min": robust["est_over_true_min"], "robust_max": robust["est_over_true_max"],
    }
    out = {"settings": {"seats": SEATS, "want_mean": WANT, "first_share": SHARE, "p_lottery": P_LOT, "p_first": P_TRY,
                        "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
           "headline": headline, "base": base, "example_one_run": ex_sum, "robust": robust}
    with open(RES / "a1182_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：先着の割合ごとの抽選の枠の倍率
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    x = np.arange(5)
    wd = 0.36
    for i, (o, c) in enumerate([("先着が先", BLUE), ("抽選が先", ORANGE)]):
        v = by_share[by_share.order == o]["lottery_ratio"].values
        ax.bar(x + (i - 0.5) * wd, v, wd, color=c, label=f"{o}の抽選の枠の倍率")
    ov = base["first"]["overall_ratio"]
    for i, o in enumerate(["先着が先", "抽選が先"]):
        v = by_share[by_share.order == o]["lottery_ratio"].values
        for xi, vi in zip(x, v):
            if ov - 0.6 < vi < ov + 0.1:  # 線と重なる値は棒の中に白で書く
                ax.text(xi + (i - 0.5) * wd, vi - 0.15, f"{vi:.2f}", ha="center", va="top", fontsize=8, color="white")
            else:
                ax.text(xi + (i - 0.5) * wd, vi + 0.15, f"{vi:.2f}", ha="center", fontsize=8)
    ax.axhline(ov, color=INK, ls="--", lw=1, label=f"全体の倍率（行きたい人÷全部の席）{ov:.4f}倍")
    ax.set_xticks(x, ["0%", "20%", "40%", "60%", "80%"])
    ax.set_xlabel("席のうち先着の枠の割合")
    ax.set_ylabel("抽選に申し込んだ人÷抽選の枠（倍）")
    ax.set_ylim(0, by_share["lottery_ratio"].max() * 1.15)
    ax.set_title("先着の枠の割合が大きいほど、抽選の枠の倍率は高く出た")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1182_by_share.png", SRC)

    # 図2：基本の内訳（人数）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    labels = ["行きたい人", "抽選に申し込んだ人", "抽選の枠", "先着の枠"]
    for i, (o, c) in enumerate([("first", BLUE), ("lottery", ORANGE)]):
        b = base[o]
        v = [b["overall_ratio"] * SEATS, b["lottery_apps"], SEATS * (1 - SHARE), SEATS * SHARE]
        y = np.arange(4) + (i - 0.5) * 0.36
        ax.barh(y, v, 0.36, color=c, label=ORDERS[o])
        for k, (yi, vi) in enumerate(zip(y, v)):
            ax.text(vi + 30, yi, f"{vi:,.0f}人" if k < 2 else f"{vi:,.0f}席", va="center", fontsize=8.5)
    ax.set_yticks(np.arange(4), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 3700)
    ax.set_xlabel("人数・席数（2,000回の平均）")
    ax.set_title("先着の割合40%：抽選に申し込む人は、抽選の枠600席を相手にする")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1182_base_counts.png", SRC)

    # 図3：確かめ 360通り
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for i, (o, c) in enumerate([("先着が先", BLUE), ("抽選が先", ORANGE)]):
        sub = g[g.order == o]
        for j, sh in enumerate([0, 20, 40, 60, 80]):
            v = sub[sub.first_share_pct == sh]["est_over_true"].values
            xx = j + (i - 0.5) * 0.3 + np.linspace(-0.1, 0.1, len(v))
            ax.scatter(xx, v, s=8, color=c, alpha=0.55, label=o if j == 0 else None)
    ax.axhline(1, color=INK, lw=1, ls="--")
    ax.set_xticks(range(5), ["0%", "20%", "40%", "60%", "80%"])
    ax.set_xlabel("席のうち先着の枠の割合")
    ax.set_ylabel("（抽選の枠の倍率×全部の席）÷行きたい人")
    ax.set_ylim(0, g["est_over_true"].max() * 1.1)
    ax.set_title("360通りの置き方：倍率から見込んだ行きたい人と本当の人数の比")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1182_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
