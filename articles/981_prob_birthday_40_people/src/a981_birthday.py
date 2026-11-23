"""981 40人の中に同じ誕生日の人がいるのは、珍しいのか？（架空のデータ）

架空の会社の40人のグループ。誕生日（月日）は作成者が置いた起きやすさから乱数で引く。
基本は365日が同じ起きやすさ（2月29日なし）。季節の偏りと2月29日を入れた確かめも行う。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 981
SRC = "架空のグループの誕生日（作成者が乱数で作成、seed 981）"
rng = np.random.default_rng(SEED)
N_GROUP = 200000


def weights(amp=0.0, leap=False):
    """1年の日ごとの起きやすさ。amp は季節の偏りの大きさ（最も多い日÷平均−1）。ピークは9月中ごろ（作成者が置いた）"""
    d = np.arange(365)
    w = 1 + amp * np.cos(2 * np.pi * (d - 257) / 365)
    if leap:
        w = np.append(w, w[58] / 4)  # 2月29日：前後の日の1/4
    return w / w.sum()


def formula_uniform(n, days=365):
    k = np.arange(n)
    return 1 - np.prod((days - k) / days)


def formula_weighted(n, p):
    """起きやすさが日ごとに違うときの、全員が違う日になる確率を、厳密に出す（多項の再帰）"""
    # e_k：p の k 次の基本対称式。全員違う確率 = n! * e_n
    e = np.zeros(n + 1); e[0] = 1.0
    for pi in p:
        e[1:] = e[1:] + pi * e[:-1]
    from math import lgamma, exp, log
    return 1 - exp(lgamma(n + 1) + log(e[n]))


def stats(b):
    """b：グループ×人数の誕生日（日の番号）。同じ日の人がいるか等を数える"""
    s = np.sort(b, axis=1)
    same = (np.diff(s, axis=1) == 0)
    any_pair = same.any(1)
    # 3人以上が同じ日
    triple = (same[:, :-1] & same[:, 1:]).any(1)
    # 同じ日の組の数
    n = b.shape[1]
    days = b.max() + 1
    cnt = np.zeros((b.shape[0], days), dtype=np.int16)
    np.add.at(cnt, (np.repeat(np.arange(b.shape[0]), n), b.ravel()), 1)
    pairs = (cnt * (cnt - 1) // 2).sum(1)
    n_days_shared = (cnt >= 2).sum(1)
    return any_pair, triple, pairs, n_days_shared


def near_pair(b, days=365, gap=1):
    """誕生日が gap 日以内（同じ日を含む、年をまたいで回る）の2人がいるか"""
    s = np.sort(b, axis=1)
    d = np.diff(s, axis=1)
    wrap = s[:, 0] + days - s[:, -1]
    return (d <= gap).any(1) | (wrap <= gap)


def main():
    n = 40
    p0 = weights()
    b = rng.choice(365, size=(N_GROUP, n), p=p0)
    any_pair, triple, pairs, nds = stats(b)
    me = (b[:, 1:] == b[:, [0]]).any(1)
    near1 = near_pair(b, gap=1)
    near3 = near_pair(b, gap=3)
    base = {
        "groups": N_GROUP, "people": n,
        "P_any_same_sim": round(float(any_pair.mean()) * 100, 2),
        "P_any_same_formula": round(formula_uniform(n) * 100, 2),
        "P_someone_same_as_me_sim": round(float(me.mean()) * 100, 2),
        "P_someone_same_as_me_formula": round((1 - (364 / 365) ** (n - 1)) * 100, 2),
        "naive_40_over_365": round(n / 365 * 100, 2),
        "pairs_of_people": n * (n - 1) // 2,
        "mean_same_pairs_sim": round(float(pairs.mean()), 3),
        "mean_same_pairs_formula": round(n * (n - 1) / 2 / 365, 3),
        "share_pairs_0": round(float((pairs == 0).mean()) * 100, 2),
        "share_pairs_1": round(float((pairs == 1).mean()) * 100, 2),
        "share_pairs_2": round(float((pairs == 2).mean()) * 100, 2),
        "share_pairs_3plus": round(float((pairs >= 3).mean()) * 100, 2),
        "P_three_same_day": round(float(triple.mean()) * 100, 2),
        "P_within_1day": round(float(near1.mean()) * 100, 2),
        "P_within_3days": round(float(near3.mean()) * 100, 2),
    }

    # 会社全体：40人のグループが50（2,000人）。同じ誕生日の人がいないグループの数
    g50 = any_pair[: (N_GROUP // 50) * 50].reshape(-1, 50)
    nog = 50 - g50.sum(1)
    vc = pd.Series(nog).value_counts().sort_index()
    company = {"companies": int(len(nog)), "mean_groups_without_same": round(float(nog.mean()), 2),
               "P_no_same_formula": round((1 - formula_uniform(n)) * 100, 2),
               "mean_groups_without_same_formula": round(50 * (1 - formula_uniform(n)), 2),
               "share_company_0_without": round(float((nog == 0).mean()) * 100, 2),
               "p10_without": int(np.quantile(nog, .1)), "p90_without": int(np.quantile(nog, .9)),
               "max_without": int(nog.max())}

    # 人数ごと（365日同じ起きやすさ）：式と乱数
    rows = []
    for k in [5, 10, 15, 20, 23, 25, 30, 35, 40, 50, 60, 70, 80]:
        bb = rng.choice(365, size=(50000, k))
        a, t, pr, _ = stats(bb)
        rows.append({"people": k, "P_same_formula": round(formula_uniform(k) * 100, 2),
                     "P_same_sim": round(float(a.mean()) * 100, 2),
                     "P_same_as_me_formula": round((1 - (364 / 365) ** (k - 1)) * 100, 2),
                     "P_within_1day_sim": round(float(near_pair(bb, gap=1).mean()) * 100, 2),
                     "P_three_same_sim": round(float(t.mean()) * 100, 2)})
    bysize = pd.DataFrame(rows)
    bysize.to_csv(RES / "by_group_size.csv", index=False)

    # 確かめ：季節の偏り（amp）と2月29日
    srows = []
    for amp in [0.0, 0.1, 0.2, 0.4, 0.8]:
        for leap in [False, True]:
            p = weights(amp, leap)
            days = len(p)
            bb = rng.choice(days, size=(100000, n), p=p)
            a, t, pr, _ = stats(bb)
            srows.append({"amp": amp, "leap_day": leap, "max_over_min_day": round(float(p.max() / p[:365].min()), 2),
                          "P_same_exact": round(formula_weighted(n, p) * 100, 2),
                          "P_same_sim": round(float(a.mean()) * 100, 2),
                          "mean_same_pairs_sim": round(float(pr.mean()), 3),
                          "P_three_same_sim": round(float(t.mean()) * 100, 2)})
    season = pd.DataFrame(srows)
    season.to_csv(RES / "by_seasonality.csv", index=False)

    out = {"base_uniform_40": base, "company_50_groups": company,
           "company_without_counts": {int(k): int(v) for k, v in vc.items()},
           "by_group_size": bysize.to_dict("records"), "by_seasonality": season.to_dict("records"),
           "check": {"max_abs_diff_sim_formula_by_size": round(float((bysize.P_same_sim - bysize.P_same_formula).abs().max()), 2),
                     "max_abs_diff_sim_exact_seasonality": round(float((season.P_same_sim - season.P_same_exact).abs().max()), 2),
                     "rise_pt_at_1_5x": round(float(season[(season.amp == 0.2) & ~season.leap_day].P_same_exact.iloc[0] - season[(season.amp == 0) & ~season.leap_day].P_same_exact.iloc[0]), 2),
                     "leap_day_change_pt_by_amp": [round(float(a - b), 2) for a, b in zip(season[season.leap_day].P_same_exact, season[~season.leap_day].P_same_exact)]},
           "range_P_same_seasonality": [float(season.P_same_exact.min()), float(season.P_same_exact.max())]}
    json.dump(out, open(RES / "a981_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # data：最初の200グループの誕生日
    ex = b[:200]
    mm = pd.to_datetime("2025-01-01") + pd.to_timedelta(ex.ravel(), unit="D")
    pd.DataFrame({"group_id": np.repeat(np.arange(1, 201), n), "person": np.tile(np.arange(1, n + 1), 200),
                  "day_of_year": ex.ravel() + 1, "month": mm.month, "day": mm.day,
                  "group_has_same": np.repeat(any_pair[:200].astype(int), n)}).to_csv(DATA / "groups_example.csv", index=False)

    # 図1：人数ごとの確率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(bysize.people, bysize.P_same_formula, color=BLUE, lw=2, marker="o", ms=4, label="だれか2人が同じ誕生日（式）")
    ax.plot(bysize.people, bysize.P_within_1day_sim, color=GREEN, lw=1.5, marker="s", ms=3, label="だれか2人の誕生日が1日違い以内（乱数）")
    ax.plot(bysize.people, bysize.P_same_as_me_formula, color=ORANGE, lw=2, marker="o", ms=4, label="自分と同じ誕生日の人がいる（式）")
    ax.axvline(40, color=GRAY, lw=1, ls="--")
    ax.text(40.8, 3, "40人", color=GRAY, fontsize=9)
    ax.set_xlabel("グループの人数"); ax.set_ylabel("確率（%）"); ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=9, loc="center right")
    ax.set_title(f"40人なら、だれか2人が同じ誕生日は{base['P_any_same_formula']:.1f}%、自分と同じは{base['P_someone_same_as_me_formula']:.1f}%")
    save(fig, "a981_by_size.png", SRC)

    # 図2：40人のグループで、同じ誕生日の組の数
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    vals = pd.Series(pairs).value_counts().sort_index()
    vals = vals[vals.index <= 8] / len(pairs) * 100
    ax.bar(vals.index, vals.values, color=[GRAY] + [BLUE] * (len(vals) - 1))
    for x, v in zip(vals.index, vals.values):
        ax.text(x, v + .5, f"{v:.1f}%", ha="center", fontsize=8.5)
    ax.set_xlabel("40人の中で、同じ誕生日の2人の組の数（780組のうち）"); ax.set_ylabel("グループの割合（%）")
    ax.set_title(f"40人のグループ20万個：組の数の平均は{base['mean_same_pairs_sim']:.2f}組、0組は{base['share_pairs_0']:.1f}%")
    save(fig, "a981_pairs.png", SRC)

    # 図3：季節の偏り
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    s0 = season[~season.leap_day].reset_index(drop=True)
    lab = [f"{r.max_over_min_day:g}倍" + ("\n（偏りなし）" if r.amp == 0 else "") for _, r in s0.iterrows()]
    ax.plot(range(len(s0)), s0.P_same_exact, color=BLUE, marker="o", ms=7, lw=1.5)
    for i, v in enumerate(s0.P_same_exact):
        ax.text(i, v + .35, f"{v:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(range(len(s0))); ax.set_xticklabels(lab)
    ax.set_xlabel("いちばん多い日÷いちばん少ない日（季節の偏りの大きさ、作成者が置いた）")
    ax.set_ylabel("同じ誕生日の2人がいる確率（%）"); ax.set_ylim(85, 96)
    ax.set_title("季節の偏りを置くと、確率は少しだけ上がる（40人、式。縦軸は85%から）", pad=12)
    save(fig, "a981_seasonality.png", SRC, y=-0.07)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
