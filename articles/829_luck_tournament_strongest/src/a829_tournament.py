"""829 トーナメントで、いちばん強いチームが優勝する確率は？（架空のデータ）

架空のリーグの16チーム。チームごとに「本当の強さ」を作成者が置く（平均0・標準偏差0.6の正規分布）。
1試合の勝ち負けは、強さの差 d から 1/(1+exp(-d)) の確率で決まる（引き分けなし、ホームの有利なし）。
大会の形（1発勝負のトーナメント・何試合かで勝ち抜け・総当たり）ごとに、本当にいちばん強いチームが優勝する確率を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import comb
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 829
SRC = "架空のリーグと大会（作成者が乱数で作成、seed 829）"
rng = np.random.default_rng(SEED)
N_TEAM = 16
SPREAD = 0.6
REPS = 20000


def p_win(d):
    return 1 / (1 + np.exp(-d))


def p_series(p, k):
    """1試合の勝つ確率 p で、k 試合のうち過半数を先に取る確率"""
    need = k // 2 + 1
    return sum(comb(k, w) * p ** w * (1 - p) ** (k - w) for w in range(need, k + 1))


def seed_order(n):
    """強い順1〜n の、よくあるシードの並び（1位と2位は決勝まで当たらない）"""
    o = [1]
    while len(o) < n:
        m = len(o) * 2
        o = [x for s in o for x in (s, m + 1 - s)]
    return np.array(o) - 1


def knockout(rng, S, order, k=1):
    """S: (回数, チーム数) の強さ。order: (回数, チーム数) の組み合わせ順。勝ち残ったチームの列番号を返す"""
    idx = order.copy()
    rows = np.arange(S.shape[0])[:, None]
    while idx.shape[1] > 1:
        a, b = idx[:, 0::2], idx[:, 1::2]
        p = p_series(p_win(S[rows, a] - S[rows, b]), k)
        idx = np.where(rng.random(p.shape) < p, a, b)
    return idx[:, 0]


def round_robin(rng, S, g=1):
    """総当たり（各組 g 試合）。勝ち数の最も多いチーム（同じならくじ）"""
    n = S.shape[1]
    i, j = np.triu_indices(n, 1)
    p = p_win(S[:, i] - S[:, j])
    w = rng.binomial(g, p)
    wins = np.zeros_like(S)
    np.add.at(wins.T, i, w.T)
    np.add.at(wins.T, j, (g - w).T)
    return np.argmax(wins + rng.random(wins.shape) * 0.5, 1)


def run(rng, n_team, spread, reps, fmt):
    S = rng.normal(0, spread, (reps, n_team))
    best = S.argmax(1)
    if fmt == "ko1":
        champ = knockout(rng, S, rng.permuted(np.tile(np.arange(n_team), (reps, 1)), axis=1), 1)
    elif fmt == "ko1_seeded":
        rank = np.argsort(-S, 1)  # rank[:, r] = r 番目に強いチームの列
        champ = knockout(rng, S, rank[:, seed_order(n_team)], 1)
    elif fmt in ("ko3", "ko5", "ko7"):
        champ = knockout(rng, S, rng.permuted(np.tile(np.arange(n_team), (reps, 1)), axis=1), int(fmt[2]))
    elif fmt.startswith("rr"):
        champ = round_robin(rng, S, int(fmt[2]))
    true_rank = (S > S[np.arange(reps), champ][:, None]).sum(1) + 1
    return S, best, champ, true_rank


FMTS = [("ko1", "1発勝負のトーナメント（組み合わせはくじ）"),
        ("ko1_seeded", "1発勝負のトーナメント（本当の強さの順にシード）"),
        ("ko3", "3試合で2勝した方が勝ち抜け（くじ）"),
        ("ko7", "7試合で4勝した方が勝ち抜け（くじ）"),
        ("rr1", "総当たり 各組1試合（15試合）"),
        ("rr2", "総当たり 各組2試合（30試合）"),
        ("rr4", "総当たり 各組4試合（60試合）")]


def main():
    # 0) 1回分のリーグ（data/teams.csv）
    s0 = np.sort(rng.normal(0, SPREAD, N_TEAM))[::-1]
    team = [chr(ord("A") + i) for i in range(N_TEAM)]
    S0 = np.tile(s0, (REPS, 1))
    ch_ko = knockout(rng, S0, rng.permuted(np.tile(np.arange(N_TEAM), (REPS, 1)), axis=1), 1)
    ch_rr = round_robin(rng, S0, 2)
    teams = pd.DataFrame({"team": team, "true_rank": np.arange(1, N_TEAM + 1), "strength": s0.round(4),
                          "p_beat_avg_team": p_win(s0).round(4),
                          "p_champion_ko1": (np.bincount(ch_ko, minlength=N_TEAM) / REPS).round(4),
                          "p_champion_rr2": (np.bincount(ch_rr, minlength=N_TEAM) / REPS).round(4)})
    teams.to_csv(DATA / "teams.csv", index=False)

    # 1) 大会の形ごと（リーグを作り直して2万回）
    rows, rank_dist, gap = [], None, {}
    for f, label in FMTS:
        S, best, champ, tr = run(np.random.default_rng(SEED * 10 + len(rows)), N_TEAM, SPREAD, REPS, f)
        rows.append({"format": f, "label": label, "p_strongest_wins": round(float((champ == best).mean()), 4),
                     "p_top2_wins": round(float((tr <= 2).mean()), 4),
                     "p_top4_wins": round(float((tr <= 4).mean()), 4),
                     "mean_true_rank": round(float(tr.mean()), 2)})
        if f == "ko1":
            rank_dist = {int(r): round(float((tr == r).mean()), 4) for r in range(1, N_TEAM + 1)}
            srt = np.sort(S, 1)
            g = srt[:, -1] - srt[:, -2]
            hit = champ == best
            for lo, hi in [(0, 0.1), (0.1, 0.25), (0.25, 0.5), (0.5, 9)]:
                m = (g >= lo) & (g < hi)
                gap[f"{lo}-{hi}"] = {"share_of_leagues": round(float(m.mean()), 3), "p_strongest_wins": round(float(hit[m].mean()), 3)}
            p_top_vs_others = p_win(srt[:, -1][:, None] - srt[:, :-1]).mean()
            p_top_vs_second = p_win(g).mean()
    fm = pd.DataFrame(rows)
    fm.to_csv(RES / "by_format.csv", index=False)

    # 2) 確かめ：チームどうしの差の大きさ・チームの数を変える
    sens = []
    for sp in [0.2, 0.4, 0.6, 0.8, 1.0, 1.5]:
        for nt in [8, 16, 32]:
            for f in ["ko1", "ko7", "rr2"]:
                S, best, champ, tr = run(np.random.default_rng(SEED * 100 + int(sp * 10) * 7 + nt + len(f) + ord(f[2])),
                                         nt, sp, 10000, f)
                srt = np.sort(S, 1)
                sens.append({"spread": sp, "teams": nt, "format": f, "p_strongest_wins": round(float((champ == best).mean()), 4),
                             "p_top_beats_others_1game": round(float(p_win(srt[:, -1][:, None] - srt[:, :-1]).mean()), 3)})
    sv = pd.DataFrame(sens)
    sv.to_csv(RES / "sensitivity.csv", index=False)

    base_ko1 = sv[(sv.teams == 16) & (sv.format == "ko1")]
    out = {"teams": N_TEAM, "spread": SPREAD, "reps": REPS,
           "p_top_beats_others_1game": round(float(p_top_vs_others), 3),
           "p_top_beats_second_1game": round(float(p_top_vs_second), 3),
           "by_format": rows, "ko1_champion_true_rank": rank_dist,
           "ko1_by_gap_top1_top2": gap,
           "ko1_16teams_by_spread": base_ko1[["spread", "p_strongest_wins", "p_top_beats_others_1game"]].to_dict("records"),
           "one_league": {"top_team_strength": round(float(s0[0]), 3),
                          "top_team_p_champion_ko1": float(teams.p_champion_ko1[0]),
                          "top_team_p_champion_rr2": float(teams.p_champion_rr2[0]),
                          "teams_with_ge_1pct_ko1": int((teams.p_champion_ko1 >= 0.01).sum())},
           "sensitivity_range_all": {"min": float(sv.p_strongest_wins.min()), "max": float(sv.p_strongest_wins.max())}}
    json.dump(out, open(RES / "a829_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1発勝負のトーナメントで、優勝したチームの本当の強さの順位
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    r = np.arange(1, N_TEAM + 1)
    v = np.array([rank_dist[i] for i in r]) * 100
    ax.bar(r, v, color=[ORANGE] + [BLUE] * (N_TEAM - 1))
    for i, x in zip(r[:6], v[:6]):
        ax.text(i, x + 0.6, f"{x:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(r); ax.set_xlabel("優勝したチームの、本当の強さの順位（1＝いちばん強い）")
    ax.set_ylabel("割合（%）")
    ax.set_title(f"1発勝負の16チームのトーナメントで、いちばん強いチームの優勝は{v[0]:.0f}%")
    save(fig, "a829_champion_rank.png", SRC)

    # 図2：大会の形ごとの、いちばん強いチームが優勝する確率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    col = [ORANGE, LIGHT, BLUE, BLUE, GREEN, GREEN, GREEN]
    ax.barh(fm.label[::-1], fm.p_strongest_wins[::-1] * 100, color=col[::-1])
    for i, x in enumerate(fm.p_strongest_wins[::-1] * 100):
        ax.text(x + 1, i, f"{x:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("本当にいちばん強いチームが優勝した割合（%、2万回）")
    ax.set_title("同じ16チームでも、大会の形で「強いチームが勝つ」割合は変わる")
    save(fig, "a829_formats.png", SRC)

    # 図3：チームどうしの差の大きさで
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for f, c, lab in [("ko1", ORANGE, "1発勝負のトーナメント"), ("ko7", BLUE, "7試合で4勝の勝ち抜け"), ("rr2", GREEN, "総当たり 各組2試合")]:
        d = sv[(sv.teams == 16) & (sv.format == f)]
        ax.plot(d.spread, d.p_strongest_wins * 100, marker="o", color=c, label=lab)
    xt = sv[(sv.teams == 16) & (sv.format == "ko1")]
    ax.set_xticks(xt.spread)
    ax.set_xticklabels([f"{s:g}\n({p*100:.0f}%)" for s, p in zip(xt.spread, xt.p_top_beats_others_1game)], fontsize=9)
    ax.set_xlabel("チームどうしの差（強さの標準偏差）\n（かっこ内：いちばん強いチームがほかのチームに1試合で勝つ確率の平均）")
    ax.set_ylabel("いちばん強いチームが優勝（%）"); ax.set_ylim(0, 100)
    ax.axvline(SPREAD, color=GRAY, lw=1, ls="--")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("チームどうしの差を小さく置くほど、いちばん強いチームは勝ちにくい（16チーム）")
    save(fig, "a829_spread.png", SRC, y=-0.11)
    print(json.dumps({k: out[k] for k in out if k != "ko1_champion_true_rank"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
