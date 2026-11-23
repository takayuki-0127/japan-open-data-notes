"""1070 使われる割合の高いキャラクターは、強いキャラクターなのか？（架空のデータ）

架空の対戦ゲーム（1対1）。キャラクター20体それぞれに「本当の強さ」と「人気の出やすさ」（見た目・使い心地・話題など、強さと関係のないもの）を作成者が置く。
プレイヤー4,000人は、人気の出やすさと本当の強さを足した好みでキャラクターを1体選ぶ。うまい人ほど強さを重く見て選び、
うまくない人ほど人気の出やすさで選ぶとする。対戦は「見えている点数」（本当のうまさ＋誤差）の近い人どうしで当てる。
キャラクターの置き方を作り直して200回、「使われる割合」「点数の上位2割の人が使う割合」「そのままの勝率」で
本当の強さの上位3体をどれだけ当てられるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1070
SRC = "架空の対戦ゲームのキャラクターと対戦記録（作成者が乱数で作成、seed 1070）"
N_CH = 20
N_PL = 4000
ROUNDS = 20
B_SKILL = 1.0
POWER_SD = 0.10          # 本当の強さの散らばり（ロジット）
NOISE_V, JITTER = 0.5, 0.3
BASE = {"lam": 10.0, "appeal_sd": 0.5, "skill_tilt": 2.0}
SIGNALS = {"usage": "①使われる割合", "usage_top": "②点数の上位2割の人が使う割合", "raw": "③そのままの勝率"}
REPS = 200


def sig(x):
    return 1 / (1 + np.exp(-x))


def one_world(rng, lam, appeal_sd, tilt, keep=False):
    power = rng.normal(0, POWER_SD, N_CH)
    appeal = rng.normal(0, appeal_sd, N_CH)
    s = rng.normal(0, 1, N_PL)
    v = s + rng.normal(0, NOISE_V, N_PL)
    wpow = np.ones(N_PL) if tilt is None else sig(tilt * s)       # 強さをどれだけ重く見るか（うまい人ほど重い）
    util = appeal[None, :] + lam * wpow[:, None] * power[None, :] + rng.gumbel(0, 1, (N_PL, N_CH))
    ch = util.argmax(1)
    usage = np.bincount(ch, minlength=N_CH) / N_PL
    top = v >= np.quantile(v, 0.8)
    usage_top = np.bincount(ch[top], minlength=N_CH) / top.sum()
    A, Bp = [], []
    for _ in range(ROUNDS):
        order = np.argsort(v + rng.normal(0, JITTER, N_PL))
        A.append(order[::2]); Bp.append(order[1::2])
    a = np.concatenate(A); b = np.concatenate(Bp)
    win = rng.random(len(a)) < sig(B_SKILL * (s[a] - s[b]) + power[ch[a]] - power[ch[b]])
    m = ch[a] != ch[b]
    c_all = np.r_[ch[a][m], ch[b][m]]; w_all = np.r_[win[m], ~win[m]]
    games = np.bincount(c_all, minlength=N_CH)
    raw = np.bincount(c_all, weights=w_all, minlength=N_CH) / np.maximum(games, 1)
    raw[games == 0] = np.nan
    # 本当の勝率：同じうまさの相手（相手のキャラクターは使われる割合どおり、同じキャラクターは除く）と当たったとき（式）
    true = np.zeros(N_CH)
    for k in range(N_CH):
        w = usage.copy(); w[k] = 0; w = w / w.sum()
        true[k] = (w * sig(power[k] - power)).sum()
    mean_skill = np.array([s[ch == k].mean() if (ch == k).any() else np.nan for k in range(N_CH)])
    df = pd.DataFrame({"char_id": np.arange(1, N_CH + 1), "power_logit": power, "appeal": appeal, "usage_pct": usage * 100,
                       "usage_top20_pct": usage_top * 100, "raw_winrate": raw * 100, "true_winrate": true * 100,
                       "users_mean_skill": mean_skill, "games": games})
    return df


def score(df):
    true_top3 = set(df.nlargest(3, "power_logit").char_id)
    true_rank = df.power_logit.rank(ascending=False)
    out = {}
    for k, col in [("usage", "usage_pct"), ("usage_top", "usage_top20_pct"), ("raw", "raw_winrate")]:
        x = df[col].fillna(-1)
        top3 = set(df.loc[x.sort_values(ascending=False, kind="mergesort").index[:3], "char_id"])
        first = df.loc[x.idxmax()]
        out[k] = {"hit3": len(top3 & true_top3) / 3,
                  "first_in_true_top3": float(first.char_id in true_top3),
                  "first_true_rank": float(true_rank[x.idxmax()]),
                  "rank_corr": float(x.rank().corr(df.power_logit.rank()))}
    out["raw_first_usage_pct"] = float(df.loc[df.raw_winrate.fillna(-1).idxmax(), "usage_pct"] < 1.0)
    out["usage_vs_rawgap_corr"] = float(df.usage_pct.rank().corr((df.raw_winrate - df.true_winrate).rank()))
    out["usage_vs_raw_corr"] = float(df.usage_pct.rank().corr(df.raw_winrate.rank()))
    out["usage_vs_appeal_corr"] = float(df.usage_pct.rank().corr(df.appeal.rank()))
    return out


def run_many(seed0, lam, appeal_sd, tilt, reps):
    sc = [score(one_world(np.random.default_rng(seed0 + r), lam, appeal_sd, tilt)) for r in range(reps)]
    row = {}
    for k in SIGNALS:
        for mtr in ["hit3", "first_in_true_top3", "first_true_rank", "rank_corr"]:
            row[f"{k}_{mtr}"] = float(np.mean([x[k][mtr] for x in sc]))
    for mtr in ["usage_vs_rawgap_corr", "usage_vs_raw_corr", "usage_vs_appeal_corr", "raw_first_usage_pct"]:
        row[mtr] = float(np.mean([x[mtr] for x in sc]))
    row["usage_first_true_rank_dist"] = np.bincount([int(x["usage"]["first_true_rank"]) for x in sc], minlength=N_CH + 1)[1:].tolist()
    return row


def main():
    t0 = time.time()
    b = BASE
    res = {"setting": {"characters": N_CH, "players": N_PL, "rounds": ROUNDS, "power_sd_logit": POWER_SD, "skill_coef": B_SKILL,
                       "points_noise": NOISE_V, "match_jitter": JITTER, **b, "reps": REPS}}
    base = run_many(SEED * 1000, b["lam"], b["appeal_sd"], b["skill_tilt"], REPS)
    pct = lambda x: round(x * 100, 2)
    res["base"] = {k: {"name": SIGNALS[k], "top3_hit_pct": pct(base[f"{k}_hit3"]),
                       "first_in_true_top3_pct": pct(base[f"{k}_first_in_true_top3"]),
                       "first_true_rank_mean": round(base[f"{k}_first_true_rank"], 2),
                       "rank_corr": round(base[f"{k}_rank_corr"], 3)} for k in SIGNALS}
    res["base"]["chance_top3_hit_pct"] = round(3 / N_CH * 100, 2)
    res["base"]["usage_vs_rawgap_corr"] = round(base["usage_vs_rawgap_corr"], 3)
    res["base"]["usage_vs_raw_corr"] = round(base["usage_vs_raw_corr"], 3)
    res["base"]["usage_vs_appeal_corr"] = round(base["usage_vs_appeal_corr"], 3)
    res["base"]["raw_first_usage_lt1_pct"] = round(base["raw_first_usage_pct"] * 100, 2)
    dist = base["usage_first_true_rank_dist"]
    res["base"]["usage_first_true_rank_dist"] = dist
    res["base"]["usage_first_true_rank_ge11_pct"] = round(sum(dist[10:]) / REPS * 100, 2)
    res["base"]["usage_first_true_rank1_pct"] = round(dist[0] / REPS * 100, 2)
    pd.DataFrame({"true_rank": np.arange(1, N_CH + 1), "worlds": dist}).to_csv(RES / "most_used_true_rank.csv", index=False)
    pd.DataFrame([{"signal": SIGNALS[k], **res["base"][k]} for k in SIGNALS]).drop(columns="name").to_csv(RES / "base_by_signal.csv", index=False)

    # 例の1回分（data と図1）
    ex = one_world(np.random.default_rng(SEED), b["lam"], b["appeal_sd"], b["skill_tilt"])
    ex.round(4).to_csv(DATA / "characters_example.csv", index=False)
    ex_sorted = ex.sort_values("usage_pct", ascending=False)
    res["example"] = {"most_used_char": int(ex_sorted.char_id.iloc[0]), "most_used_pct": round(float(ex_sorted.usage_pct.iloc[0]), 2),
                      "most_used_true_rank": int(ex.power_logit.rank(ascending=False)[ex_sorted.index[0]]),
                      "most_used_true_winrate": round(float(ex_sorted.true_winrate.iloc[0]), 2),
                      "most_used_raw_winrate": round(float(ex_sorted.raw_winrate.iloc[0]), 2),
                      "most_used_appeal_rank": int(ex.appeal.rank(ascending=False)[ex_sorted.index[0]]),
                      "strongest_char": int(ex.loc[ex.power_logit.idxmax(), "char_id"]),
                      "strongest_usage_pct": round(float(ex.loc[ex.power_logit.idxmax(), "usage_pct"]), 2),
                      "strongest_usage_rank": int(ex.usage_pct.rank(ascending=False, method="min")[ex.power_logit.idxmax()]),
                      "strongest_true_winrate": round(float(ex.loc[ex.power_logit.idxmax(), "true_winrate"]), 2),
                      "usage_range_pct": [round(float(ex.usage_pct.min()), 2), round(float(ex.usage_pct.max()), 2)],
                      "true_winrate_range": [round(float(ex.true_winrate.min()), 2), round(float(ex.true_winrate.max()), 2)],
                      "rank_corr_usage_power": round(float(ex.usage_pct.rank().corr(ex.power_logit.rank())), 3)}

    # 確かめ：強さで選ぶ重さ λ × 人気の出やすさの散らばり × うまさによる重みの違い（27通り、各40回）
    grid = []
    j = 0
    for lam in [5.0, 10.0, 20.0]:
        for asd in [0.25, 0.5, 1.0]:
            for tname, tilt in [("うまさで変わらない", None), ("基本", 2.0), ("強く変わる", 4.0)]:
                r = run_many(SEED * 100000 + j * 1000, lam, asd, tilt, 40); j += 1
                grid.append({"lam": lam, "appeal_sd": asd, "skill_tilt": tname,
                             **{f"{k}_top3_hit_pct": pct(r[f"{k}_hit3"]) for k in SIGNALS},
                             **{f"{k}_first_in_top3_pct": pct(r[f"{k}_first_in_true_top3"]) for k in SIGNALS},
                             **{f"{k}_rank_corr": round(r[f"{k}_rank_corr"], 3) for k in SIGNALS},
                             "usage_vs_rawgap_corr": round(r["usage_vs_rawgap_corr"], 3),
                             "raw_first_usage_lt1_pct": round(r["raw_first_usage_pct"] * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    r_ = lambda c, d=grid: [float(d[c].min()), float(d[c].max())]
    res["grid_range"] = {"n_cases": int(len(grid)),
                         **{f"{k}_top3_hit_pct": r_(f"{k}_top3_hit_pct") for k in SIGNALS},
                         **{f"{k}_first_in_top3_pct": r_(f"{k}_first_in_top3_pct") for k in SIGNALS},
                         **{f"{k}_rank_corr": r_(f"{k}_rank_corr") for k in SIGNALS},
                         "usage_top_gt_usage_cases": int((grid.usage_top_top3_hit_pct > grid.usage_top3_hit_pct).sum()),
                         "usage_top_gt_usage_cases_by_tilt": {t: int((gg.usage_top_top3_hit_pct > gg.usage_top3_hit_pct).sum()) for t, gg in grid.groupby("skill_tilt", sort=False)},
                         "usage_top3_hit_by_appeal_sd": {str(a): r_("usage_top3_hit_pct", grid[grid.appeal_sd == a]) for a in [0.25, 0.5, 1.0]},
                         "usage_vs_rawgap_corr": r_("usage_vs_rawgap_corr"),
                         "lam20_no_tilt": grid[(grid.lam == 20) & (grid.skill_tilt == "うまさで変わらない")][["appeal_sd", "raw_top3_hit_pct", "raw_first_usage_lt1_pct", "usage_top3_hit_pct"]].to_dict(orient="records"),
                         "usage_vs_rawgap_corr_by_tilt": {t: r_("usage_vs_rawgap_corr", grid[grid.skill_tilt == t]) for t in ["うまさで変わらない", "基本", "強く変わる"]}}
    with open(RES / "a1070_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：例の1回分、使われる割合と本当の勝率
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    scx = ax.scatter(ex.usage_pct, ex.true_winrate, c=ex.appeal, cmap="coolwarm", s=46, edgecolor=INK, lw=0.4)
    top3 = ex.nlargest(3, "power_logit")
    for _, rr in ex.iterrows():
        # 近くに点が集まるところは、ラベルを点の左に置いて重ならないようにする
        crowded = ((ex.usage_pct - rr.usage_pct).abs() < 0.6) & ((ex.true_winrate - rr.true_winrate).abs() < 0.6)
        if crowded.sum() >= 3 and rr.true_winrate <= ex.loc[crowded, "true_winrate"].min():
            ax.text(rr.usage_pct, rr.true_winrate - 0.25, f"{int(rr.char_id)}", fontsize=8, color=INK, ha="center", va="top")
        elif crowded.sum() >= 3 and rr.usage_pct < ex.loc[crowded, "usage_pct"].max():
            ax.text(rr.usage_pct - 0.15, rr.true_winrate, f"{int(rr.char_id)}", fontsize=8, color=INK, ha="right", va="center")
        else:
            ax.text(rr.usage_pct + 0.12, rr.true_winrate + 0.12, f"{int(rr.char_id)}", fontsize=8, color=INK)
    ax.scatter(top3.usage_pct, top3.true_winrate, s=170, facecolor="none", edgecolor=ORANGE, lw=1.5, label="本当の強さの上位3体")
    ax.set_xlim(0, ex.usage_pct.max() * 1.12)
    ax.axhline(50, color=GRAY, lw=0.8, ls=":")
    ax.set_xlabel("使われる割合（%）"); ax.set_ylabel("本当の勝率（%、式）")
    cb = fig.colorbar(scx, ax=ax, pad=0.02); cb.set_label("人気の出やすさ（強さと関係ない）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(f"例の1回分（20体）：使われる割合と本当の勝率の順位相関 {res['example']['rank_corr_usage_power']:.2f}")
    save(fig, "a1070_example.png", SRC)

    # 図2：上位3体の当たり（200回の平均）
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    ks = list(SIGNALS)
    y = np.arange(len(ks))
    v1 = [res["base"][k]["top3_hit_pct"] for k in ks]; v2 = [res["base"][k]["first_in_true_top3_pct"] for k in ks]
    ax.barh(y - 0.2, v1, 0.38, color=BLUE, label="上位3体のうち本当の上位3体だった割合")
    ax.barh(y + 0.2, v2, 0.38, color=ORANGE, label="いちばん上の1体が本当の上位3体に入っていた割合")
    for i in range(len(ks)):
        ax.text(v1[i] + 0.8, i - 0.2, f"{v1[i]:.1f}%", va="center", fontsize=8.5)
        ax.text(v2[i] + 0.8, i + 0.2, f"{v2[i]:.1f}%", va="center", fontsize=8.5)
    ax.axvline(res["base"]["chance_top3_hit_pct"], color=GRAY, ls="--", lw=1)
    ax.text(res["base"]["chance_top3_hit_pct"] + 0.8, -0.55, f"でたらめに選んだとき {res['base']['chance_top3_hit_pct']:.0f}%", fontsize=8.5, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([SIGNALS[k] for k in ks]); ax.set_ylim(len(ks) - 0.4, -0.75); ax.set_xlim(0, 100)
    ax.set_xlabel("%（キャラクターの置き方を作り直して200回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=1)
    ax.set_title("本当の強さの上位3体を、どの数字でどれだけ当てられるか（基本の置き方）")
    save(fig, "a1070_hits.png", SRC, y=-0.3)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    xs = np.arange(len(grid))
    for k, c, mk in [("usage", BLUE, "o"), ("usage_top", GREEN, "^"), ("raw", ORANGE, "s")]:
        ax.scatter(xs, grid[f"{k}_top3_hit_pct"], color=c, marker=mk, s=26, label=SIGNALS[k])
    ax.axhline(res["base"]["chance_top3_hit_pct"], color=GRAY, ls=":", lw=1)
    for k in [9, 18]:
        ax.axvline(k - 0.5, color=GRAY, lw=0.8, ls="--")
    ax.set_ylim(0, 105)
    for k, lam in enumerate([5, 10, 20]):
        ax.text(k * 9 + 4, 104, f"強さで選ぶ重さ λ={lam}", ha="center", va="top", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels([f"{a:g}" for a in grid.appeal_sd], fontsize=8)
    ax.set_xlabel("人気の出やすさの散らばり（目盛り）\n同じ散らばりの3つは、うまさで強さの重みが「変わらない・基本・強く変わる」の順")
    ax.set_ylabel("上位3体の当たり（%）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax.set_title("置き方を変えた27通り（各40回）：点線はでたらめに選んだとき（15%）")
    save(fig, "a1070_grid.png", SRC, y=-0.25)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
