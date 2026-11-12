"""495 会員ランクを「暦年」と「直近12か月」で判定すると、何人のランクが変わるのか（実務の型）

架空の会員2万人の月ごとの購入額（2024〜2025年）から、2つの決め方でランクを出して比べる。
  暦年：前の年（1〜12月）の購入額で、その年の1年間のランクを決める
  直近12か月：毎月1日に、前の月までの12か月の購入額でランクを決め直す
ランクは ゴールド（10万円以上）・シルバー（3万円以上）・ブロンズ（それ未満）。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 495
N = 20_000
MONTHS = pd.period_range("2024-01", "2025-12", freq="M")
CUT = [(100_000, "ゴールド"), (30_000, "シルバー"), (0, "ブロンズ")]
ORD = {"ブロンズ": 0, "シルバー": 1, "ゴールド": 2}


def rank(x):
    return np.where(x >= CUT[0][0], "ゴールド", np.where(x >= CUT[1][0], "シルバー", "ブロンズ"))


def make_spend(rng, n, trend_sd=0.35):
    base = rng.gamma(0.9, 3_300, n)                             # 会員ごとの月の平均購入額（ばらつき大）
    trend = np.exp(rng.normal(0, trend_sd, n))                  # 2年で何倍になるか（増える人・減る人）
    season = np.array([0.9, 0.8, 1.0, 1.0, 1.0, 0.95, 1.1, 1.0, 0.9, 0.95, 1.05, 1.45])
    start = rng.integers(0, 24, n) * (rng.random(n) < 0.15)      # 15%は途中から入会
    stop = np.where(rng.random(n) < 0.12, rng.integers(1, 24, n), 99)   # 12%は途中で来なくなる
    rows = []
    sp = np.zeros((n, len(MONTHS)))
    for t, m in enumerate(MONTHS):
        mu = base * trend ** (t / 23) * season[m.month - 1]
        buy = rng.random(n) < np.clip(0.55 + 0.1 * np.log1p(base / 3000), 0.2, 0.95)
        amt = np.where(buy, rng.gamma(2.0, mu / 2.0 / np.maximum(0.2, buy.mean())), 0.0)
        amt[(t < start) | (t >= stop)] = 0
        sp[:, t] = np.round(amt, -1)
    return sp


def main():
    rng = np.random.default_rng(SEED)
    sp = make_spend(rng, N)
    df = pd.DataFrame(sp, columns=[str(m) for m in MONTHS]); df.insert(0, "member", np.arange(1, N + 1))
    df.to_csv(DATA / "fictional_monthly_spend.csv", index=False)

    y2024 = sp[:, :12].sum(1)
    rank_cal = rank(y2024)                                       # 2025年の1年間のランク（暦年）
    months25 = MONTHS[12:]
    roll = np.stack([sp[:, t - 12:t].sum(1) for t in range(12, 24)], axis=1)   # 2025年各月1日の直近12か月
    rank_roll = np.stack([rank(roll[:, k]) for k in range(12)], axis=1)
    o_cal = np.vectorize(ORD.get)(rank_cal); o_roll = np.vectorize(ORD.get)(rank_roll)

    # SQL（DuckDB）でも直近12か月の判定を出し、Python と一致することを確かめる
    long = df.melt(id_vars="member", var_name="ym", value_name="amount")
    con = duckdb.connect(); con.register("s", long)
    q = """WITH m AS (SELECT member, CAST(ym || '-01' AS DATE) d, amount FROM s),
           w AS (SELECT member, d, SUM(amount) OVER (PARTITION BY member ORDER BY d
                    RANGE BETWEEN INTERVAL 12 MONTH PRECEDING AND INTERVAL 1 MONTH PRECEDING) r12 FROM m)
           SELECT member, d, r12 FROM w WHERE d >= DATE '2025-01-01' ORDER BY member, d"""
    chk = con.execute(q).df()
    assert np.allclose(chk.r12.values.reshape(N, 12), roll)

    diff = o_roll != o_cal[:, None]
    up = o_roll > o_cal[:, None]; down = o_roll < o_cal[:, None]
    by_month = pd.DataFrame({"month": [str(m) for m in months25], "differ": diff.mean(0), "roll_higher": up.mean(0),
                             "roll_lower": down.mean(0)})
    by_month.to_csv(RES / "monthly_differ.csv", index=False)
    changes = (o_roll[:, 1:] != o_roll[:, :-1]).sum(1)          # 2025年の中で、直近12か月のランクが変わった回数
    active = (sp.sum(1) > 0)
    ch_dist = pd.Series(changes[active]).value_counts().sort_index()
    ch_dist.to_csv(RES / "rank_changes_per_member.csv", header=["members"])

    # 入れ替わりの表（2025年12月1日時点：暦年 → 直近12か月）
    tr = pd.crosstab(pd.Series(rank_cal, name="暦年（2024年の購入額）"), pd.Series(rank_roll[:, -1], name="直近12か月（2024/12〜2025/11）"))
    tr = tr.loc[["ゴールド", "シルバー", "ブロンズ"], ["ゴールド", "シルバー", "ブロンズ"]]
    tr.to_csv(RES / "transition_dec2025.csv")
    # 年の途中で、暦年ではシルバー以上なのに、直近12か月ではブロンズの人
    res = {"members": N, "share_cal": {k: float((rank_cal == k).mean()) for k in ORD},
           "share_roll_dec": {k: float((rank_roll[:, -1] == k).mean()) for k in ORD},
           "differ_mean": float(diff.mean()), "differ_min": float(diff.mean(0).min()), "differ_max": float(diff.mean(0).max()),
           "differ_dec": float(diff[:, -1].mean()), "roll_higher_dec": float(up[:, -1].mean()), "roll_lower_dec": float(down[:, -1].mean()),
           "ever_differ_2025": float(diff.any(1).mean()),
           "changes_ge1_share_active": float((changes[active] >= 1).mean()), "changes_ge2_share_active": float((changes[active] >= 2).mean()),
           "changes_mean_active": float(changes[active].mean()),
           "gold_cal": int((rank_cal == "ゴールド").sum()), "gold_roll_dec": int((rank_roll[:, -1] == "ゴールド").sum())}
    # トレンドを変えたとき（伸び縮みのばらつき）
    sweep = []
    for tsd in [0.0, 0.15, 0.35, 0.6]:
        r2 = np.random.default_rng(SEED + int(tsd * 100))
        s2 = make_spend(r2, 8_000, trend_sd=tsd)
        rc = np.vectorize(ORD.get)(rank(s2[:, :12].sum(1)))
        rr = np.stack([np.vectorize(ORD.get)(rank(s2[:, t - 12:t].sum(1))) for t in range(12, 24)], axis=1)
        act = s2.sum(1) > 0
        sweep.append({"trend_sd": tsd, "differ_mean": float((rr != rc[:, None]).mean()),
                      "differ_dec": float((rr[:, -1] != rc).mean()),
                      "changes_ge1_active": float(((rr[:, 1:] != rr[:, :-1]).sum(1)[act] >= 1).mean())})
    res["sweep_trend"] = sweep
    pd.DataFrame(sweep).to_csv(RES / "sweep_trend.csv", index=False)
    json.dump(res, open(RES / "a495_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：月ごとの、ランクが違う会員の割合
    fig, ax = plt.subplots(figsize=(8.4, 4.1))
    x = np.arange(12)
    ax.bar(x, by_month.roll_higher * 100, color=BLUE, label="直近12か月のほうが上")
    ax.bar(x, by_month.roll_lower * 100, bottom=by_month.roll_higher * 100, color=ORANGE, label="直近12か月のほうが下")
    for xi, v in zip(x, by_month.differ): ax.text(xi, v * 100 + 0.5, f"{v*100:.1f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x, [f"{m.month}月" for m in months25]); ax.set_ylabel("2つの決め方でランクが違う会員（%）")
    ax.set_ylim(0, by_month.differ.max() * 100 * 1.25); ax.legend(fontsize=9, frameon=False, loc="upper left")
    ax.set_title("2025年の各月1日に、暦年のランクと直近12か月のランクが違う会員")
    save(fig, "a495_monthly.png", "架空の会員2万人（seed 495）で作成。ランクは年10万円以上ゴールド、3万円以上シルバー")

    # 図2：12月の入れ替わり表
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    v = tr.values
    ax.imshow(v / v.sum(1, keepdims=True), cmap="Blues", vmin=0, vmax=1)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{v[i,j]:,}人\n（{v[i,j]/v[i].sum()*100:.0f}%）", ha="center", va="center", fontsize=10,
                    color="white" if v[i, j] / v[i].sum() > 0.6 else INK)
    ax.set_xticks(range(3), tr.columns); ax.set_yticks(range(3), tr.index)
    ax.set_xlabel("直近12か月のランク（2025年12月1日）"); ax.set_ylabel("暦年のランク（2025年の1年間）")
    ax.set_title("同じ会員の、2つのランク（行ごとの割合）", fontsize=11.5)
    for s in ax.spines.values(): s.set_visible(False)
    save(fig, "a495_transition.png", "架空の会員2万人（seed 495）で作成")

    # 図3：直近12か月の決め方で、1年に何回ランクが変わるか
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.bar(ch_dist.index, ch_dist.values / active.sum() * 100, color=GREEN)
    for xi, vv in zip(ch_dist.index, ch_dist.values): ax.text(xi, vv / active.sum() * 100 + 0.8, f"{vv/active.sum()*100:.1f}%", ha="center", fontsize=9)
    ax.set_xlabel("2025年の中で、直近12か月のランクが変わった回数"); ax.set_ylabel("会員の割合（%）")
    ax.set_xticks(ch_dist.index)
    ax.set_title("直近12か月で決めると、年の途中でランクが何回変わるか（暦年なら0回）")
    save(fig, "a495_changes.png", "架空の会員（購入のある人、seed 495）で作成")
    print(json.dumps(res, ensure_ascii=False, indent=0)[:2000])
    print(by_month.round(3).to_string()); print(tr); print(ch_dist)


if __name__ == "__main__":
    main()
