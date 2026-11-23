"""1075 シーズンの初めに点数を戻すと、上位はどれだけ入れかわるのか？（架空のデータ）

架空の対戦ゲームのリーグ（1,000人）。作成者が1人ひとりの「本当の強さ」を置き、シーズンの間に少しだけ変わるとする。
前のシーズンの終わりの点数を ①そのまま ②半分だけ平均（1500）に戻す ③全員1500に戻す の3つで次のシーズンを始め、
シーズンの途中と終わりの上位50人（上位5%）が、前のシーズンの上位50人・本当の上位50人とどれだけ重なるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1075
SRC = "架空の対戦ゲームのリーグ（作成者が乱数で作成、seed 1075）"
BASE = {"n": 1000, "sd": 200.0, "drift": 30.0, "k": 32.0, "w": 100.0, "warm": 300, "games": 100, "top": 50}
POLICIES = [(1.0, "そのまま"), (0.5, "半分戻す"), (0.0, "全員1500に戻す")]
CHECK = [5, 10, 25, 50, 100]


def pwin(d):
    """点の差 d（自分−相手）のときに勝つ確率。差400点で10対1"""
    return 1.0 / (1.0 + 10.0 ** (-d / 400.0))


def play(rng, true, rating, rounds, k, w, checks=(), top=50):
    """rounds 回の総当たりでない対戦（毎回、点数＋ゆらぎの近い人どうしを当てる）。checks の回の上位を返す"""
    n = len(true)
    snaps = {}
    for t in range(rounds):
        order = np.argsort(rating + rng.normal(0, w, n))
        a, b = order[0::2], order[1::2]
        win_a = (rng.random(len(a)) < pwin(true[a] - true[b])).astype(float)
        d = k * (win_a - pwin(rating[a] - rating[b]))
        rating[a] += d; rating[b] -= d
        if t + 1 in checks:
            snaps[t + 1] = topset(rating, top, rng)
    return rating, snaps


def topset(x, top, rng):
    # 同じ点数の人はくじで並べる
    return set(np.lexsort((rng.random(len(x)), -x))[:top].tolist())


def league(rng, n=1000, sd=200.0, drift=30.0, k=32.0, w=100.0, warm=300, games=100, top=50, checks=CHECK, keep=False):
    t1 = rng.normal(1500, sd, n)
    r1, _ = play(rng, t1, np.full(n, 1500.0), warm, k, w)
    t2 = t1 + rng.normal(0, drift, n)
    prev_top = topset(r1, top, rng)
    true1_top, true2_top = topset(t1, top, rng), topset(t2, top, rng)
    out = {"true_change": top - len(true1_top & true2_top),
           "prev_vs_true1": len(prev_top & true1_top), "prev_vs_true2": len(prev_top & true2_top)}
    state = rng.bit_generator.state
    ends = {}
    for c, _ in POLICIES:
        rg = np.random.default_rng(); rg.bit_generator.state = state  # 3つの決め方で同じ乱数を使う
        start = 1500 + c * (r1 - 1500)
        r2, snaps = play(rg, t2, start.copy(), games, k, w, checks=set(checks), top=top)
        for g in checks:
            if g > games:
                continue
            out[f"c{c}_g{g}_changed"] = top - len(snaps[g] & prev_top)
            out[f"c{c}_g{g}_true_hit"] = len(snaps[g] & true2_top)
        out[f"c{c}_end_changed"] = top - len(snaps[games] & prev_top)
        out[f"c{c}_end_true_hit"] = len(snaps[games] & true2_top)
        out[f"c{c}_end_sd_ratio"] = float(r2.std() / t2.std())
        ends[c] = r2
    if keep:
        return out, t1, t2, r1, ends
    return out


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    reps = 20
    rows = []
    for i in range(reps):
        res = league(np.random.default_rng([SEED, i]), **BASE, keep=(i == 0))
        if i == 0:
            res, t1, t2, r1, ends = res
            pd.DataFrame({"player_id": np.arange(1, BASE["n"] + 1), "true_season1": t1.round(1), "true_season2": t2.round(1),
                          "rating_end_season1": r1.round(1),
                          **{f"rating_end_season2_{nm}": ends[c].round(1) for c, nm in POLICIES}}).to_csv(
                DATA / "league_example.csv", index=False)
        rows.append({"rep": i + 1, **res})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "reps_base.csv", index=False)
    m = df.mean(numeric_only=True)

    path = []
    for c, nm in POLICIES:
        for g in CHECK:
            path.append({"policy": nm, "c": c, "games": g, "changed_mean": r(m[f"c{c}_g{g}_changed"], 2),
                         "changed_min": int(df[f"c{c}_g{g}_changed"].min()), "changed_max": int(df[f"c{c}_g{g}_changed"].max()),
                         "true_hit_mean": r(m[f"c{c}_g{g}_true_hit"], 2)})
    path = pd.DataFrame(path); path.to_csv(RES / "by_policy_games.csv", index=False)

    # 確かめ：1シーズンの試合数 × 本当の強さの変わり方 × 1試合で動かす点の幅（27通り、各5リーグ）
    grid = []
    j = 0
    for games in [50, 100, 200]:
        for drift in [0.0, 30.0, 60.0]:
            for k in [16.0, 32.0, 64.0]:
                rr = [league(np.random.default_rng([SEED, 1000 + j, q]), **dict(BASE, games=games, drift=drift, k=k),
                             checks=[10, games]) for q in range(5)]
                j += 1
                d = pd.DataFrame(rr).mean()
                row = {"games": games, "drift": drift, "k": k, "true_change": r(d["true_change"], 2)}
                for c, nm in POLICIES:
                    row[f"c{c}_g10_changed"] = r(d[f"c{c}_g10_changed"], 2)
                    row[f"c{c}_end_changed"] = r(d[f"c{c}_end_changed"], 2)
                    row[f"c{c}_end_true_hit"] = r(d[f"c{c}_end_true_hit"], 2)
                grid.append(row)
    g = pd.DataFrame(grid); g.to_csv(RES / "grid.csv", index=False)

    T = BASE["top"]
    hl = {"top": T, "reps": reps, "true_change_mean": r(m["true_change"], 2),
          "true_change_min": int(df.true_change.min()), "true_change_max": int(df.true_change.max()),
          "prev_vs_true1_mean": r(m["prev_vs_true1"], 2)}
    for c, nm in POLICIES:
        for g_ in [10, 100]:
            hl[f"c{c}_g{g_}_changed"] = r(m[f"c{c}_g{g_}_changed"], 2)
            hl[f"c{c}_g{g_}_true_hit"] = r(m[f"c{c}_g{g_}_true_hit"], 2)
        hl[f"c{c}_end_sd_ratio"] = r(m[f"c{c}_end_sd_ratio"], 3)
    hl["full_g10_changed_over_true_change"] = r(m["c0.0_g10_changed"] / m["true_change"], 2)
    hl["keep_g100_changed_over_true_change"] = r(m["c1.0_g100_changed"] / m["true_change"], 2)
    hl["keep_minus_full_g100_true_hit"] = r(m["c1.0_g100_true_hit"] - m["c0.0_g100_true_hit"], 2)
    gs = {"n": int(len(g))}
    for c, nm in POLICIES:
        for col in ["g10_changed", "end_changed", "end_true_hit"]:
            gs[f"c{c}_{col}_min"] = r(g[f"c{c}_{col}"].min(), 2); gs[f"c{c}_{col}_max"] = r(g[f"c{c}_{col}"].max(), 2)
    gs["true_change_min"] = r(g.true_change.min(), 2); gs["true_change_max"] = r(g.true_change.max(), 2)
    gs["full_reset_end_more_changed_count"] = int((g["c0.0_end_changed"] > g["c1.0_end_changed"]).sum())
    gs["full_reset_g10_more_changed_count"] = int((g["c0.0_g10_changed"] > g["c1.0_g10_changed"]).sum())
    gs["full_reset_end_better_true_count"] = int((g["c0.0_end_true_hit"] > g["c1.0_end_true_hit"]).sum())
    gs["keep_end_true_hit_ge_full_count"] = int((g["c1.0_end_true_hit"] >= g["c0.0_end_true_hit"]).sum())
    gs["drift0_keep_end_changed_min"] = r(g[g.drift == 0]["c1.0_end_changed"].min(), 2)
    gs["drift0_keep_end_changed_max"] = r(g[g.drift == 0]["c1.0_end_changed"].max(), 2)
    gs["games50_full_end_changed_min"] = r(g[g.games == 50]["c0.0_end_changed"].min(), 2)
    gs["games50_full_end_changed_max"] = r(g[g.games == 50]["c0.0_end_changed"].max(), 2)
    gs["games200_full_end_changed_min"] = r(g[g.games == 200]["c0.0_end_changed"].min(), 2)
    gs["games200_full_end_changed_max"] = r(g[g.games == 200]["c0.0_end_changed"].max(), 2)
    out = {"base_setting": BASE, "policies": [{"c": c, "label": nm} for c, nm in POLICIES],
           "headline": hl, "by_policy_games": path.to_dict("records"), "grid_summary": gs}
    json.dump(out, open(RES / "a1075_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：シーズンの何試合目で、前のシーズンの上位50人から何人入れかわっているか
    cl = {1.0: GRAY, 0.5: BLUE, 0.0: ORANGE}
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for c, nm in POLICIES:
        pp = path[path.c == c]
        ax.plot(pp.games, pp.changed_mean, marker="o", color=cl[c], label=nm)
        dy = {1.0: -2.3, 0.5: 0.8, 0.0: 1.6}[c]
        for x_, y_ in zip(pp.games, pp.changed_mean):
            if x_ == CHECK[-1]:
                ax.text(x_ * 1.07, y_ + {1.0: -1.6, 0.5: -0.3, 0.0: 1.3}[c], f"{y_:.2f}", fontsize=8, color=cl[c], va="center")
            elif c == 1.0 and x_ == 10:
                ax.text(x_ * 1.06, y_ + 0.8, f"{y_:.2f}", fontsize=8, color=cl[c])
            elif c == 0.5 and x_ == 50:
                ax.text(x_ * 0.95, y_ + 0.7, f"{y_:.2f}", fontsize=8, color=cl[c], ha="right")
            else:
                ax.text(x_ * 1.06, y_ + dy, f"{y_:.2f}", fontsize=8, color=cl[c])
    ax.axhline(m["true_change"], color=INK, lw=.8, ls="--")
    ax.text(28, m["true_change"] - 2.6, f"本当の上位50人の入れかわり {m['true_change']:.2f}人", fontsize=8.5)
    ax.set_xlim(4.2, 140)
    ax.set_xscale("log"); ax.set_xticks(CHECK); ax.set_xticklabels([str(x) for x in CHECK])
    ax.set_ylim(0, T); ax.set_xlabel("新しいシーズンの何試合目（対数の目盛り）")
    ax.set_ylabel(f"前のシーズンの上位{T}人から入れかわった人数")
    ax.legend(frameon=False, fontsize=9, loc="upper right", title="シーズンの初めの点数", title_fontsize=9)
    ax.set_title(f"全員を戻すと、序盤の上位は大きく入れかわる（{reps}リーグの平均）")
    save(fig, "a1075_path.png", SRC)

    # 図2：シーズンの終わりと10試合目の上位50人のうち、本当の上位50人に入っていた人数
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(POLICIES)); wd = 0.36
    v10 = [m[f"c{c}_g10_true_hit"] for c, _ in POLICIES]; v100 = [m[f"c{c}_g100_true_hit"] for c, _ in POLICIES]
    b1 = ax.bar(x - wd / 2, v10, wd, color=LIGHT, label="10試合目")
    b2 = ax.bar(x + wd / 2, v100, wd, color=BLUE, label=f"{BASE['games']}試合目（シーズンの終わり）")
    for bars in (b1, b2):
        for bb in bars:
            ax.text(bb.get_x() + bb.get_width() / 2, bb.get_height() + 0.5, f"{bb.get_height():.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([nm for _, nm in POLICIES]); ax.set_ylim(0, T)
    ax.set_ylabel(f"上位{T}人のうち本当の上位{T}人（人）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("全員を戻すと、10試合目の上位50人は本当の上位50人を半分ほどしか含まない")
    save(fig, "a1075_truehit.png", SRC)

    # 図3：27通りのシーズンの終わりの入れかわり
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    lab = [f"{int(a)}試合\n変化{int(b)}" for a, b in g.groupby(["games", "drift"]).size().index]
    gg = g.groupby(["games", "drift"]).mean(numeric_only=True).reset_index()
    xx = np.arange(len(gg)); wd = 0.27
    for i, (c, nm) in enumerate(POLICIES):
        ax.bar(xx + (i - 1) * wd, gg[f"c{c}_end_changed"], wd, color=cl[c], label=nm)
    ax.scatter(xx, gg.true_change, marker="_", s=300, color=INK, zorder=3, label="本当の上位の入れかわり")
    ax.set_xticks(xx); ax.set_xticklabels(lab, fontsize=8)
    ax.set_ylim(0, T); ax.set_ylabel(f"シーズンの終わりに入れかわった人数（{T}人中）")
    ax.set_xlabel("1シーズンの試合数 と 本当の強さのシーズン間の変化（標準偏差）。点の幅3通りの平均")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=2)
    ax.set_title("置き方27通り：シーズンの終わりに入れかわった人数")
    save(fig, "a1075_grid.png", SRC, y=-0.05)

    print(json.dumps(hl, ensure_ascii=False, indent=1)); print(json.dumps(gs, ensure_ascii=False, indent=1))
    print(path.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
