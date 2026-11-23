"""1121 敵の体力を1割増やすと、倒すのに要る回数はなぜ1割より大きく跳ねることがあるのか？（架空のデータ）

架空のゲームで、敵の体力を1,000から1,100（1割増し）にする。プレイヤーの1回のダメージは、攻撃力 D に乱数の振れ（±s の一様）と会心を掛けたもの。
倒すのに要る回数（体力が0以下になるまでの回数）が、1割増しでどれだけ増えるかを、攻撃力ごと・プレイヤーの集まり全体で数える。
振れがなければ回数は 体力÷D の切り上げで決まる（作りどおり）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1121
SRC = "架空のゲームの敵とプレイヤー（作成者が置いた体力・攻撃力・ダメージの振れからの乱数、seed 1121）"
HP0 = 1000.0
UPS = [0.05, 0.10, 0.20]
UP = 0.10
D_FIX = np.arange(50, 601)            # 振れなしで見る攻撃力（1きざみ）
D_RAND = np.arange(50, 601, 5)        # 振れありで見る攻撃力（5きざみ）
SPREAD = 0.10                         # 基本のダメージの振れ（±10%の一様）
N_FIGHT = 20000
SPREADS = [0.0, 0.05, 0.10, 0.20]
CRITS = [(0.0, 1.0), (0.1, 2.0)]      # 会心なし／1割で2倍
N_PLAYER = 5000                       # プレイヤーの集まり（攻撃力は中央値200・対数の標準偏差0.4）
P_MED, P_SIG = 200.0, 0.4
EXAMPLES = [200, 250, 300, 340, 400]


def r(x, d=3):
    return round(float(x), d)


def hits_fixed(hp, d):
    return np.ceil(hp / d - 1e-12)


def sim_hits(rng, hp_list, d, spread, crit, n):
    """同じ乱数のダメージの並びで、体力ごとに倒すのに要る回数を数える（体力の違いだけを比べるため）"""
    p, m = crit
    max_h = int(np.ceil(max(hp_list) / (d * (1 - spread)))) + 1
    dmg = d * rng.uniform(1 - spread, 1 + spread, (n, max_h))
    if p > 0:
        dmg = dmg * np.where(rng.random((n, max_h)) < p, m, 1.0)
    cum = np.cumsum(dmg, axis=1)
    return [(cum < hp).sum(axis=1) + 1 for hp in hp_list]


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    hp1 = HP0 * (1 + UP)

    # 1) 振れなし（作りどおり：切り上げ）
    h0 = hits_fixed(HP0, D_FIX)
    h1 = hits_fixed(hp1, D_FIX)
    ch = np.round((h1 / h0 - 1) * 100, 6)
    fix = pd.DataFrame({"attack": D_FIX, "hits_hp1000": h0.astype(int), "hits_hp1100": h1.astype(int),
                        "change_pct": np.round(ch, 2)})
    fix.to_csv(RES / "fixed_damage.csv", index=False)
    # 確かめ：振れ0の乱数の戦いでも、切り上げの回数と同じになるか
    chk_ok = 0
    rng_chk = np.random.default_rng([SEED, 1])
    for d in D_FIX:
        a, b = sim_hits(rng_chk, [HP0, hp1], float(d), 0.0, CRITS[0], 1)
        chk_ok += int(a[0] == h0[d - D_FIX[0]] and b[0] == h1[d - D_FIX[0]])
    band = fix.groupby("hits_hp1000").agg(attack_min=("attack", "min"), attack_max=("attack", "max"),
                                          n=("attack", "size"), share_up=("change_pct", lambda x: (x > 0).mean()),
                                          max_change_pct=("change_pct", "max")).reset_index()
    band["share_up"] = band.share_up.round(4)
    band.to_csv(RES / "fixed_by_hits.csv", index=False)

    # 2) 振れあり（基本 ±10%、会心なし）：攻撃力ごと
    rows = []
    for d in D_RAND:
        a, b = sim_hits(rng, [HP0, hp1], float(d), SPREAD, CRITS[0], N_FIGHT)
        n0 = int(hits_fixed(HP0, d))
        rows.append({"attack": int(d), "mean_hits_hp1000": r(a.mean(), 3), "mean_hits_hp1100": r(b.mean(), 3),
                     "mean_change_pct": r((b.mean() / a.mean() - 1) * 100, 2),
                     "fixed_change_pct": r((hits_fixed(hp1, d) / n0 - 1) * 100, 2),
                     "n_fixed": n0, "share_within_n_hp1000": r((a <= n0).mean(), 4), "share_within_n_hp1100": r((b <= n0).mean(), 4),
                     "share_more_hits": r((b > a).mean(), 4)})
    rnd = pd.DataFrame(rows)
    rnd.to_csv(RES / "random_damage.csv", index=False)

    # 例の攻撃力：回数の分布
    ex_rows = []
    for d in EXAMPLES:
        a, b = sim_hits(rng, [HP0, hp1], float(d), SPREAD, CRITS[0], N_FIGHT)
        for hp, arr in [(HP0, a), (hp1, b)]:
            vc = pd.Series(arr).value_counts(normalize=True).sort_index()
            for k, v in vc.items():
                ex_rows.append({"attack": d, "hp": hp, "hits": int(k), "share": r(v, 4)})
    exd = pd.DataFrame(ex_rows)
    exd.to_csv(DATA / "hits_distribution_examples.csv", index=False)

    # 3) プレイヤーの集まり（攻撃力がばらばら）
    pd_att = np.round(P_MED * np.exp(rng.normal(0, P_SIG, N_PLAYER)))
    pd_att = np.clip(pd_att, 30, None)
    pl_fix0, pl_fix1 = hits_fixed(HP0, pd_att), hits_fixed(hp1, pd_att)
    pl_rows = []
    for i, d in enumerate(pd_att):
        a, b = sim_hits(rng, [HP0, hp1], float(d), SPREAD, CRITS[0], 400)
        pl_rows.append((a.mean(), b.mean()))
    pl = np.array(pl_rows)
    players = pd.DataFrame({"player": np.arange(1, N_PLAYER + 1), "attack": pd_att.astype(int),
                            "hits_fixed_hp1000": pl_fix0.astype(int), "hits_fixed_hp1100": pl_fix1.astype(int),
                            "mean_hits_rand_hp1000": np.round(pl[:, 0], 3), "mean_hits_rand_hp1100": np.round(pl[:, 1], 3)})
    players.to_csv(DATA / "players.csv", index=False)
    pch_fix = (pl_fix1 / pl_fix0 - 1) * 100
    pch_rnd = (pl[:, 1] / pl[:, 0] - 1) * 100
    pop = {
        "n_players": N_PLAYER, "attack_median": r(np.median(pd_att), 1),
        "fixed_share_no_change": r((pch_fix == 0).mean(), 4),
        "fixed_share_up": r((pch_fix > 0).mean(), 4),
        "fixed_mean_change_pct": r(pch_fix.mean(), 2),
        "fixed_mean_change_if_up_pct": r(pch_fix[pch_fix > 0].mean(), 2),
        "fixed_max_change_pct": r(pch_fix.max(), 2),
        "fixed_total_hits_change_pct": r((pl_fix1.sum() / pl_fix0.sum() - 1) * 100, 2),
        "rand_mean_change_pct": r(pch_rnd.mean(), 2),
        "rand_p05_change_pct": r(np.percentile(pch_rnd, 5), 2),
        "rand_p95_change_pct": r(np.percentile(pch_rnd, 95), 2),
        "rand_share_over_15pct": r((pch_rnd > 15).mean(), 4),
    }

    # 4) 置き方を変えると：体力の増やし方3通り×振れ4通り×会心2通り（攻撃力 100〜500 の5きざみ）
    grid = []
    dg = np.arange(100, 501, 5)
    for up in UPS:
        hpu = HP0 * (1 + up)
        for sp in SPREADS:
            for crit in CRITS:
                chs = []
                for d in dg:
                    if sp == 0 and crit[0] == 0:
                        c = (hits_fixed(hpu, d) / hits_fixed(HP0, d) - 1) * 100
                    else:
                        a, b = sim_hits(rng, [HP0, hpu], float(d), sp, crit, 4000)
                        c = (b.mean() / a.mean() - 1) * 100
                    chs.append(c)
                chs = np.array(chs)
                grid.append({"hp_up": up, "spread": sp, "crit_p": crit[0], "crit_mult": crit[1],
                             "mean_change_pct": r(chs.mean(), 2), "max_change_pct": r(chs.max(), 2),
                             "min_change_pct": r(chs.min(), 2),
                             "share_over_1_5x_up": r((chs > 150 * up).mean(), 4),
                             "share_under_half_up": r((chs < 50 * up).mean(), 4)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    def at(d):
        return rnd[rnd.attack == d].iloc[0]

    out = {
        "settings": {"hp": HP0, "hp_up": UP, "attack_fixed_range": [int(D_FIX.min()), int(D_FIX.max())],
                     "attack_random_step": 5, "spread": SPREAD, "n_fight": N_FIGHT, "spreads": SPREADS,
                     "crits": CRITS, "ups": UPS, "player_attack_median": P_MED, "player_attack_logsd": P_SIG,
                     "n_player": N_PLAYER, "player_fights": 400, "grid_attack": [100, 500, 5], "grid_fights": 4000,
                     "seed": SEED},
        "fixed": {"share_no_change": r((ch == 0).mean(), 4), "share_up": r((ch > 0).mean(), 4),
                  "max_change_pct": r(ch.max(), 2), "mean_change_pct": r(ch.mean(), 2),
                  "min_positive_change_pct": r(ch[ch > 0].min(), 2), "share_over_10pct": r((ch > 10).mean(), 4),
                  "share_20pct_or_more": r((ch >= 20).mean(), 4),
                  "share_up_attack_200_600": r((ch[D_FIX >= 200] > 0).mean(), 4),
                  "mean_change_if_up_attack_200_600": r(ch[(D_FIX >= 200) & (ch > 0)].mean(), 2),
                  "by_hits": band.to_dict("records")},
        "random_base": {"mean_change_min": r(rnd.mean_change_pct.min(), 2), "mean_change_max": r(rnd.mean_change_pct.max(), 2),
                        "mean_change_mean": r(rnd.mean_change_pct.mean(), 2),
                        "examples": [at(d).to_dict() for d in EXAMPLES if d in set(rnd.attack)]},
        "population": pop,
        "check_spread0_sim_equal": f"{chk_ok}/{len(D_FIX)}",
        "grid": grid,
    }
    with open(RES / "a1121_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=float)

    # 図1：攻撃力ごとの回数の増え方（振れなし＝階段、振れ±10%）
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    ax.plot(fix.attack, fix.change_pct, color=GRAY, lw=1, drawstyle="steps-mid", label="ダメージが決まっているとき（切り上げ）")
    ax.plot(rnd.attack, rnd.mean_change_pct, color=BLUE, lw=2, label="ダメージが±10%振れるとき（回数の平均）")
    ax.axhline(10, color=INK, ls="--", lw=1)
    ax.text(603, 10, "体力の増え方\n（+10%）", fontsize=8, va="center")
    ax.set_xlim(50, 640)
    ax.set_ylim(0, 105)
    ax.set_xlabel("プレイヤーの1回のダメージ（攻撃力）")
    ax.set_ylabel("倒すのに要る回数の増え方（%）")
    ax.set_title("敵の体力1,000→1,100：回数は変わらないか、1回まるごと増えるか")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1121_by_attack.png", SRC)

    # 図2：例の攻撃力で、倒すのに要る回数の分布（振れ±10%）
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.8), sharey=True)
    for ax, d in zip(axes, [250, 300, 340]):
        sub = exd[exd.attack == d]
        hs = np.arange(sub.hits.min(), sub.hits.max() + 1)
        for j, (hp, col) in enumerate([(HP0, GRAY), (hp1, BLUE)]):
            s_ = sub[sub.hp == hp].set_index("hits").share.reindex(hs, fill_value=0)
            ax.bar(hs + (j - 0.5) * 0.38, s_.values * 100, width=0.38, color=col, label=f"体力{hp:,.0f}")
        ax.set_xticks(hs)
        ax.set_title(f"攻撃力{d}", fontsize=11)
        ax.set_xlabel("倒すのに要った回数")
        ax.set_ylim(0, 105)
    axes[0].set_ylabel("割合（%）")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("ダメージ±10%：1割増しで回数の分布がどう動くか", fontsize=12, y=1.03)
    save(fig, "a1121_examples.png", SRC)

    # 図3：置き方を変えると（攻撃力100〜500の回数の増え方の平均と最大）
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    sub = g[g.hp_up == UP]
    labels = [f"振れ±{int(s * 100)}%\n{'会心あり' if c > 0 else '会心なし'}" for s, c in zip(sub.spread, sub.crit_p)]
    x = np.arange(len(sub))
    ax.bar(x - 0.2, sub.mean_change_pct, width=0.4, color=GRAY, label="攻撃力100〜500での平均")
    ax.bar(x + 0.2, sub.max_change_pct, width=0.4, color=ORANGE, label="いちばん大きい増え方")
    for xx, v in zip(x, sub.max_change_pct):
        ax.text(xx + 0.2, v + 0.8, f"{v:g}", ha="center", fontsize=8)
    for xx, v in zip(x, sub.mean_change_pct):
        ax.text(xx - 0.2, v / 2, f"{v:g}", ha="center", va="center", fontsize=8, color="white")
    ax.axhline(10, color=INK, ls="--", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, max(sub.max_change_pct) * 1.15)
    ax.set_ylabel("倒すのに要る回数の増え方（%）")
    ax.set_title("体力+10%：振れが大きいほど、いちばん大きい増え方は小さくなる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1121_grid.png", SRC)

    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
