"""1069 キャラクターごとの勝率は、使う人のうまさでどれだけ動くのか？（架空のデータ）

架空の対戦ゲーム（1対1）。プレイヤー6,000人の「本当のうまさ」と、10体のキャラクターの「本当の強さ」を作成者が置く。
勝つ確率は、うまさの差とキャラクターの強さの差で決まる（ロジット＝1.0×うまさの差＋キャラクターの強さの差）。
キャラクターには「むずかしさ」も置き、うまい人ほどむずかしいキャラクターを選びやすいとする（むずかしさは強さに関係しない）。
対戦は「見えている点数」（本当のうまさ＋誤差）の近い人どうしで当てる。
キャラクターごとの勝率を4つの数え方で出し、本当の勝率（同じうまさの相手と当たったときの勝率、式で出す）と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1069
SRC = "架空の対戦ゲームの対戦記録（作成者が乱数で作成、seed 1069）"
N_PL = 6000
ROUNDS = 50
B_SKILL = 1.0
CHARS = list("ABCDEFGHIJ")
POWER = np.array([0.15, 0.10, 0.05, 0.05, 0.0, 0.0, -0.05, -0.05, -0.10, -0.15])   # 本当の強さ（ロジット）
DIFF = np.array([-1.0, 1.0, 0.0, -0.5, 1.0, -1.0, 0.5, 0.0, 1.0, -0.5])           # むずかしさ
BASE = {"gamma": 1.0, "noise_v": 0.5, "match_jitter": 0.3}
METHODS = {"raw": "①そのままの勝率", "top20": "②点数の上位2割どうしの勝率",
           "adj_points": "③点数の差で調整", "adj_true": "④本当のうまさの差で調整（作る側だけが分かる）"}


def sig(x):
    return 1 / (1 + np.exp(-x))


def choose(rng, s, gamma):
    w = np.exp(gamma * DIFF[None, :] * s[:, None])
    p = w / w.sum(1, keepdims=True)
    u = rng.random(len(s))[:, None]
    return (p.cumsum(1) < u).sum(1).clip(0, len(CHARS) - 1)


def play(rng, gamma, noise_v, jitter, n=N_PL, rounds=ROUNDS):
    s = rng.normal(0, 1, n)
    ch = choose(rng, s, gamma)
    v = s + rng.normal(0, noise_v, n)
    A, Bp = [], []
    for _ in range(rounds):
        if jitter is None:      # くじで当てる
            order = rng.permutation(n)
        else:                   # 見えている点数の近い人どうし（毎回少しゆらして並べる）
            order = np.argsort(v + rng.normal(0, jitter, n))
        A.append(order[::2]); Bp.append(order[1::2])
    a = np.concatenate(A); b = np.concatenate(Bp)
    win = rng.random(len(a)) < sig(B_SKILL * (s[a] - s[b]) + POWER[ch[a]] - POWER[ch[b]])
    g = pd.DataFrame({"a": a, "b": b, "ca": ch[a], "cb": ch[b], "dv": v[a] - v[b], "ds": s[a] - s[b], "win_a": win.astype(int)})
    return s, ch, v, g


def true_rate(usage):
    """同じうまさの相手（相手のキャラクターは使われる割合どおり、同じキャラクターは除く）と当たったときの勝率（式）"""
    out = np.zeros(len(CHARS))
    for k in range(len(CHARS)):
        w = usage.copy(); w[k] = 0; w = w / w.sum()
        out[k] = (w * sig(POWER[k] - POWER)).sum()
    return out


def side_long(g):
    """1試合を2人分の行にする（同じキャラクターどうしの試合は除く）"""
    g = g[g.ca != g.cb]
    x = pd.DataFrame({"c": np.r_[g.ca, g.cb], "win": np.r_[g.win_a, 1 - g.win_a],
                      "pa": np.r_[g.a, g.b], "pb": np.r_[g.b, g.a]})
    return g, x


def fit_bt(g, col):
    """勝ち ~ col（差）＋ キャラクターの差 のロジスティック回帰（ニュートン法、キャラクターの強さは平均0に固定）"""
    g = g[g.ca != g.cb]
    k = len(CHARS)
    X = np.zeros((len(g), k))
    X[np.arange(len(g)), g.ca.values] += 1
    X[np.arange(len(g)), g.cb.values] -= 1
    Z = X[:, :-1] - X[:, [-1]]          # 和0の制約
    D = np.c_[g[col].values, Z]
    y = g.win_a.values.astype(float)
    beta = np.zeros(D.shape[1])
    for _ in range(25):
        p = sig(D @ beta)
        H = D.T @ (D * (p * (1 - p))[:, None]) + 1e-8 * np.eye(D.shape[1])
        step = np.linalg.solve(H, D.T @ (y - p))
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    c = np.r_[beta[1:], -beta[1:].sum()]
    return beta[0], c


def rate_from_power(c, usage):
    out = np.zeros(len(CHARS))
    for k in range(len(CHARS)):
        w = usage.copy(); w[k] = 0; w = w / w.sum()
        out[k] = (w * sig(c[k] - c)).sum()
    return out


def evaluate(s, ch, v, g):
    usage = np.bincount(ch, minlength=len(CHARS)) / len(ch)
    tr = true_rate(usage)
    gg, x = side_long(g)
    raw = x.groupby("c").win.mean().reindex(range(len(CHARS))).values
    cut = np.quantile(v, 0.8)
    top = (v[x.pa.values] >= cut) & (v[x.pb.values] >= cut)
    top20 = x[top].groupby("c").win.mean().reindex(range(len(CHARS))).values
    _, cp = fit_bt(g, "dv"); adj_p = rate_from_power(cp, usage)
    _, ct = fit_bt(g, "ds"); adj_t = rate_from_power(ct, usage)
    mean_skill = np.array([s[ch == k].mean() for k in range(len(CHARS))])
    df = pd.DataFrame({"char": CHARS, "power_logit": POWER, "difficulty": DIFF, "usage_pct": usage * 100,
                       "users_mean_skill": mean_skill, "true": tr * 100, "raw": raw * 100, "top20": top20 * 100,
                       "adj_points": adj_p * 100, "adj_true": adj_t * 100,
                       "games_raw": x.groupby("c").size().reindex(range(len(CHARS))).values,
                       "games_top20": x[top].groupby("c").size().reindex(range(len(CHARS))).values,
                       "opp_skill_gap": np.array([(s[x.pa.values] - s[x.pb.values])[x.c.values == k].mean() for k in range(len(CHARS))])})
    return df


def rank_of(v):
    return pd.Series(v).rank(ascending=False, method="min").astype(int).values


def summarize(df):
    out = {}
    for m in METHODS:
        e = df[m] - df["true"]
        out[m] = {"mae_pt": round(float(e.abs().mean()), 3), "max_abs_pt": round(float(e.abs().max()), 3),
                  "hard_mean_err_pt": round(float(e[df.difficulty == 1].mean()), 3),
                  "easy_mean_err_pt": round(float(e[df.difficulty == -1].mean()), 3),
                  "rank_corr": round(float(pd.Series(df[m]).rank().corr(pd.Series(df["true"]).rank())), 3)}
    return out


def main():
    t0 = time.time()
    b = BASE
    res = {"setting": {"players": N_PL, "rounds": ROUNDS, "skill_coef": B_SKILL, "power_logit": dict(zip(CHARS, POWER.tolist())),
                       "difficulty": dict(zip(CHARS, DIFF.tolist())), **b, "reps": 5}}
    dfs = []
    for r in range(5):
        s, ch, v, g = play(np.random.default_rng(SEED * 100 + r), b["gamma"], b["noise_v"], b["match_jitter"])
        if r == 0:
            pd.DataFrame({"player_id": np.arange(1, N_PL + 1), "skill": s.round(3), "points_visible": v.round(3),
                          "char": [CHARS[k] for k in ch]}).to_csv(DATA / "players.csv", index=False)
            gs = g.iloc[:30000].copy()
            gs.insert(0, "game_id", np.arange(1, len(gs) + 1))
            gs["char_a"] = [CHARS[k] for k in gs.ca]; gs["char_b"] = [CHARS[k] for k in gs.cb]
            gs[["game_id", "a", "b", "char_a", "char_b", "win_a"]].rename(columns={"a": "player_a", "b": "player_b"}) \
                .assign(player_a=lambda d: d.player_a + 1, player_b=lambda d: d.player_b + 1).to_csv(DATA / "games_first_10rounds.csv", index=False)
        d = evaluate(s, ch, v, g); d["rep"] = r; dfs.append(d)
    allr = pd.concat(dfs)
    base = allr.groupby("char", sort=False).mean(numeric_only=True).drop(columns="rep")
    base = base.round(3).reset_index()
    base["rank_true"] = rank_of(base["true"]); base["rank_raw"] = rank_of(base["raw"]); base["rank_adj_points"] = rank_of(base["adj_points"])
    base.to_csv(RES / "base_by_character.csv", index=False)
    res["base"] = summarize(base)
    res["base_table"] = base.set_index("char").to_dict(orient="index")
    res["games_per_rep"] = N_PL // 2 * ROUNDS
    res["data_games_rows"] = 30000
    rep_sd = allr.groupby("char", sort=False)[["raw", "adj_points"]].std().round(3)
    res["rep_sd_pt"] = {"raw_max": float(rep_sd.raw.max()), "adj_points_max": float(rep_sd.adj_points.max())}

    # 確かめ：うまさで使うキャラが分かれる強さ γ × 点数の誤差 × 当て方（27通り、各1回）
    grid = []
    j = 0
    for gm in [0.0, 1.0, 2.0]:
        for nv in [0.25, 0.5, 1.0]:
            for mname, jit in [("近い点数どうし", 0.3), ("ゆるく近い点数どうし", 1.0), ("くじ", None)]:
                s, ch, v, g = play(np.random.default_rng(SEED * 10000 + j), gm, nv, jit); j += 1
                d = evaluate(s, ch, v, g); sm = summarize(d)
                row = {"gamma": gm, "noise_v": nv, "matching": mname}
                for m in METHODS:
                    row[f"{m}_mae"] = sm[m]["mae_pt"]; row[f"{m}_hard_err"] = sm[m]["hard_mean_err_pt"]; row[f"{m}_rank_corr"] = sm[m]["rank_corr"]
                row["rank_raw_I"] = int(rank_of(d["raw"])[CHARS.index("I")])
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    gpos = grid[grid.gamma > 0]
    r_ = lambda d, c: [float(d[c].min()), float(d[c].max())]
    res["grid_range"] = {"n_cases": int(len(grid)),
                         "gamma0": {m: r_(grid[grid.gamma == 0], f"{m}_mae") for m in METHODS},
                         "gamma_pos_mae": {m: r_(gpos, f"{m}_mae") for m in METHODS},
                         "gamma_pos_hard_err": {m: r_(gpos, f"{m}_hard_err") for m in METHODS},
                         "gamma_pos_rank_corr": {m: r_(gpos, f"{m}_rank_corr") for m in METHODS},
                         "adj_points_lt_raw_cases_gamma_pos": int((gpos.adj_points_mae < gpos.raw_mae).sum()),
                         "top20_lt_raw_cases_gamma_pos": int((gpos.top20_mae < gpos.raw_mae).sum()),
                         "n_gamma_pos": int(len(gpos)),
                         "random_matching_raw_mae_gamma_pos": r_(gpos[gpos.matching == "くじ"], "raw_mae"),
                         "close_matching_raw_mae_gamma_pos": r_(gpos[gpos.matching == "近い点数どうし"], "raw_mae"),
                         "rank_raw_I_gamma_pos": r_(gpos, "rank_raw_I"),
                         "adj_points_mae_by_noise_gamma_pos": {str(nv): r_(gpos[gpos.noise_v == nv], "adj_points_mae") for nv in [0.25, 0.5, 1.0]},
                         "raw_mae_by_matching_gamma_pos": {mt: r_(gpos[gpos.matching == mt], "raw_mae") for mt in ["近い点数どうし", "ゆるく近い点数どうし", "くじ"]}}
    with open(RES / "a1069_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：キャラクターごとの本当の勝率と、そのままの勝率
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    x = np.arange(len(CHARS)); w = 0.38
    ax.bar(x - w / 2, base["true"] - 50, w, color=GRAY, label="本当の勝率（同じうまさの相手と当たったとき、式）")
    ax.bar(x + w / 2, base["raw"] - 50, w, color=[ORANGE if d == 1 else (BLUE if d == -1 else LIGHT) for d in DIFF], label="そのままの勝率")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([f"{c}\n{['やさしい', 'ふつう', 'むずかしい'][int(np.sign(d)) + 1] if abs(d) == 1 else ('ふつう' if d == 0 else ('やや易' if d < 0 else 'やや難'))}" for c, d in zip(CHARS, DIFF)], fontsize=9)
    ax.set_ylabel("勝率−50（ポイント）")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GRAY, label="本当の勝率（同じうまさの相手と当たったとき、式）"),
                       Patch(color=ORANGE, label="そのままの勝率：むずかしいキャラクター"),
                       Patch(color=LIGHT, label="そのままの勝率：ふつう・やや易・やや難"),
                       Patch(color=BLUE, label="そのままの勝率：やさしいキャラクター")], frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("むずかしいキャラクター（オレンジ）は、そのままの勝率で強く見える")
    save(fig, "a1069_by_char.png", SRC, y=-0.04)

    # 図2：数え方ごとのずれ（基本、平均の絶対値・むずかしいキャラの平均）
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    mm = list(METHODS)
    y = np.arange(len(mm))
    ax.barh(y - 0.2, [res["base"][m]["mae_pt"] for m in mm], 0.38, color=BLUE, label="10体のずれの大きさの平均")
    ax.barh(y + 0.2, [res["base"][m]["hard_mean_err_pt"] for m in mm], 0.38, color=ORANGE, label="むずかしい3体のずれ（平均、＋は強く見える）")
    for i, m in enumerate(mm):
        ax.text(max(res["base"][m]["mae_pt"], 0) + 0.05, i - 0.2, f"{res['base'][m]['mae_pt']:.2f}", va="center", fontsize=8)
        hv = res["base"][m]["hard_mean_err_pt"]
        ax.text(max(hv, 0) + 0.05, i + 0.2, f"{hv:+.2f}", va="center", fontsize=8)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([METHODS[m] for m in mm]); ax.invert_yaxis()
    ax.set_xlabel("本当の勝率とのずれ（ポイント）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("点数でそろえても、ずれは残る（基本の置き方、5回の平均）")
    save(fig, "a1069_methods.png", SRC, y=-0.04)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    xs = np.arange(len(grid))
    for m, c, mk in [("raw", ORANGE, "o"), ("top20", GREEN, "^"), ("adj_points", BLUE, "s")]:
        ax.scatter(xs, grid[f"{m}_mae"], color=c, marker=mk, s=26, label=METHODS[m])
    for k in [9, 18]:
        ax.axvline(k - 0.5, color=GRAY, lw=0.8, ls="--")
    top = max(grid.raw_mae.max(), grid.top20_mae.max()) * 1.12
    ax.set_ylim(0, top)
    for k, gm in enumerate([0.0, 1.0, 2.0]):
        ax.text(k * 9 + 4, top, f"使うキャラの分かれ方 γ={gm:g}", ha="center", va="top", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels(["近" if mt == "近い点数どうし" else ("ゆ" if mt.startswith("ゆるく") else "く") for mt in grid.matching], fontsize=8)
    ax.set_xlabel("当て方（近：近い点数どうし、ゆ：ゆるく近い点数どうし、く：くじ）\n各γの中は、点数の誤差0.25・0.5・1.0の順に3つずつ")
    ax.set_ylabel("10体のずれの大きさの平均（ポイント）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    ax.set_title("置き方を変えた27通り：γ=0（使う人のうまさが同じ）ならずれはほぼない")
    save(fig, "a1069_grid.png", SRC, y=-0.2)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
