"""944 自己評価と上司評価のずれは、何を表しているのか？（架空のデータ）

架空の会社の人たち。人ごとに「本当の働き」（5段階の点の目盛りで平均3.0）を置く。
自己評価＝本当の働き＋本人の自己評価の癖（平均+0.2）＋その年のぶれ。
上司評価＝本当の働き＋上司の甘さ＋その年のぶれ。
ずれ（自己評価−上司評価）が、本人の癖・上司の甘さ・ぶれのどれでできているかを数え、
「上司評価の低い人ほど自分を高く見ている」という読み方が、本人の癖がなくても出ることを確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 944
SRC = "架空の会社の自己評価と上司評価（作成者が乱数で作成、seed 944）"
P_SD, B_MEAN = 0.5, 0.2
BASE = dict(bsd=0.25, lsd=0.25, esd=0.4, link=0.0)
GROUPS = ["本当の働き", "その年の上司評価", "その年の自己評価", "別の上司の評価"]


def make(rng, n_boss, team, years, bsd, lsd, esd, link):
    """link：本当の働きが低い人ほど自分を高く見る強さ（0なら、癖は働きと無関係）"""
    n = n_boss * team
    P = 3.0 + rng.normal(0, P_SD, n)
    b = B_MEAN - link * (P - 3.0) + rng.normal(0, bsd, n)
    lb = rng.normal(0, lsd, n_boss)
    boss = np.repeat(np.arange(n_boss), team)
    S = P[:, None] + b[:, None] + rng.normal(0, esd, (n, years))
    B = P[:, None] + lb[boss][:, None] + rng.normal(0, esd, (n, years))
    other = P + rng.normal(0, lsd, n) + rng.normal(0, esd, n)   # 別の上司（甘さも、ぶれも別）の評価
    return dict(P=P, b=b, lb=lb, boss=boss, S=S, B=B, other=other)


def r3(x):
    return round(float(x), 3) + 0.0


def quartile_gap(d):
    g = d["S"][:, 0] - d["B"][:, 0]
    out = {}
    for name, key in zip(GROUPS, [d["P"], d["B"][:, 0], d["S"][:, 0], d["other"]]):
        q = pd.qcut(key, 4, labels=False)
        m = pd.Series(g).groupby(q).mean()
        out[name] = [r3(v) for v in m.values]
    return out


def main():
    rng = np.random.default_rng(SEED)

    # 0) 1社分（上司100人×10人、3年）を data に置く
    d0 = make(rng, 100, 10, 3, **BASE)
    df = pd.DataFrame({"staff_id": np.arange(1, 1001), "boss_id": d0["boss"] + 1, "true_work": d0["P"],
                       "self_habit": d0["b"], "boss_leniency": d0["lb"][d0["boss"]]})
    for y in range(3):
        df[f"self_y{y + 1}"] = d0["S"][:, y]; df[f"boss_y{y + 1}"] = d0["B"][:, y]
    df["other_boss_rating"] = d0["other"]
    df.to_csv(DATA / "company_1000_3years.csv", index=False, float_format="%.3f")

    # 1) 基本の置き方（上司2万人×10人＝20万人）
    d = make(np.random.default_rng(SEED * 10), 20000, 10, 3, **BASE)
    g1 = d["S"][:, 0] - d["B"][:, 0]
    g3 = (d["S"] - d["B"]).mean(1)
    var = {"self_habit": BASE["bsd"] ** 2, "boss_leniency": BASE["lsd"] ** 2,
           "self_noise": BASE["esd"] ** 2, "boss_noise": BASE["esd"] ** 2}
    tot = sum(var.values())
    share = {k: round(100 * v / tot, 1) for k, v in var.items()}
    gdf = pd.DataFrame({"boss": d["boss"], "g1": g1})
    team = gdf.groupby("boss").g1.mean()
    base = {"gap_mean": r3(g1.mean()), "gap_sd": r3(g1.std()),
            "variance_share_pct_formula": share,
            "corr_gap1_self_habit_formula": r3(np.sqrt(var["self_habit"] / tot)),
            "corr_gap1_self_habit": r3(np.corrcoef(g1, d["b"])[0, 1]),
            "corr_gap1_boss_leniency": r3(np.corrcoef(g1, d["lb"][d["boss"]])[0, 1]),
            "corr_gap1_true_work": r3(np.corrcoef(g1, d["P"])[0, 1]),
            "corr_gap3_self_habit": r3(np.corrcoef(g3, d["b"])[0, 1]),
            "corr_team_gap_boss_leniency": r3(np.corrcoef(team.values, d["lb"])[0, 1]),
            "share_gap1_positive_pct": round(100 * float((g1 > 0).mean()), 1),
            "share_habit_positive_pct": round(100 * float((d["b"] > 0).mean()), 1),
            "share_gap1_sign_wrong_pct": round(100 * float((np.sign(g1) != np.sign(d["b"])).mean()), 1)}
    qg = quartile_gap(d)
    # 2) 本当に「働きが低い人ほど自分を高く見る」と置いた場合（link 0.3）
    d_link = make(np.random.default_rng(SEED * 11), 20000, 10, 3, **{**BASE, "link": 0.3})
    qg_link = quartile_gap(d_link)
    rows = []
    for scen, q in [("本人の癖は働きと無関係", qg), ("働きが低い人ほど自分を高く見る（0.3）", qg_link)]:
        for name in GROUPS:
            rows.append({"scenario": scen, "grouped_by": name, **{f"Q{i + 1}_gap": v for i, v in enumerate(q[name])},
                         "Q1_minus_Q4": r3(q[name][0] - q[name][3])})
    qdf = pd.DataFrame(rows)
    qdf.to_csv(RES / "gap_by_quartile.csv", index=False)

    # 3) 確かめ：ぶれ・上司の甘さ・本人の癖の大きさ（24通り、各10万人）
    grid = []
    for esd in [0.0, 0.2, 0.4, 0.6]:
        for lsd in [0.0, 0.25]:
            for bsd in [0.1, 0.25, 0.4]:
                gd = make(np.random.default_rng(SEED * 1000 + int(esd * 10) * 100 + int(lsd * 100) + int(bsd * 10)),
                          10000, 10, 3, bsd, lsd, esd, 0.0)
                q = quartile_gap(gd)
                gg1 = gd["S"][:, 0] - gd["B"][:, 0]
                gg3 = (gd["S"] - gd["B"]).mean(1)
                grid.append({"noise_sd": esd, "leniency_sd": lsd, "habit_sd": bsd,
                             "by_boss_Q1_minus_Q4": r3(q[GROUPS[1]][0] - q[GROUPS[1]][3]),
                             "by_other_Q1_minus_Q4": r3(q[GROUPS[3]][0] - q[GROUPS[3]][3]),
                             "by_true_Q1_minus_Q4": r3(q[GROUPS[0]][0] - q[GROUPS[0]][3]),
                             "corr_gap1_habit": r3(np.corrcoef(gg1, gd["b"])[0, 1]),
                             "corr_gap3_habit": r3(np.corrcoef(gg3, gd["b"])[0, 1])})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid_24.csv", index=False)
    gn = g[g.noise_sd > 0]
    g0 = g[(g.noise_sd == 0) & (g.leniency_sd == 0)]
    gsum = {"n_settings": int(len(g)),
            "by_boss_range_noise_pos": [float(gn.by_boss_Q1_minus_Q4.min()), float(gn.by_boss_Q1_minus_Q4.max())],
            "n_by_boss_positive_noise_pos": int((gn.by_boss_Q1_minus_Q4 > 0).sum()), "n_noise_pos": int(len(gn)),
            "by_boss_noise0_len0_range": [float(g0.by_boss_Q1_minus_Q4.min()), float(g0.by_boss_Q1_minus_Q4.max())],
            "by_boss_noise0_len_pos_range": [float(g[(g.noise_sd == 0) & (g.leniency_sd > 0)].by_boss_Q1_minus_Q4.min()),
                                             float(g[(g.noise_sd == 0) & (g.leniency_sd > 0)].by_boss_Q1_minus_Q4.max())],
            "by_other_abs_max": float(g.by_other_Q1_minus_Q4.abs().max()),
            "by_true_abs_max": float(g.by_true_Q1_minus_Q4.abs().max()),
            "corr_gap1_habit_range_noise_pos": [float(gn.corr_gap1_habit.min()), float(gn.corr_gap1_habit.max())],
            "corr_gap3_habit_range_noise_pos": [float(gn.corr_gap3_habit.min()), float(gn.corr_gap3_habit.max())]}

    out = {"base_200k": base, "gap_by_quartile": rows, "grid_24": gsum}
    json.dump(out, open(RES / "a944_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：上司評価の4分の1ごとの、ずれの平均（2つの置き方）と本当の働きで分けた場合
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.9), sharey=True)
    x = np.arange(4)
    for ax, q, ttl in [(axes[0], qg, "本人の癖は働きと無関係と置いた場合"),
                       (axes[1], qg_link, "働きが低い人ほど自分を高く見ると置いた場合")]:
        for name, col, mk in [(GROUPS[1], ORANGE, "o"), (GROUPS[0], INK, "s"), (GROUPS[3], BLUE, "^")]:
            ax.plot(x, q[name], marker=mk, color=col, lw=1.6, label=f"{name}で分けた")
        ax.axhline(B_MEAN, color=GRAY, lw=0.8, ls=":")
        ax.text(3.15, B_MEAN, "癖の平均", color=GRAY, fontsize=8, va="center")
        ax.set_xticks(x); ax.set_xticklabels(["下位25%", "", "", "上位25%"]); ax.set_xlim(-0.3, 3.6)
        ax.set_title(ttl, fontsize=10.5); ax.set_xlabel("分ける物差しの4分の1（低い→高い）")
    axes[0].set_ylabel("ずれの平均（自己評価−上司評価、点）")
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.suptitle("その年の上司評価で分けると、癖が働きと無関係でも「下位ほど自分を高く見る」形が出る", fontsize=12, y=1.04)
    save(fig, "a944_quartile.png", SRC, y=-0.03)

    # 図2：ずれの中身（分散の割合、式）
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    labels = ["本人の自己評価の癖", "上司の甘さ", "自己評価のその年のぶれ", "上司評価のその年のぶれ"]
    cols = [ORANGE, BLUE, GRAY, LIGHT]
    vals = [share[k] for k in var.keys()]
    yy = np.arange(4)[::-1]
    ax.barh(yy, vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(v + 1, yy[i], f"{v:.1f}%", va="center", fontsize=9)
    ax.set_yticks(yy); ax.set_yticklabels(labels); ax.set_xlim(0, 50)
    ax.set_xlabel("1年のずれのばらつき（分散）のうちの割合（%、置いた値からの式）")
    ax.set_title("1年のずれのうち、本人の癖で決まるのは一部")
    save(fig, "a944_variance.png", SRC, y=-0.09)

    # 図3：部署（上司）ごとのずれの平均と、上司の甘さ
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    sub = np.arange(2000)
    ax.scatter(d["lb"][sub], team.values[sub], s=7, color=BLUE, alpha=.45, lw=0)
    ax.set_xlabel("上司の甘さ（作成者が置いた値、点）"); ax.set_ylabel("部署10人のずれの平均（点）")
    ax.set_title(f"部署ごとのずれの平均は、上司の甘さを映す（相関{base['corr_team_gap_boss_leniency']:.2f}）")
    save(fig, "a944_team.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
