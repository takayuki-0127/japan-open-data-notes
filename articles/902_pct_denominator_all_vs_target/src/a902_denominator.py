"""902 分母を「全体」にするか「対象者」にするかで、割合はどう変わるのか？（架空のデータ）

架空の通販の会社が行った40回のクーポン施策。施策ごとに会員の数、クーポンを送った対象者の割合、
対象者のうち使った人の割合（本当の値）を置き、使った人の数は二項分布で引く。
利用率を「会員全体」で割るか「対象者」で割るかで、施策の順位と2つずつの比べがどれだけ入れかわるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 902
SRC = "架空の通販の会社のクーポン施策（作成者が乱数で作成、seed 902）"
N_CAMP = 40
S_MID, Q_MID = 0.30, 0.12     # 対象者の割合・対象者の利用率の真ん中
SD_S, SD_Q = 0.6, 0.6         # 施策どうしの差（ロジットの標準偏差）
RHO = -0.3                    # 対象者の割合と、対象者の利用率の相関（ロジット）


def logit(p):
    return np.log(p / (1 - p))


def inv(x):
    return 1 / (1 + np.exp(-x))


def make(rng, rho=RHO, sd_s=SD_S, sd_q=SD_Q, n=N_CAMP):
    z1, z2 = rng.normal(0, 1, (2, n))
    members = np.round(np.exp(rng.normal(np.log(20000), 0.5, n))).astype(int)
    s = inv(logit(S_MID) + sd_s * z1)
    qq = inv(logit(Q_MID) + sd_q * (rho * z1 + np.sqrt(1 - rho ** 2) * z2))
    target = rng.binomial(members, s)
    used = rng.binomial(target, qq)
    return pd.DataFrame({"campaign": np.arange(1, n + 1), "members": members, "targets": target, "used": used,
                         "true_target_share": s, "true_use_rate_in_target": qq})


def compare(df):
    a = df.used / df.members           # 会員全体で割る
    t = df.used / df.targets           # 対象者で割る
    n = len(df)
    i, j = np.triu_indices(n, 1)
    flip = ((a.values[i] - a.values[j]) * (t.values[i] - t.values[j]) < 0).mean()
    top1 = int(a.idxmax() == t.idxmax())
    top5 = len(set(a.nlargest(5).index) & set(t.nlargest(5).index))
    # 分母がまざった比べ：i は対象者で、j は会員全体で割って報告した組
    mixed_t_wins = (t.values[i] > a.values[j]).mean() * 0.5 + (t.values[j] > a.values[i]).mean() * 0.5
    # まざった比べの答えが、そろえた比べ（対象者どうし／全体どうし）と合う割合
    agree_t = ((t.values[i] > a.values[j]) == (t.values[i] > t.values[j])).mean()
    agree_a = ((t.values[i] > a.values[j]) == (a.values[i] > a.values[j])).mean()
    return {"spearman": float(a.rank().corr(t.rank())), "pair_flip": float(flip), "top1_same": top1, "top5_overlap": top5,
            "mixed_target_reported_wins": float(mixed_t_wins), "mixed_agree_with_target": float(agree_t),
            "mixed_agree_with_all": float(agree_a)}


def expand_example():
    """1つの施策で、対象を広げていく。会員を「使いそうな順」に並べ、上から s の割合に送る。
    順位 u（0〜1）の人が使う確率は 0.40×exp(−4u) と置く（使いそうな人から先に入る）。"""
    N = 100000
    u = (np.arange(N) + 0.5) / N
    p = 0.40 * np.exp(-4 * u)
    rows = []
    for s in [0.05, 0.10, 0.20, 0.40, 0.80, 1.00]:
        k = int(round(N * s))
        used = p[:k].sum()
        rows.append({"target_share": s, "targets": k, "expected_used": round(float(used), 1),
                     "rate_in_target": round(float(used / k), 4), "rate_all": round(float(used / N), 4)})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    df = make(rng)
    df["rate_all"] = df.used / df.members
    df["rate_target"] = df.used / df.targets
    df["rank_all"] = df.rate_all.rank(ascending=False, method="min").astype(int)
    df["rank_target"] = df.rate_target.rank(ascending=False, method="min").astype(int)
    df.to_csv(DATA / "campaigns.csv", index=False, float_format="%.5f")
    one = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in compare(df).items()}
    one["max_rank_change"] = int((df.rank_all - df.rank_target).abs().max())
    one["share_rank_change_ge10"] = round(float(((df.rank_all - df.rank_target).abs() >= 10).mean()), 3)
    one["top_by_target"] = {"campaign": int(df.loc[df.rate_target.idxmax(), "campaign"]),
                            "rank_all": int(df.loc[df.rate_target.idxmax(), "rank_all"]),
                            "rate_target": round(float(df.rate_target.max()), 4),
                            "rate_all": round(float(df.loc[df.rate_target.idxmax(), "rate_all"]), 4),
                            "target_share": round(float(df.loc[df.rate_target.idxmax(), "targets"] /
                                                        df.loc[df.rate_target.idxmax(), "members"]), 4)}
    one["top_by_all"] = {"campaign": int(df.loc[df.rate_all.idxmax(), "campaign"]),
                         "rank_target": int(df.loc[df.rate_all.idxmax(), "rank_target"]),
                         "rate_target": round(float(df.loc[df.rate_all.idxmax(), "rate_target"]), 4),
                         "rate_all": round(float(df.rate_all.max()), 4),
                         "target_share": round(float(df.loc[df.rate_all.idxmax(), "targets"] /
                                                     df.loc[df.rate_all.idxmax(), "members"]), 4)}

    # 500回
    sim = pd.DataFrame([compare(make(np.random.default_rng(SEED * 1000 + r))) for r in range(500)])
    rep = {c: {"mean": round(float(sim[c].mean()), 4), "p10": round(float(sim[c].quantile(.1)), 4),
               "p90": round(float(sim[c].quantile(.9)), 4)} for c in sim.columns}

    # 確かめ：相関 rho × 対象者の割合の差 sd_s（各200回）
    sens = []
    for i, rho in enumerate([-0.6, -0.3, 0.0, 0.3]):
        for j, sd_s in enumerate([0.3, 0.6, 1.0]):
            g = pd.DataFrame([compare(make(np.random.default_rng(SEED * 7 + 10000 * i + 1000 * j + r), rho, sd_s))
                              for r in range(200)])
            sens.append({"rho": rho, "sd_s": sd_s, **{c: round(float(g[c].mean()), 4) for c in
                         ["spearman", "pair_flip", "top1_same", "mixed_target_reported_wins"]}})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    srange = {f"{c}_{m}": float(getattr(sens[c], m)()) for c in ["spearman", "pair_flip", "top1_same",
                                                                  "mixed_target_reported_wins"] for m in ["min", "max"]}

    ex = expand_example()
    ex.to_csv(RES / "expand_example.csv", index=False)

    out = {"settings": {"n_campaign": N_CAMP, "target_share_mid": S_MID, "use_rate_mid": Q_MID, "sd_s_logit": SD_S,
                        "sd_q_logit": SD_Q, "rho": RHO, "members_median": 20000, "n_pairs": N_CAMP * (N_CAMP - 1) // 2,
                        "seed": SEED},
           "one_draw": one, "reps_500": rep, "sensitivity_range": srange, "expand_example": ex.to_dict("records")}
    json.dump(out, open(RES / "a902_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ40回の施策の順位（全体で割る／対象者で割る）
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    for _, r in df.iterrows():
        big = abs(r.rank_all - r.rank_target) >= 10
        ax.plot([0, 1], [r.rank_all, r.rank_target], color=ORANGE if big else LIGHT, lw=1.6 if big else 1, alpha=.9)
    ax.set_xlim(-0.25, 1.25); ax.set_ylim(N_CAMP + 1, 0)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["会員全体で割った順位", "対象者で割った順位"])
    ax.set_ylabel("順位（1が上）")
    ax.spines["bottom"].set_visible(False)
    ax.set_title(f"同じ40回の施策でも、分母を変えると順位が入れかわる\n（橙は10位以上動いた施策、{one['share_rank_change_ge10']*100:.1f}%）")
    save(fig, "a902_rank.png", SRC)

    # 図2：対象を広げると
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(ex.target_share * 100, ex.rate_in_target * 100, "o-", color=ORANGE, label="対象者で割った利用率")
    ax.plot(ex.target_share * 100, ex.rate_all * 100, "o-", color=BLUE, label="会員全体で割った利用率")
    for _, r in ex.iterrows():
        x, ha = (r.target_share * 100 + 1.5, "left") if r.target_share < 1 else (r.target_share * 100 - 1.5, "right")
        ax.text(x, r.rate_in_target * 100 + 1.0, f"{r.rate_in_target*100:.1f}%", ha=ha, fontsize=8.5, color=ORANGE)
        ax.text(x, r.rate_all * 100 - 2.4, f"{r.rate_all*100:.1f}%", ha=ha, fontsize=8.5, color=BLUE)
    ax.set_xlabel("クーポンを送った対象者の割合（会員のうち、%）"); ax.set_ylabel("利用率（%）")
    ax.set_ylim(-3, 42); ax.legend(frameon=False, fontsize=9, loc="center right")
    ax.set_title("対象を広げると、対象者で割った率は下がり、全体で割った率は上がる（例）")
    save(fig, "a902_expand.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for sd_s, c in zip([0.3, 0.6, 1.0], [LIGHT, BLUE, INK]):
        g = sens[sens.sd_s == sd_s]
        ax.plot(g.rho, g.pair_flip * 100, "o-", color=c, label=f"対象者の割合の施策どうしの差 {sd_s}（ロジットの標準偏差）")
    ax.set_xlabel("対象者の割合と、対象者の利用率の相関（作成者が置いた値）")
    ax.set_ylabel("2つの施策の上下が入れかわった組（%）")
    ax.set_ylim(0, 50); ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("絞った施策ほど対象者の利用率が高いと置くほど、入れかわりが増える（各200回）")
    save(fig, "a902_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
