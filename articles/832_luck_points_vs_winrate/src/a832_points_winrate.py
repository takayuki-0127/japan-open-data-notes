"""832 勝ち点と勝率で、順位はどれだけ入れ替わるのか？（架空のデータ）

架空のリーグ（基本12チーム、どの2チームも4試合、1チーム44試合）。チームごとに「本当の強さ」θと
「引き分けやすさ」δを置く。1試合の結果は、強さの差 d=θi−θj と、引き分けの幅 c=c0+δi+δj から
  i の勝ち = σ(d−c)、j の勝ち = σ(−d−c)、引き分け = 残り（σ はロジスティック関数）
で決める。順位は ①勝ち点（勝3・分1）②勝ち点（勝2・分1。勝ち越し数と同じ順）③勝率（勝÷(勝＋負)、分は除く）。
同じ値のときは、3つの並べ方で共通の抽選で順を決める。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 832
SRC = "架空のリーグの成績（作成者が乱数で作成、seed 832）"
rng = np.random.default_rng(SEED)
N_REP = 3000


def sig(x):
    return 1 / (1 + np.exp(-x))


def season(rng, n_rep, n_team=12, games_per_pair=4, theta_sd=0.5, draw_sd=0.3, c0=0.55):
    theta = rng.normal(0, theta_sd, (n_rep, n_team))
    delta = rng.normal(0, draw_sd, (n_rep, n_team))
    W = np.zeros((n_rep, n_team)); D = np.zeros((n_rep, n_team)); L = np.zeros((n_rep, n_team))
    for i in range(n_team):
        for j in range(i + 1, n_team):
            d = theta[:, i] - theta[:, j]
            c = np.maximum(c0 + delta[:, i] + delta[:, j], 0.0)
            pw, pl = sig(d - c), sig(-d - c)
            u = rng.random((n_rep, games_per_pair))
            wi = (u < pw[:, None]).sum(1)
            lj = (u >= 1 - pl[:, None]).sum(1)
            dr = games_per_pair - wi - lj
            W[:, i] += wi; L[:, i] += lj; D[:, i] += dr
            W[:, j] += lj; L[:, j] += wi; D[:, j] += dr
    return theta, delta, W, D, L


def ranks(score, tieb):
    """大きいほど上位。同点は共通の抽選 tieb で順を決める。1 が首位"""
    key = score * 1000 + tieb          # score の差は抽選（0〜1）より必ず大きくなるよう 1000 倍
    order = np.argsort(-key, axis=1)
    r = np.empty_like(order)
    rows = np.arange(order.shape[0])[:, None]
    r[rows, order] = np.arange(1, order.shape[1] + 1)
    return r


def spearman(a, b):
    a = a - a.mean(1, keepdims=True); b = b - b.mean(1, keepdims=True)
    return (a * b).sum(1) / np.sqrt((a * a).sum(1) * (b * b).sum(1))


def summarize(rng, theta, delta, W, D, L):
    n = theta.shape[1]
    tieb = rng.random(theta.shape)
    pts3 = 3 * W + D
    pts2 = 2 * W + D
    wr = W / np.maximum(W + L, 1)
    r3, r2, rw = ranks(pts3, tieb), ranks(pts2, tieb), ranks(wr, tieb)
    rt = ranks(theta, tieb)
    out = {"draw_share": round(float(D.sum() / (W + D + L).sum()), 3)}
    for nm, ra, rb in [("pts3_vs_winrate", r3, rw), ("pts3_vs_pts2", r3, r2)]:
        diff = ra != rb
        out[nm] = {"mean_teams_changed": round(float(diff.sum(1).mean()), 2),
                   "p_top1_differs": round(float((ra.argmin(1) != rb.argmin(1)).mean()), 3),
                   "p_top3_set_differs": round(float(np.mean([set(np.where(x <= 3)[0]) != set(np.where(y <= 3)[0])
                                                               for x, y in zip(ra, rb)])), 3),
                   "mean_max_rank_gap": round(float(np.abs(ra - rb).max(1).mean()), 2)}
    for nm, ra in [("pts3", r3), ("pts2", r2), ("winrate", rw)]:
        out[nm] = {"spearman_with_true": round(float(spearman(ra.astype(float), rt.astype(float)).mean()), 3),
                   "p_true_best_is_top1": round(float((ra.argmin(1) == theta.argmax(1)).mean()), 3),
                   "mean_abs_rank_error": round(float(np.abs(ra - rt).mean()), 2)}
    return out, (r3, rw, rt)


def main():
    # 1シーズン分（data に保存）
    th, de, W, D, L = season(rng, 1)
    o1, (r3, rw, rt) = summarize(rng, th, de, W, D, L)
    df = pd.DataFrame({"team": [chr(65 + i) for i in range(12)], "theta": th[0], "draw_style": de[0],
                       "W": W[0].astype(int), "D": D[0].astype(int), "L": L[0].astype(int)})
    df["points_3_1"] = 3 * df.W + df.D
    df["winrate"] = df.W / (df.W + df.L)
    df["rank_points"] = r3[0]; df["rank_winrate"] = rw[0]; df["rank_true"] = rt[0]
    df.to_csv(DATA / "season_one.csv", index=False, float_format="%.4f")

    base, (R3, RW, RT) = summarize(np.random.default_rng(SEED * 10 + 1), *season(np.random.default_rng(SEED * 10), N_REP))
    changed = (R3 != RW).sum(1)
    changed_dist = {int(k): round(float((changed == k).mean()), 3) for k in range(0, 13)}

    # 確かめ：引き分けやすさの差・引き分けの多さ・試合数・強さの差
    rows = []
    settings = [("引き分けやすさの差なし", dict(draw_sd=0.0)),
                ("基本", dict()),
                ("引き分けやすさの差が大きい", dict(draw_sd=0.6)),
                ("引き分けが少ない", dict(c0=0.3)),
                ("引き分けが多い", dict(c0=0.85)),
                ("試合が少ない（22試合）", dict(games_per_pair=2)),
                ("試合が多い（88試合）", dict(games_per_pair=8)),
                ("強さの差が小さい", dict(theta_sd=0.25)),
                ("強さの差が大きい", dict(theta_sd=1.0))]
    for k, (nm, kw) in enumerate(settings):
        s, _ = summarize(np.random.default_rng(SEED * 100 + k), *season(np.random.default_rng(SEED * 1000 + k), 2000, **kw))
        rows.append({"setting": nm, "draw_share": s["draw_share"],
                     "teams_changed": s["pts3_vs_winrate"]["mean_teams_changed"],
                     "p_top1_differs": s["pts3_vs_winrate"]["p_top1_differs"],
                     "p_top1_differs_pts3_vs_pts2": s["pts3_vs_pts2"]["p_top1_differs"],
                     "best_top1_pts3": s["pts3"]["p_true_best_is_top1"],
                     "best_top1_winrate": s["winrate"]["p_true_best_is_top1"],
                     "spearman_pts3": s["pts3"]["spearman_with_true"],
                     "spearman_winrate": s["winrate"]["spearman_with_true"]})
    sens = pd.DataFrame(rows)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"settings": {"n_team": 12, "games_per_pair": 4, "games_per_team": 44, "theta_sd": 0.5,
                        "draw_style_sd": 0.3, "c0": 0.55, "n_rep": N_REP},
           "base": base, "teams_changed_dist": changed_dist,
           "one_season": {"draw_share": o1["draw_share"], "teams_changed": int((r3 != rw).sum()),
                          "top1_points": df.team[df.rank_points == 1].item(),
                          "top1_winrate": df.team[df.rank_winrate == 1].item(),
                          "top1_true": df.team[df.rank_true == 1].item()},
           "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a832_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1シーズンの勝ち点の順位と勝率の順位
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    ax.plot([0.5, 12.5], [0.5, 12.5], color=GRAY, lw=.8, ls=":")
    same = df.rank_points == df.rank_winrate
    ax.scatter(df.rank_points[same], df.rank_winrate[same], s=60, color=BLUE, zorder=3, label="同じ順位")
    ax.scatter(df.rank_points[~same], df.rank_winrate[~same], s=60, color=ORANGE, zorder=3, label="順位が違う")
    for _, r in df.iterrows():
        ax.text(r.rank_points + .25, r.rank_winrate - .1, f"{r.team}（{r.W}勝{r.D}分{r.L}敗）", fontsize=7.5)
    ax.set_xlim(.5, 14.8); ax.set_ylim(12.5, .5)
    ax.set_xticks(range(1, 13)); ax.set_yticks(range(1, 13))
    ax.set_xlabel("勝ち点（勝3・分1）の順位"); ax.set_ylabel("勝率（分を除く）の順位")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title(f"ある1シーズン（12チーム・44試合）：{out['one_season']['teams_changed']}チームの順位が違った")
    save(fig, "a832_one_season.png", SRC)

    # 図2：順位が違ったチームの数の分布
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ks = np.arange(0, 13)
    ax.bar(ks, [changed_dist[k] * 100 for k in ks], color=BLUE)
    ax.set_xticks(ks); ax.set_xlabel("勝ち点と勝率で順位が違ったチームの数（12チーム中）")
    ax.set_ylabel("シーズンの割合（%）")
    ax.set_title(f"平均{base['pts3_vs_winrate']['mean_teams_changed']:.1f}チーム。首位が違ったのは"
                 f"{base['pts3_vs_winrate']['p_top1_differs']*100:.0f}%のシーズン")
    save(fig, "a832_changed.png", SRC)

    # 図3：置き方を変えたときの、首位が違うシーズンの割合
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    y = np.arange(len(sens))[::-1]
    ax.barh(y, sens.p_top1_differs * 100, color=[BLUE if "基本" in s else LIGHT for s in sens.setting])
    for yy, v in zip(y, sens.p_top1_differs * 100):
        ax.text(v + .5, yy, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels([f"{s}（引き分け{d*100:.0f}%）" for s, d in zip(sens.setting, sens.draw_share)], fontsize=9)
    ax.set_xlabel("勝ち点と勝率で首位のチームが違ったシーズンの割合（%、2,000シーズン）")
    ax.set_title("首位の入れ替わりは、引き分けやすさの差と強さの差で動く")
    save(fig, "a832_sens.png", SRC)
    print(json.dumps({k: out[k] for k in ["base", "one_season"]}, ensure_ascii=False, indent=1))
    print(sens.to_string())


if __name__ == "__main__":
    main()
