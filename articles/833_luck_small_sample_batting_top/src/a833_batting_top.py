"""833 少ない打席の「最高打率」は、件数の少なさで決まるのか？（架空のデータ）

架空のリーグの打者300人。打者ごとに「本当の打率」（打席が無限にあったときの打率）を置き、
打数は、レギュラー（4割の打者：350〜600打数で一様）と控え（6割の打者：5〜350打数、対数で一様）に分ける。
安打は 打数×本当の打率 の二項分布から引く。打数と本当の打率は関係なしと置く。
「最低打数の線」（線以上の打数の打者だけで打率1位を決める）を 0〜500打数で動かして、1位が当たる割合を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 833
SRC = "架空のリーグの打撃成績（作成者が乱数で作成、seed 833）"
rng = np.random.default_rng(SEED)
N_PLAYER = 300
N_REP = 3000
LINES = [0, 10, 25, 50, 100, 200, 300, 400, 500]


def make(rng, n_rep, n=N_PLAYER, sd=0.025, regular_share=0.4):
    p = np.clip(rng.normal(0.260, sd, (n_rep, n)), 0.180, 0.340)
    reg = rng.random((n_rep, n)) < regular_share
    ab_reg = rng.integers(350, 601, (n_rep, n))
    ab_bench = np.round(np.exp(rng.uniform(np.log(5), np.log(350), (n_rep, n)))).astype(int)
    ab = np.where(reg, ab_reg, ab_bench)
    h = rng.binomial(ab, p)
    return p, ab, h


def eval_lines(rng, p, ab, h, lines=LINES):
    avg = h / ab
    tieb = rng.random(avg.shape) * 1e-9
    rows = []
    best_all = p.argmax(1)
    top10_all = np.argsort(-p, 1)[:, :10]
    for t in lines:
        ok = ab >= t
        sc = np.where(ok, avg + tieb, -1.0)
        top = sc.argmax(1)
        has = ok.any(1)
        pe = np.where(ok, p, -1.0)
        best_el = pe.argmax(1)
        idx = np.arange(len(top))
        rows.append({"min_ab": t,
                     "mean_eligible": round(float(ok.sum(1).mean()), 1),
                     "p_top_is_best_eligible": round(float((top == best_el)[has].mean()), 3),
                     "p_top_is_best_all": round(float((top == best_all)[has].mean()), 3),
                     "p_top_in_true_top10_all": round(float(np.mean([top[i] in top10_all[i] for i in idx[has]])), 3),
                     "p_best_all_eligible": round(float(ok[idx, best_all].mean()), 3),
                     "top_obs_avg_mean": round(float(avg[idx, top][has].mean()), 3),
                     "top_true_avg_mean": round(float(p[idx, top][has].mean()), 3),
                     "top_ab_median": float(np.median(ab[idx, top][has]))})
    return pd.DataFrame(rows)


def main():
    # 1シーズン分（data に保存）
    p1, ab1, h1 = make(rng, 1)
    df = pd.DataFrame({"player_id": np.arange(1, N_PLAYER + 1), "true_avg": p1[0], "ab": ab1[0], "hits": h1[0]})
    df["avg"] = df.hits / df.ab
    df.to_csv(DATA / "batters_one_season.csv", index=False, float_format="%.4f")
    top5 = df.sort_values(["avg", "ab"], ascending=[False, False]).head(5)
    one = {"top5_no_line": top5[["player_id", "ab", "hits", "avg", "true_avg"]].round(3).to_dict("records"),
           "n_avg_ge_400": int((df.avg >= .4).sum()),
           "n_avg_ge_400_ab_lt_50": int(((df.avg >= .4) & (df.ab < 50)).sum()),
           "true_best": df.loc[df.true_avg.idxmax(), ["player_id", "ab", "avg", "true_avg"]].round(3).to_dict(),
           "top_line300": df[df.ab >= 300].sort_values("avg", ascending=False).head(1)[
               ["player_id", "ab", "avg", "true_avg"]].round(3).to_dict("records")[0]}

    p, ab, h = make(np.random.default_rng(SEED * 10), N_REP)
    base = eval_lines(np.random.default_rng(SEED * 10 + 1), p, ab, h)
    base.to_csv(RES / "by_min_ab.csv", index=False)
    avg = h / ab
    # 打率4割以上の打者は、打数がどれくらいか
    ge4 = avg >= .4
    ab_band = {"5-24": (5, 24), "25-49": (25, 49), "50-99": (50, 99), "100-199": (100, 199),
               "200-349": (200, 349), "350-600": (350, 600)}
    share_ge4 = {k: round(float(ge4[(ab >= a) & (ab <= b)].mean()), 4) for k, (a, b) in ab_band.items()}
    mean_n_ge4 = round(float(ge4.sum(1).mean()), 2)
    mean_n_ge4_lt50 = round(float((ge4 & (ab < 50)).sum(1).mean()), 2)

    # 確かめ：本当の打率の散らばりと、控えの割合
    sens = []
    k = 0
    for sd in [0.015, 0.025, 0.035]:
        for rs in [0.2, 0.4, 0.6]:
            k += 1
            pp, aa, hh = make(np.random.default_rng(SEED * 100 + k), 1500, sd=sd, regular_share=rs)
            e = eval_lines(np.random.default_rng(SEED * 1000 + k), pp, aa, hh, [0, 50, 100, 300, 400])
            row = {"true_sd": sd, "regular_share": rs}
            for _, r in e.iterrows():
                row[f"best_all_line{int(r.min_ab)}"] = r.p_top_is_best_all
                row[f"top10_line{int(r.min_ab)}"] = r.p_top_in_true_top10_all
            row["top_ab_median_line0"] = float(e.loc[e.min_ab == 0, "top_ab_median"].item())
            sens.append(row)
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    best_line = {f"{r.true_sd}_{r.regular_share}": int(max([0, 50, 100, 300, 400], key=lambda t: r[f"top10_line{t}"]))
                 for _, r in sens.iterrows()}

    out = {"settings": {"n_player": N_PLAYER, "true_avg_mean": 0.260, "true_avg_sd": 0.025, "clip": [0.18, 0.34],
                        "regular_share": 0.4, "ab_regular": [350, 600], "ab_bench_loguniform": [5, 350],
                        "n_rep": N_REP},
           "by_min_ab": base.to_dict("records"), "share_avg_ge_400_by_ab": share_ge4,
           "mean_players_avg_ge_400": mean_n_ge4, "mean_players_avg_ge_400_ab_lt_50": mean_n_ge4_lt50, "one_season": one,
           "sensitivity": sens.to_dict("records"), "best_line_for_top10_by_setting": best_line}
    json.dump(out, open(RES / "a833_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1シーズンの打数と打率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df.ab, df.avg, s=9, color=BLUE, alpha=.5, lw=0)
    t = top5.iloc[0]
    ax.scatter([t.ab], [t.avg], s=50, color=ORANGE, zorder=3)
    ax.annotate(f"打率1位（線なし）：{int(t.hits)}安打／{int(t.ab)}打数", (t.ab, t.avg), xytext=(t.ab * 1.6, t.avg - .02),
                fontsize=8.5, color=ORANGE, arrowprops=dict(arrowstyle="-", color=ORANGE, lw=.8))
    b = df.loc[df.true_avg.idxmax()]
    ax.scatter([b.ab], [b.avg], s=50, color=GREEN, zorder=3, marker="D")
    ax.annotate(f"本当の打率1位（{b.true_avg:.3f}）", (b.ab, b.avg), xytext=(b.ab * 0.35, b.avg + .07),
                fontsize=8.5, color=GREEN, arrowprops=dict(arrowstyle="-", color=GREEN, lw=.8))
    ax.set_xscale("log"); ax.set_xlabel("打数（対数の目盛り）"); ax.set_ylabel("見かけの打率")
    ax.set_xticks([5, 10, 25, 50, 100, 200, 400, 600]); ax.set_xticklabels(["5", "10", "25", "50", "100", "200", "400", "600"])
    ax.minorticks_off()
    ax.set_title("打数が少ない打者ほど、打率は上にも下にも振れる（打者300人）")
    save(fig, "a833_scatter.png", SRC)

    # 図2：最低打数の線と、1位が当たる割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(base))
    ax.plot(x, base.p_top_is_best_eligible * 100, "o-", color=BLUE, label="線を越えた打者の中で、本当にいちばん")
    ax.plot(x, base.p_top_is_best_all * 100, "s-", color=ORANGE, label="打者全員の中で、本当にいちばん")
    ax.plot(x, base.p_top_in_true_top10_all * 100, "^-", color=GREEN, label="打者全員の中で、本当の上位10人に入る")
    ax.set_xticks(x); ax.set_xticklabels([str(t) for t in base.min_ab])
    ax.set_xlabel("最低打数の線（この打数以上の打者だけで打率1位を決める）")
    ax.set_ylabel("打率1位が当たっていた割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("線を上げると「線の中の1位」は当たるが、全員の中の1位は取りこぼす")
    save(fig, "a833_lines.png", SRC)

    # 図3：打数ごとの、打率4割以上になった打者の割合
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ks = list(share_ge4.keys())
    ax.bar(range(len(ks)), [share_ge4[k] * 100 for k in ks], color=BLUE)
    for i, k in enumerate(ks):
        v = share_ge4[k] * 100
        ax.text(i, v + .3, f"{v:.1f}%" if v >= 1 else f"{v:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(range(len(ks))); ax.set_xticklabels([f"{k}打数" for k in ks], fontsize=9)
    ax.set_ylabel("打率4割以上の打者の割合（%）")
    ax.set_title("本当の打率の上限を .340 と置いたのに、少ない打数では4割が出る")
    save(fig, "a833_ge400.png", SRC)
    print(json.dumps({k: out[k] for k in ["share_avg_ge_400_by_ab", "mean_players_avg_ge_400", "mean_players_avg_ge_400_ab_lt_50", "one_season",
                                          "best_line_for_top10_by_setting"]}, ensure_ascii=False, indent=1))
    print(base.to_string()); print(sens.to_string())


if __name__ == "__main__":
    main()
