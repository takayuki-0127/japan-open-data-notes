"""1189 1件が何往復もするとき、件数で数えるか往復の数で数えるかで、忙しい種類の順はどう変わるのか？（架空のデータ）

作成者が置いた架空の会社の窓口。問い合わせの種類は8つ（A〜H）。種類ごとに、件数の割合・1件の平均の往復の数（担当の返信の数）・
1回目の返信にかかる時間の目安（分）を置く。2回目以降の返信は1回目の ρ 倍（基本0.4）の時間がかかる。
1件の往復の数＝1＋追加の回数。追加の回数は、平均（平均の往復の数−1）のまわりに散らばり、ときどき長く続く件が出る
（散らばりの形 k：小さいほど長く続く件が多い。基本 k=1）。1回の返信の時間は目安を平均に散らばる（標準偏差は平均の0.5倍）。
本当の忙しさ＝種類ごとの返信の時間の合計（長い目で見た値＝置いた値からの期待値）。
数え方：①件数　②往復の数（担当の返信の数）　③返信の時間の合計（本当の忙しさ）
(1) 例の窓口：長い目で見た割合と順（置いた値からの式）。1か月3,000件の例も1件ずつ作る
(2) でたらめに作った窓口（各1,000か所）：種類ごとの件数の割合・平均の往復の数・1回目の時間をでたらめに置き、
    ①・②の1位が③の1位と同じ窓口の割合と、③との割合のずれ（種類ごとの割合の差の絶対値の合計の半分）を数える。
    平均の往復の数と1回目の時間の結びつき（−0.8・−0.4・0・0.4・0.8）×ρ（0.2・0.4・0.7・1.0）
    ×往復の数の散らばり（0.4・0.7・1.0）×1回目の時間の散らばり（0.3・0.6・0.9）＝180通り
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1189
SRC = "架空の会社の問い合わせ窓口（作成者が置いた種類ごとの件数・往復の数・返信の時間からの乱数、seed 1189）"
TYPES = pd.DataFrame({
    "type": list("ABCDEFGH"),
    "name": ["使い方の質問", "請求の確認", "ログインできない", "不具合の報告", "解約の手続き", "設定の相談", "返品・交換", "その他"],
    "share": [0.30, 0.16, 0.15, 0.10, 0.09, 0.08, 0.07, 0.05],
    "mean_rounds": [1.4, 1.5, 3.6, 3.0, 1.6, 2.0, 2.6, 1.3],
    "first_min": [6, 9, 4, 12, 10, 30, 8, 5],
})
RHO, K, N_MONTH = 0.4, 1.0, 3000
NOISE_SHAPE = 4.0           # 1回の返信の時間の散らばり（標準偏差は平均の0.5倍）
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def expected(types, rho):
    t = types.copy()
    t["count_share"] = t.share
    t["rounds_share"] = t.share * t.mean_rounds / (t.share * t.mean_rounds).sum()
    per = t.first_min * (1 + rho * (t.mean_rounds - 1))
    t["minutes_per_case"] = per
    t["minutes_share"] = t.share * per / (t.share * per).sum()
    t["minutes_per_round"] = per / t.mean_rounds
    for c in ["count_share", "rounds_share", "minutes_share"]:
        t[c.replace("_share", "_rank")] = t[c].rank(ascending=False, method="min").astype(int)
    return t


def random_windows(rng, corr, rho, sd_r, sd_t, w=1000):
    """でたらめに作った w か所の窓口（種類8つ）。返り値は①・②の1位の当たりと割合のずれ"""
    share = rng.dirichlet(np.full(8, 1.5), size=w)
    z1 = rng.standard_normal((w, 8))
    z2 = corr * z1 + np.sqrt(1 - corr ** 2) * rng.standard_normal((w, 8))
    mean_rounds = 1 + np.exp(sd_r * z1)              # 平均の往復の数（1＋追加の平均。追加の平均の真ん中は1回）
    first = 9 * np.exp(sd_t * z2)                    # 1回目の時間（分、真ん中は9分）
    cnt = share
    rnd = share * mean_rounds
    mins = share * first * (1 + rho * (mean_rounds - 1))
    top = mins.argmax(axis=1)
    norm = lambda v: v / v.sum(axis=1, keepdims=True)
    tv_c = 0.5 * np.abs(norm(cnt) - norm(mins)).sum(axis=1)
    tv_r = 0.5 * np.abs(norm(rnd) - norm(mins)).sum(axis=1)
    top3 = np.argsort(-mins, axis=1)[:, :3]
    t3 = lambda v: np.mean([set(a_) == set(b_) for a_, b_ in zip(np.argsort(-v, axis=1)[:, :3], top3)])
    return {"count_top_match": (cnt.argmax(axis=1) == top).mean(), "rounds_top_match": (rnd.argmax(axis=1) == top).mean(),
            "count_top3_same": t3(cnt), "rounds_top3_same": t3(rnd),
            "count_share_gap": tv_c.mean(), "rounds_share_gap": tv_r.mean(),
            "rounds_closer_windows": (tv_r < tv_c).mean()}


def main():
    rng = np.random.default_rng(SEED)
    ex = expected(TYPES, RHO)
    ex.round(4).to_csv(RES / "types_expected.csv", index=False)

    # 1か月分の例（1件ずつ）
    rex = np.random.default_rng(SEED + 1)
    typ = rex.choice(8, size=N_MONTH, p=TYPES.share.values)
    mu = TYPES.mean_rounds.values[typ] - 1
    extra = rex.negative_binomial(K, K / (K + mu))
    t1 = TYPES.first_min.values[typ]
    first = t1 * rex.gamma(NOISE_SHAPE, 1 / NOISE_SHAPE, size=N_MONTH)
    later = np.array([RHO * t1[i] * rex.gamma(NOISE_SHAPE, 1 / NOISE_SHAPE, size=extra[i]).sum() for i in range(N_MONTH)])
    case = pd.DataFrame({"case_id": np.arange(1, N_MONTH + 1), "type": TYPES.type.values[typ],
                         "rounds": 1 + extra, "minutes": np.round(first + later, 2)})
    case.to_csv(DATA / "cases_example_month.csv", index=False)
    ce = case.groupby("type").agg(count=("case_id", "size"), rounds=("rounds", "sum"), minutes=("minutes", "sum")).reset_index()
    ce["minutes"] = ce.minutes.round(2)
    longest = case.sort_values("rounds", ascending=False).head(5)

    # (2) でたらめに作った窓口 180通り
    rows = []
    for corr in [-0.8, -0.4, 0, 0.4, 0.8]:
        for rho in [0.2, 0.4, 0.7, 1.0]:
            for sd_r in [0.4, 0.7, 1.0]:
                for sd_t in [0.3, 0.6, 0.9]:
                    x = random_windows(rng, corr, rho, sd_r, sd_t)
                    rows.append({"corr_rounds_time": corr, "rho": rho, "sd_rounds": sd_r, "sd_first_time": sd_t,
                                 **{k_: r(v_) for k_, v_ in x.items()}})
    grid = pd.DataFrame(rows)
    grid["rounds_minus_count_top_match"] = (grid.rounds_top_match - grid.count_top_match).round(4)
    grid.to_csv(RES / "grid.csv", index=False)
    g = grid
    by_corr = g.groupby("corr_rounds_time").agg(
        count_top_match_mean=("count_top_match", "mean"), rounds_top_match_mean=("rounds_top_match", "mean"),
        count_share_gap_mean=("count_share_gap", "mean"), rounds_share_gap_mean=("rounds_share_gap", "mean"),
        n_rounds_better_top=("rounds_minus_count_top_match", lambda v: int((v > 0).sum())),
        rounds_minus_count_min=("rounds_minus_count_top_match", "min"), rounds_minus_count_max=("rounds_minus_count_top_match", "max"),
        n=("rho", "size")).round(4).reset_index()
    by_corr.to_csv(RES / "by_corr.csv", index=False)
    mid = g[(g.rho == 0.4) & (g.sd_rounds == 0.7) & (g.sd_first_time == 0.6)].set_index("corr_rounds_time")
    robust = {
        "n": int(len(g)),
        "n_rounds_better_top": int((g.rounds_minus_count_top_match > 0).sum()),
        "n_count_better_top": int((g.rounds_minus_count_top_match < 0).sum()),
        "count_top_match_min": r(g.count_top_match.min()), "count_top_match_max": r(g.count_top_match.max()),
        "rounds_top_match_min": r(g.rounds_top_match.min()), "rounds_top_match_max": r(g.rounds_top_match.max()),
        "max_top_match_any": r(np.maximum(g.count_top_match, g.rounds_top_match).max()),
        "neg_corr_n": int((g.corr_rounds_time < 0).sum()),
        "neg_corr_n_count_better": int(((g.corr_rounds_time < 0) & (g.rounds_minus_count_top_match < 0)).sum()),
        "pos_corr_n": int((g.corr_rounds_time > 0).sum()),
        "pos_corr_n_rounds_better": int(((g.corr_rounds_time > 0) & (g.rounds_minus_count_top_match > 0)).sum()),
        "zero_corr_n_rounds_better": int(((g.corr_rounds_time == 0) & (g.rounds_minus_count_top_match > 0)).sum()),
        "zero_corr_n": int((g.corr_rounds_time == 0).sum()),
        "rho1_zero_corr_rounds_better": int(((g.corr_rounds_time == 0) & (g.rho == 1.0) & (g.rounds_minus_count_top_match > 0)).sum()),
        "middle_setting": {str(k_): {"count_top_match": r(v_.count_top_match), "rounds_top_match": r(v_.rounds_top_match),
                                      "count_share_gap": r(v_.count_share_gap), "rounds_share_gap": r(v_.rounds_share_gap)}
                           for k_, v_ in mid.iterrows()},
        "by_sd_first_time": g.groupby("sd_first_time")[["count_top_match", "rounds_top_match"]].agg(["min", "max"]).round(4).values.tolist(),
    }

    e = ex.set_index("type")
    headline = {
        "count_top": e.count_share.idxmax(), "rounds_top": e.rounds_share.idxmax(), "minutes_top": e.minutes_share.idxmax(),
        "F_count_share": r(e.loc["F", "count_share"]), "F_rounds_share": r(e.loc["F", "rounds_share"]), "F_minutes_share": r(e.loc["F", "minutes_share"]),
        "A_count_share": r(e.loc["A", "count_share"]), "A_minutes_share": r(e.loc["A", "minutes_share"]),
        "C_rounds_share": r(e.loc["C", "rounds_share"]), "C_minutes_share": r(e.loc["C", "minutes_share"]),
        "F_count_rank": int(e.loc["F", "count_rank"]), "F_rounds_rank": int(e.loc["F", "rounds_rank"]),
        "C_minutes_rank": int(e.loc["C", "minutes_rank"]), "A_minutes_rank": int(e.loc["A", "minutes_rank"]),
        "middle_corr_m08_count_top_match": robust["middle_setting"]["-0.8"]["count_top_match"],
        "middle_corr_m08_rounds_top_match": robust["middle_setting"]["-0.8"]["rounds_top_match"],
        "middle_corr_p08_count_top_match": robust["middle_setting"]["0.8"]["count_top_match"],
        "middle_corr_p08_rounds_top_match": robust["middle_setting"]["0.8"]["rounds_top_match"],
    }
    out = {"settings": {"types": TYPES.to_dict("records"), "rho": RHO, "k": K, "cases_per_month": N_MONTH,
                        "reply_time_sd_over_mean": 0.5, "random_windows_per_setting": 1000, "seed": SEED},
           "headline": headline,
           "example_month": {"by_type": ce.to_dict("records"),
                             "longest_cases": longest.to_dict("records"),
                             "rounds_total": int(case.rounds.sum()), "minutes_total": r(case.minutes.sum(), 2)},
           "robust": robust}
    with open(RES / "a1189_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

    # 図1：3つの数え方の割合
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    x = np.arange(8)
    w = 0.27
    for i, (col, lab, cl) in enumerate([("count_share", "①件数", GRAY), ("rounds_share", "②往復の数", BLUE), ("minutes_share", "③返信の時間（本当の忙しさ）", ORANGE)]):
        ax.bar(x + (i - 1) * w, ex[col] * 100, w, color=cl, label=lab)
        for xi, v, rk in zip(x, ex[col] * 100, ex[col.replace("_share", "_rank")]):
            if rk == 1:
                ax.text(xi + (i - 1) * w, v + 0.6, "1位", ha="center", fontsize=8, color=cl)
    ax.set_xticks(x, [f"{t}\n{n}" if len(n) <= 5 else f"{t}\n{n[:4]}\n{n[4:]}" for t, n in zip(TYPES.type, TYPES.name)], fontsize=8.5)
    ax.set_ylabel("全体に占める割合（%）")
    ax.set_ylim(0, max(ex.count_share.max(), ex.rounds_share.max(), ex.minutes_share.max()) * 100 * 1.2)
    ax.set_title("同じ問い合わせでも、数え方で1位の種類が入れかわった（置いた値からの式どおり）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1189_shares.png", SRC)

    # 図2：結びつきごとの1位の当たり（180通り）
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    cs = [-0.8, -0.4, 0, 0.4, 0.8]
    for i, (name, lab, cl) in enumerate([("count", "①件数の1位", GRAY), ("rounds", "②往復の数の1位", BLUE)]):
        for j, cc in enumerate(cs):
            v = g[g.corr_rounds_time == cc][f"{name}_top_match"].values * 100
            xx = j + (i - 0.5) * 0.3 + np.linspace(-0.1, 0.1, len(v))
            ax.scatter(xx, v, s=9, color=cl, alpha=0.7, label=lab if j == 0 else None)
        ax.plot(np.arange(5) + (i - 0.5) * 0.3, by_corr[f"{name}_top_match_mean"] * 100, color=cl, lw=1.5, marker="_", ms=14)
    ax.set_xticks(range(5), [f"{c:g}" for c in cs])
    ax.set_xlabel("平均の往復の数と1回目の時間の結びつき（負：往復の多い種類ほど1回が短い）")
    ax.set_ylabel("1位が③の1位と同じだった窓口（%）")
    ax.set_ylim(0, 100)
    ax.set_title("でたらめに作った窓口（180通り×各1,000か所）：1位の当たり")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1189_corr_top.png", SRC)

    # 図3：割合のずれ
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x5 = np.arange(5)
    ax.bar(x5 - 0.18, by_corr.count_share_gap_mean, 0.36, color=GRAY, label="①件数の割合と③の割合のずれ")
    ax.bar(x5 + 0.18, by_corr.rounds_share_gap_mean, 0.36, color=BLUE, label="②往復の数の割合と③の割合のずれ")
    for xi, a_, b_ in zip(x5, by_corr.count_share_gap_mean, by_corr.rounds_share_gap_mean):
        ax.text(xi - 0.18, a_ + 0.004, f"{a_:g}", ha="center", fontsize=8)
        ax.text(xi + 0.18, b_ + 0.004, f"{b_:g}", ha="center", fontsize=8)
    ax.set_xticks(x5, [f"{c:g}" for c in cs])
    ax.set_xlabel("平均の往復の数と1回目の時間の結びつき")
    ax.set_ylabel("割合のずれ（0〜1、36通りの平均）")
    ax.set_ylim(0, max(by_corr.count_share_gap_mean.max(), by_corr.rounds_share_gap_mean.max()) * 1.25)
    ax.set_title("③の割合とのずれ（種類ごとの差の絶対値の合計の半分）")
    ax.legend(frameon=False, fontsize=9, loc="upper center")
    save(fig, "a1189_share_gap.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), json.dumps(robust, ensure_ascii=False, default=str)[:2500], round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
