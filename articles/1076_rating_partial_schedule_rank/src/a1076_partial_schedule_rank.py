"""1076 総当たりでない対戦の記録から、順位はどこまで決められるのか？（架空のデータ）

架空の盤のゲームのリーグ（24人、引き分けなし）。作成者が1人ひとりの「本当の強さ」を置き、全員とは当たらない
対戦の組み方（でたらめに組む／2つの組の中で多く当たる）で1人あたり4〜12試合させる。順位を
①勝率 ②相手の強さも同時に見積もる方法 ③点数の付け方（勝つと上がり負けると下がる点数を試合の順に動かす）
の3つで決め、本当の強さの順位とどれだけ合うかを、総当たり（1回・2回）と比べて数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1076
SRC = "架空の盤のゲームのリーグ（作成者が乱数で作成、seed 1076）"
BASE = {"n": 24, "sd": 200.0, "gap": 200.0, "k": 32.0}
GAMES = [4, 8, 12, "rr1", "rr2"]
GLABEL = {4: "4試合", 8: "8試合", 12: "12試合", "rr1": "総当たり1回（23試合）", "rr2": "総当たり2回（46試合）"}
METHODS = [("wr", "勝率"), ("joint", "相手の強さも見積もる"), ("pts", "点数の付け方（順に動かす）")]
SCHED = [("random", "でたらめに組む"), ("group", "組の中で多く当たる")]


def pwin(d):
    """点の差 d（自分−相手）のときに勝つ確率。差400点で10対1"""
    return 1.0 / (1.0 + 10.0 ** (-d / 400.0))


def strengths(rng, n, sd, gap, sched):
    t = rng.normal(0, sd, n)
    if sched == "group":
        t[: n // 2] += gap / 2; t[n // 2:] -= gap / 2   # 組1（0〜11番）が強め、組2（12〜23番）が弱め
    return t


def schedule(rng, n, g, sched):
    """対戦の組（i, j）の並び（試合の順）。g は1人あたりの試合数または rr1・rr2"""
    if g in ("rr1", "rr2"):
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        pairs = pairs * (1 if g == "rr1" else 2)
        idx = rng.permutation(len(pairs))
        return np.array(pairs)[idx]
    out = []
    n_cross = max(1, int(round(g / 4))) if sched == "group" else g
    cross_rounds = set(rng.choice(g, n_cross, replace=False).tolist())
    half = n // 2
    for rd in range(g):
        if rd in cross_rounds:
            p = rng.permutation(n)
        else:
            p = np.concatenate([rng.permutation(half), half + rng.permutation(n - half)])
        out += list(zip(p[0::2], p[1::2]))
    return np.array(out)


def fit_joint(n, a, b, wa, iters=400):
    """相手の強さも同時に見積もる方法（勝つ確率＝強さの比。各人に平均の相手との1勝1敗を足して発散を防ぐ）"""
    W = np.zeros((n, n))
    np.add.at(W, (a, b), wa); np.add.at(W, (b, a), 1 - wa)
    N = W + W.T
    wins = W.sum(1) + 1.0
    p = np.ones(n)
    lp = np.zeros(n)
    for _ in range(iters):
        den = (N / (p[:, None] + p[None, :])).sum(1) + 2.0 / (p + 1.0)
        p = wins / den
        nl = np.log(p); nl -= nl.sum() / n
        p = np.exp(nl)
        if np.abs(nl - lp).max() < 1e-9:   # 動かなくなったら止める
            break
        lp = nl
    return 400 * np.log10(p)


def rank_of(x, rng):
    """大きいほど上。同点はくじ。1が最上位"""
    order = np.lexsort((rng.random(len(x)), -x))
    rk = np.empty(len(x), int); rk[order] = np.arange(1, len(x) + 1)
    return rk


def spearman_rank(r1, r2):
    return float(np.corrcoef(r1, r2)[0, 1])


def one(rng, n, sd, gap, k, g, sched):
    t = strengths(rng, n, sd, gap, sched)
    pr = schedule(rng, n, g, sched)
    a, b = pr[:, 0], pr[:, 1]
    wa = (rng.random(len(a)) < pwin(t[a] - t[b])).astype(float)
    games = np.bincount(a, minlength=n) + np.bincount(b, minlength=n)
    w = np.bincount(a, weights=wa, minlength=n) + np.bincount(b, weights=1 - wa, minlength=n)
    est = {"wr": w / np.maximum(games, 1), "joint": fit_joint(n, a, b, wa)}
    rt = np.zeros(n)
    for i, j, x in zip(a, b, wa):
        d = k * (x - pwin(rt[i] - rt[j])); rt[i] += d; rt[j] -= d
    est["pts"] = rt
    tr = rank_of(t, rng)
    res = {}
    for m, _ in METHODS:
        er = rank_of(est[m], rng)
        res[f"{m}_spearman"] = spearman_rank(er, tr)
        res[f"{m}_top1"] = float(er[tr == 1][0] == 1)
        res[f"{m}_top3"] = float(len(set(np.where(er <= 3)[0]) & set(np.where(tr <= 3)[0])) / 3)
        res[f"{m}_within2"] = float((np.abs(er - tr) <= 2).mean())
        res[f"{m}_mae"] = float(np.abs(er - tr).mean())
        if sched == "group":
            # 弱めの組（組2）の人が、強めの組（組1）の人より上に並べられた組み合わせのうち、本当は下だった割合
            g1, g2 = np.arange(n // 2), np.arange(n // 2, n)
            above = er[g2][:, None] < er[g1][None, :]
            wrong = above & (t[g2][:, None] < t[g1][None, :])
            res[f"{m}_g2_wrong_above"] = float(wrong.sum() / (n // 2) ** 2)
            res[f"{m}_g2_top6_share"] = float((er[g2] <= 6).sum() / 6)
    res["true_g2_top6_share"] = float((tr[n // 2:] <= 6).sum() / 6) if sched == "group" else np.nan
    return res, (t, pr, wa, est)


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    reps = 300
    rows = []
    example = None
    j = 0
    for s, slab in SCHED:
        for g in GAMES:
            acc = []
            for q in range(reps):
                res, ex = one(np.random.default_rng([SEED, j, q]), **BASE, g=g, sched=s)
                acc.append(res)
                if s == "group" and g == 8 and q == 0:
                    example = ex
            j += 1
            d = pd.DataFrame(acc).mean()
            for m, mlab in METHODS:
                row = {"schedule": slab, "games": GLABEL[g], "method": mlab,
                       "spearman": r(d[f"{m}_spearman"]), "top1_hit": r(d[f"{m}_top1"]), "top3_overlap": r(d[f"{m}_top3"]),
                       "within2": r(d[f"{m}_within2"]), "mean_abs_rank_error": r(d[f"{m}_mae"])}
                if s == "group":
                    row["g2_wrong_above"] = r(d[f"{m}_g2_wrong_above"]); row["g2_top6_share"] = r(d[f"{m}_g2_top6_share"])
                    row["true_g2_top6_share"] = r(d["true_g2_top6_share"])
                rows.append(row)
    tab = pd.DataFrame(rows); tab.to_csv(RES / "by_schedule_games_method.csv", index=False)

    # 1回分の例（組の中で多く当たる・8試合）
    t, pr, wa, est = example
    pd.DataFrame({"game_no": np.arange(1, len(pr) + 1), "player_a": pr[:, 0] + 1, "player_b": pr[:, 1] + 1,
                  "a_won": wa.astype(int)}).to_csv(DATA / "games_example.csv", index=False)
    pd.DataFrame({"player_id": np.arange(1, BASE["n"] + 1), "group": np.where(np.arange(BASE["n"]) < BASE["n"] // 2, 1, 2),
                  "true": t.round(1), "winrate": est["wr"].round(4), "joint_points": est["joint"].round(1),
                  "rating": est["pts"].round(1)}).to_csv(DATA / "players_example.csv", index=False)

    # 確かめ：強さの散らばり × 1人あたりの試合数 × 組の強さの差（組の中で多く当たる組み方、27通り×各80リーグ）
    grid = []
    for sd in [100.0, 200.0, 300.0]:
        for g in [4, 8, 12]:
            for gap in [0.0, 200.0, 400.0]:
                acc = [one(np.random.default_rng([SEED, 900, int(sd), g, int(gap), q]), n=BASE["n"], sd=sd, gap=gap,
                           k=BASE["k"], g=g, sched="group")[0] for q in range(80)]
                d = pd.DataFrame(acc).mean()
                grid.append({"sd": sd, "games": g, "gap": gap,
                             **{f"{m}_{x}": r(d[f"{m}_{x}"]) for m, _ in METHODS for x in ["spearman", "top1", "within2"]},
                             "wr_g2_wrong_above": r(d["wr_g2_wrong_above"]), "joint_g2_wrong_above": r(d["joint_g2_wrong_above"])})
    g = pd.DataFrame(grid); g.to_csv(RES / "grid.csv", index=False)

    def pick(s, gg, m, col):
        return float(tab[(tab.schedule == dict(SCHED)[s]) & (tab.games == GLABEL[gg]) & (tab.method == dict(METHODS)[m])][col].iloc[0])

    hl = {}
    for s, _ in SCHED:
        for gg in GAMES:
            for m, _ in METHODS:
                hl[f"{s}_{gg}_{m}_spearman"] = r(pick(s, gg, m, "spearman"), 3)
                hl[f"{s}_{gg}_{m}_top1_pct"] = r(pick(s, gg, m, "top1_hit") * 100, 2)
                hl[f"{s}_{gg}_{m}_within2_pct"] = r(pick(s, gg, m, "within2") * 100, 2)
    for gg in [4, 8, 12]:
        for m in ["wr", "joint"]:
            hl[f"group_{gg}_{m}_g2_wrong_above_pct"] = r(pick("group", gg, m, "g2_wrong_above") * 100, 2)
            hl[f"group_{gg}_{m}_g2_top6_pct"] = r(pick("group", gg, m, "g2_top6_share") * 100, 2)
    hl["group_true_g2_top6_pct"] = r(pick("group", 8, "wr", "true_g2_top6_share") * 100, 2)
    hl["win_prob_diff_200"] = r(pwin(200)); hl["win_prob_diff_100"] = r(pwin(100))
    gs = {"n": int(len(g))}
    for m, _ in METHODS:
        for x in ["spearman", "top1", "within2"]:
            gs[f"{m}_{x}_min"] = r(g[f"{m}_{x}"].min()); gs[f"{m}_{x}_max"] = r(g[f"{m}_{x}"].max())
    gs["joint_beats_wr_spearman_count"] = int((g.joint_spearman > g.wr_spearman).sum())
    gs["gap0_joint_minus_wr_min"] = r((g.joint_spearman - g.wr_spearman)[g.gap == 0].min())
    gs["gap0_joint_minus_wr_max"] = r((g.joint_spearman - g.wr_spearman)[g.gap == 0].max())
    gs["gap400_joint_minus_wr_min"] = r((g.joint_spearman - g.wr_spearman)[g.gap == 400].min())
    gs["gap400_joint_minus_wr_max"] = r((g.joint_spearman - g.wr_spearman)[g.gap == 400].max())
    gs["wr_wrong_min"] = r(g.wr_g2_wrong_above.min()); gs["wr_wrong_max"] = r(g.wr_g2_wrong_above.max())
    gs["joint_wrong_min"] = r(g.joint_g2_wrong_above.min()); gs["joint_wrong_max"] = r(g.joint_g2_wrong_above.max())
    out = {"base_setting": BASE, "reps": reps,
           "group_schedule": "2つの組（各12人）。1人あたり g 試合のうち round(g/4) 回（最低1回）は全員からでたらめに相手を決め、残りは組の中で決める",
           "headline": hl, "table": tab.to_dict("records"), "grid_summary": gs}
    json.dump(out, open(RES / "a1076_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：試合数ごとの順位相関（2つの組み方 × 3つの決め方）
    cl = {"wr": GRAY, "joint": BLUE, "pts": ORANGE}
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0), sharey=True)
    xs = np.arange(len(GAMES))
    for ax, (s, slab) in zip(axes, SCHED):
        for m, mlab in METHODS:
            v = [pick(s, gg, m, "spearman") for gg in GAMES]
            ax.plot(xs, v, marker="o", color=cl[m], label=mlab)
        ax.set_xticks(xs); ax.set_xticklabels(["4", "8", "12", "総当たり\n1回", "総当たり\n2回"])
        ax.set_ylim(0, 1); ax.set_title(slab, fontsize=11); ax.set_xlabel("1人あたりの試合数")
    axes[0].set_ylabel("本当の順位との順位相関（300リーグの平均）")
    axes[1].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle("組の中で多く当たると、勝率の順位は本当の順位から離れる", fontsize=13, y=1.02)
    save(fig, "a1076_spearman.png", SRC, y=-0.07)

    # 図2：1位を当てる割合（棒、0始まり）
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    wd = 0.26
    for i, (m, mlab) in enumerate(METHODS):
        v = [pick("group", gg, m, "top1_hit") * 100 for gg in GAMES]
        bars = ax.bar(xs + (i - 1) * wd, v, wd, color=cl[m], label=mlab)
        for bb in bars:
            ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 1, f"{bb.get_height():.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(xs); ax.set_xticklabels([GLABEL[x].replace("（", "\n（") for x in GAMES], fontsize=8.5)
    ax.set_ylim(0, 100); ax.set_ylabel("本当の1位を1位にした割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title(f"組の中で多く当たる組み方：1位を当てる割合（総当たり2回でも{pick('group', 'rr2', 'wr', 'top1_hit')*100:.1f}%）")
    save(fig, "a1076_top1.png", SRC)

    # 図3：例（8試合）本当の強さと勝率・見積もった強さ
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
    grp = np.arange(BASE["n"]) < BASE["n"] // 2
    for ax, key, lab in [(axes[0], "wr", "勝率"), (axes[1], "joint", "相手の強さも見積もった強さ")]:
        y = est[key] * (100 if key == "wr" else 1)
        ax.scatter(t[grp], y[grp], color=BLUE, s=28, label="組1（強め）")
        ax.scatter(t[~grp], y[~grp], color=ORANGE, s=28, marker="s", label="組2（弱め）")
        ax.set_xlabel("本当の強さ（平均0）"); ax.set_ylabel("勝率（%）" if key == "wr" else "見積もった強さ（点）")
        if key == "wr":
            ax.set_ylim(0, 100)
        ax.set_title(lab, fontsize=11)
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("1回分の例（組の中で多く当たる・1人8試合）：弱めの組の人も、勝率では上のほうに並ぶ", fontsize=12, y=1.02)
    save(fig, "a1076_example.png", SRC)

    print(json.dumps(hl, ensure_ascii=False, indent=0)); print(json.dumps(gs, ensure_ascii=False, indent=0))
    print(tab.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
