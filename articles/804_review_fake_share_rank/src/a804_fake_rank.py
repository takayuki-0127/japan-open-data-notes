"""804 サクラの投稿を何%混ぜると、順位は何位上がるのか？（架空のデータ）

架空の同じジャンルの店300軒。店ごとに本当の満足度を置き、本物の口コミを引く。
真ん中くらいの店（本当の満足度3.9）を1軒「対象の店」とし、星5のサクラの投稿を、口コミ全体に占める割合で
0〜30%混ぜたとき、300軒の中の順位が何位上がるかを数える。並べ方は「星の平均そのまま」と「件数で寄せる平均（m=10）」。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 804
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 804）"
rng = np.random.default_rng(SEED)
N_SHOP, REPS = 300, 200
STARS = np.arange(1, 6)
TARGET_MU = 3.9
SHARES = [0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 40, 50]  # サクラの割合（%）


def star_probs(mu, width=0.9):
    """平均が mu になる1〜5の山形の分布"""
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / width) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def make_others(rng, n=N_SHOP - 1, spread=0.35):
    true = np.clip(rng.normal(3.9, spread, n), 2.5, 4.8)
    n_rev = np.round(np.exp(rng.uniform(np.log(3), np.log(500), n))).astype(int)
    cnt = np.array([rng.multinomial(k, p) for k, p in zip(n_rev, star_probs(true))])
    return true, n_rev, cnt


def scores(cnt, m=None):
    n = cnt.sum(1)
    mean = (cnt * STARS).sum(1) / n
    if m is None:
        return mean
    c = (cnt * STARS).sum() / n.sum()
    return (mean * n + c * m) / (n + m)


def rank_of_target(cnt_all, m):
    s = scores(cnt_all, m)
    return int(1 + (s[1:] > s[0]).sum())  # 0番目が対象の店。同点は対象の店に有利に数える


def fake_counts(n_real, share, kind):
    k = int(round(n_real * share / (100 - share))) if share > 0 else 0
    if kind == "星5だけ":
        return np.array([0, 0, 0, 0, k])
    return np.array([0, 0, 0, k - k // 2, k // 2])  # 星4と星5を半分ずつ


def run(n_real, kind="星5だけ", spread=0.35, seed_off=0):
    """REPS 回、ほかの店と対象の店の本物の口コミを作り直し、サクラの割合ごとの順位を数える"""
    rows = []
    for r in range(REPS):
        g = np.random.default_rng(SEED * 1000 + seed_off + r)
        true, n_rev, cnt = make_others(g, spread=spread)
        real = g.multinomial(n_real, star_probs(np.array([TARGET_MU]))[0])
        true_rank = int(1 + (true > TARGET_MU).sum())
        for sh in SHARES:
            t = real + fake_counts(n_real, sh, kind)
            allc = np.vstack([t, cnt])
            rows.append({"rep": r, "share": sh, "true_rank": true_rank,
                         "rank_raw": rank_of_target(allc, None), "rank_m10": rank_of_target(allc, 10),
                         "target_mean": float((t * STARS).sum() / t.sum())})
    return pd.DataFrame(rows)


def summ(df):
    g = df.groupby("share")
    out = pd.DataFrame({"rank_raw": g.rank_raw.median(), "rank_m10": g.rank_m10.median(),
                         "target_mean": g.target_mean.mean().round(3),
                         "top10_raw": g.rank_raw.apply(lambda x: (x <= 10).mean()).round(3),
                         "top10_m10": g.rank_m10.apply(lambda x: (x <= 10).mean()).round(3)})
    out.insert(1, "gain_raw", out.rank_raw.iloc[0] - out.rank_raw)
    out.insert(3, "gain_m10", out.rank_m10.iloc[0] - out.rank_m10)
    return out


def main():
    # 1回分の店（data）
    true, n_rev, cnt = make_others(rng)
    real = rng.multinomial(100, star_probs(np.array([TARGET_MU]))[0])
    d = pd.DataFrame(np.vstack([real, cnt]), columns=[f"cnt{s}" for s in STARS])
    d.insert(0, "true", np.r_[TARGET_MU, true]); d.insert(0, "is_target", [1] + [0] * len(true))
    d.insert(0, "shop_id", np.arange(1, N_SHOP + 1))
    d.to_csv(DATA / "shops.csv", index=False, float_format="%.4f")

    # 2) 基本：対象の店の本物の口コミ100件、サクラは星5だけ
    base_df = run(100)
    base = summ(base_df)
    base.to_csv(RES / "rank_by_share_n100.csv")
    true_rank_med = float(base_df.true_rank.median())

    # 3) 対象の店の件数を変える
    by_n = {}
    for n in [20, 100, 500]:
        s = base if n == 100 else summ(run(n, seed_off=n))
        by_n[str(n)] = s[["rank_raw", "rank_m10"]].T.to_dict()
    # 4) 確かめ：サクラを星4と星5の半分ずつにする／店どうしの差を変える
    sens = {}
    for name, kw in [("星4と星5を半分ずつ", {"kind": "星4と星5を半分ずつ"}),
                     ("店どうしの差0.2", {"spread": 0.2}), ("店どうしの差0.5", {"spread": 0.5})]:
        s = summ(run(100, seed_off=7, **kw))
        sens[name] = {str(sh): {"rank_raw": float(s.loc[sh, "rank_raw"]), "rank_m10": float(s.loc[sh, "rank_m10"])}
                      for sh in [0, 5, 10, 20, 30]}
    rows = []
    for name, v in sens.items():
        for sh, x in v.items():
            rows.append({"scenario": name, "share": int(sh), **x})
    pd.DataFrame(rows).to_csv(RES / "robustness.csv", index=False)

    # 1回分の店（data/shops.csv）での対象の店の平均と順位（星の平均そのまま）
    s0 = scores(np.vstack([real, cnt]))
    one = {}
    for sh in [0, 10, 20]:
        t = real + fake_counts(100, sh, "星5だけ")
        v = float((t * STARS).sum() / t.sum())
        one[str(sh)] = {"fakes": int(t.sum() - real.sum()), "mean": round(v, 3), "rank_raw": int(1 + (s0[1:] > v).sum())}

    out = {"n_shops": N_SHOP, "reps": REPS, "target_true_mu": TARGET_MU, "target_true_rank_median": true_rank_med,
           "base_n100_star5": {str(k): v for k, v in base.T.to_dict().items()},
           "by_target_n": by_n, "robustness": sens, "one_draw_n100": one}
    json.dump(out, open(RES / "a804_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：サクラの割合と順位（基本）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(base.index, base.rank_raw, "o-", color=ORANGE, label="星の平均そのまま")
    ax.plot(base.index, base.rank_m10, "o-", color=BLUE, label="件数で寄せる（m=10）")
    for sh in [10, 20, 30]:
        ax.text(sh + 0.8, base.loc[sh, "rank_raw"] + 7, f"{base.loc[sh, 'rank_raw']:.0f}位", color=ORANGE, fontsize=9)
    ax.invert_yaxis(); ax.set_xlabel("口コミ全体に占めるサクラ（星5）の割合（%）"); ax.set_ylabel("300軒の中の順位（中央値）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("真ん中くらいの店（本物の口コミ100件）に、星5のサクラを混ぜると")
    save(fig, "a804_rank.png", SRC)

    # 図2：対象の店の件数ごと（星の平均そのまま）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for n, col in [("20", LIGHT), ("100", ORANGE), ("500", INK)]:
        v = by_n[n]
        ax.plot(SHARES, [v[sh]["rank_raw"] for sh in SHARES], "o-", color=col, label=f"本物の口コミ{n}件")
    ax.invert_yaxis(); ax.set_xlabel("口コミ全体に占めるサクラ（星5）の割合（%）"); ax.set_ylabel("300軒の中の順位（中央値）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("同じ割合なら、件数が多い店でも順位の上がり方はほぼ同じ（星の平均そのまま）")
    save(fig, "a804_by_n.png", SRC)

    # 図3：1回分の店の星の平均と、対象の店の位置
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.hist(s0[1:], bins=np.linspace(2.0, 5.0, 61), color=GRAY, alpha=.8)
    for sh, col in [(0, BLUE), (10, ORANGE), (20, GREEN)]:
        v, rk = one[str(sh)]["mean"], one[str(sh)]["rank_raw"]
        ax.axvline(v, color=col, lw=2)
        ax.text(4.42, ax.get_ylim()[1] * (0.92 - sh / 100 * 1.2), f"サクラ{sh}%：平均{v:.2f}・{rk}位", color=col,
                fontsize=9.5)
    ax.set_xlim(2.5, 5.05); ax.set_xlabel("星の平均（ほかの店299軒は灰色の山、縦の線が対象の店）"); ax.set_ylabel("店の数")
    ax.set_title("真ん中には店が固まっているので、平均が少し上がるだけで多くの店を抜く（1回分）")
    save(fig, "a804_hist.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
