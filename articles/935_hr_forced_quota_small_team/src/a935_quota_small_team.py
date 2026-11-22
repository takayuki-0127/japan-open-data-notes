"""935 相対評価の枠（上位2割など）は、小さいチームでどう働くのか？（架空のデータ）

架空の会社の社員240人を、同じ人数のチームに分ける（3〜40人）。社員ごとに「本当の実力」を置き、
チームごとの本当の実力の平均にも差を置く。評価者の印象は本当の実力にぶれを足したもの。
各チームで印象の上位2割（人数×0.2を四捨五入）に「A」を付ける決まりと、会社全体で上位2割に付ける決まりを比べ、
本当の上位2割の人がどれだけ A になるか、A の人のうち本当の上位2割は何割かを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 935
SRC = "架空の会社の人事評価（作成者が乱数で作成、seed 935）"
N = 240
SIZES = [3, 4, 5, 6, 8, 10, 12, 20, 40]
QUOTA = 0.2
SD_TEAM = 0.3       # チームの本当の実力の平均の差（本当の実力の標準偏差を1とした大きさ）
NOISE = 0.5         # 評価者の印象のぶれ
N_REP = 300
ROUND = {"四捨五入": lambda x: np.floor(x + 0.5 + 1e-9), "切り捨て": np.floor, "切り上げ": lambda x: np.ceil(x - 1e-9)}


def n_a(size, rule):
    return int(ROUND[rule](size * QUOTA))


def make(rng, size, sd_team=SD_TEAM, noise=NOISE, n_rep=N_REP):
    t = N // size
    tm = rng.normal(0, sd_team, (n_rep, t))
    ind = rng.normal(0, np.sqrt(max(1 - sd_team ** 2, 1e-9)), (n_rep, N))
    true = np.repeat(tm, size, axis=1) + ind
    imp = true + rng.normal(0, noise, (n_rep, N))
    return true, imp


def assign(imp, size, rule):
    """各チームで印象の上位 k 人に A"""
    r, t = imp.shape[0], N // size
    k = n_a(size, rule)
    order = np.argsort(-imp.reshape(r, t, size), axis=2)
    a = np.zeros((r, t, size), bool)
    if k > 0:
        np.put_along_axis(a, order[:, :, :k], True, axis=2)
    return a.reshape(r, N)


def company_wide(imp):
    k = int(round(N * QUOTA))
    a = np.zeros_like(imp, bool)
    np.put_along_axis(a, np.argsort(-imp, axis=1)[:, :k], True, axis=1)
    return a


def metrics(true, a):
    k = int(round(N * QUOTA))
    top = np.zeros_like(true, bool)
    np.put_along_axis(top, np.argsort(-true, axis=1)[:, :k], True, axis=1)
    pct = (true.argsort(axis=1).argsort(axis=1) + 0.5) / N * 100
    band = (pct >= 85) & (pct < 95)
    low = pct < 50
    return {"a_share": float(a.mean()), "recall_top20": float(a[top].mean()),
            "precision_top20": float(top[a].mean()) if a.any() else float("nan"),
            "p_a_pct85_95": float(a[band].mean()), "p_a_bottom_half": float(a[low].mean())}


def main():
    rng = np.random.default_rng(SEED)

    # 1) 1社分（5人チーム、data に置く）
    true, imp = make(rng, 5, n_rep=1)
    a = assign(imp, 5, "四捨五入")
    cw = company_wide(imp)
    df = pd.DataFrame({"person_id": np.arange(1, N + 1), "team": np.arange(N) // 5 + 1, "true": true[0].round(4),
                       "impression": imp[0].round(4), "A_in_team": a[0].astype(int), "A_company_wide": cw[0].astype(int)})
    df.to_csv(DATA / "team5_one_company.csv", index=False)
    pct = (true[0].argsort().argsort() + 0.5) / N * 100
    one = {"top20_true_not_A_in_team": int(((pct >= 80) & ~a[0]).sum()),
           "top20_true_not_A_company_wide": int(((pct >= 80) & ~cw[0]).sum()),
           "A_from_bottom_half_in_team": int((a[0] & (pct < 50)).sum()),
           "A_from_bottom_half_company_wide": int((cw[0] & (pct < 50)).sum())}

    # 2) チームの人数ごと（基本の置き方、四捨五入）と、会社全体で上位2割
    rows = []
    for i, s in enumerate(SIZES):
        tr, im = make(np.random.default_rng(SEED * 100 + i), s)
        for rule in ROUND:
            rows.append({"team_size": s, "rule": rule, "n_A_per_team": n_a(s, rule),
                         **{k: round(v, 4) for k, v in metrics(tr, assign(im, s, rule)).items()}})
        if s == 40:
            cw_m = {k: round(v, 4) for k, v in metrics(tr, company_wide(im)).items()}
    by_size = pd.DataFrame(rows)
    by_size.to_csv(RES / "by_team_size_rule.csv", index=False)

    # 3) 確かめ：チームの実力差 × 印象のぶれ（四捨五入）
    grid = []
    for j, st in enumerate([0.0, 0.3, 0.6]):
        for l, nz in enumerate([0.3, 0.5, 0.8]):
            for i, s in enumerate(SIZES + ["全体"]):
                if (st, nz) == (SD_TEAM, NOISE):
                    seed = SEED * 100 + (SIZES.index(40) if s == "全体" else i)
                else:
                    seed = SEED * 10000 + j * 1000 + l * 100 + (SIZES.index(40) if s == "全体" else i)
                tr, im = make(np.random.default_rng(seed), 40 if s == "全体" else s, st, nz)
                aa = company_wide(im) if s == "全体" else assign(im, s, "四捨五入")
                grid.append({"sd_team": st, "noise": nz, "team_size": s,
                             **{k: round(v, 4) for k, v in metrics(tr, aa).items()}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness_team_noise.csv", index=False)

    base = by_size[by_size.rule == "四捨五入"].set_index("team_size")
    g = grid[grid.team_size != "全体"].copy()
    gw = grid[grid.team_size == "全体"].set_index(["sd_team", "noise"])
    g["recall_gap_vs_company"] = [round(r.recall_top20 - gw.loc[(r.sd_team, r.noise), "recall_top20"], 4) for r in g.itertuples()]
    EVEN = [5, 10, 20, 40]          # 人数×0.2 が割り切れ、A がちょうど2割になる人数
    ge = g[g.team_size.isin(EVEN)]
    out = {"setup": {"n_people": N, "team_sizes": SIZES, "quota": QUOTA, "sd_team": SD_TEAM, "noise": NOISE, "n_rep": N_REP},
           "one_company_team5": one,
           "company_wide_base": cw_m,
           "base_recall_gap_vs_company": {str(s_): round(float(base.loc[s_, "recall_top20"] - cw_m["recall_top20"]), 4) for s_ in EVEN},
           "base_round_half_up": base.drop(columns="rule").reset_index().to_dict("records"),
           "grid_recall_gap_by_size": {str(s_): [float(ge[ge.team_size == s_].recall_gap_vs_company.min()),
                                                 float(ge[ge.team_size == s_].recall_gap_vs_company.max())] for s_ in EVEN},
           "grid_recall_gap_sdteam0": {str(s_): [float(ge[(ge.team_size == s_) & (ge.sd_team == 0)].recall_gap_vs_company.min()),
                                                 float(ge[(ge.team_size == s_) & (ge.sd_team == 0)].recall_gap_vs_company.max())] for s_ in EVEN},
           "a_share_round_half_up_range_3_12": [float(base.loc[[3, 4, 5, 6, 8, 10, 12], "a_share"].min()),
                                                float(base.loc[[3, 4, 5, 6, 8, 10, 12], "a_share"].max())],
           "a_share_all_rules_range_3_12": [float(by_size[by_size.team_size <= 12].a_share.min()),
                                            float(by_size[by_size.team_size <= 12].a_share.max())],
           "grid_p_a_pct85_95_team5": [float(g[g.team_size == 5].p_a_pct85_95.min()), float(g[g.team_size == 5].p_a_pct85_95.max())],
           "grid_p_a_pct85_95_company": [float(gw.p_a_pct85_95.min()), float(gw.p_a_pct85_95.max())],
           "grid_p_a_bottom_half_team5": [float(g[g.team_size == 5].p_a_bottom_half.min()), float(g[g.team_size == 5].p_a_bottom_half.max())],
           "grid_p_a_bottom_half_company": [float(gw.p_a_bottom_half.min()), float(gw.p_a_bottom_half.max())]}
    json.dump(out, open(RES / "a935_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：チームの人数ごとの A の割合（決まりごと）
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    x = np.arange(len(SIZES))
    for off, rule, col in [(-.27, "切り捨て", LIGHT), (0, "四捨五入", BLUE), (.27, "切り上げ", GRAY)]:
        d = by_size[by_size.rule == rule]
        ax.bar(x + off, d.a_share * 100, width=.26, color=col, label=rule)
    ax.axhline(20, color=ORANGE, lw=1, ls="--"); ax.text(len(SIZES) - .6, 21, "2割", color=ORANGE, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"{s}人" for s in SIZES])
    ax.set_xlabel("チームの人数"); ax.set_ylabel("A が付いた人の割合（%）"); ax.set_ylim(0, 45)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper right")
    ax.set_title("「上位2割」でも、小さいチームでは人数の端数で A の割合が0〜33%に動く", fontsize=12)
    save(fig, "a935_a_share.png", SRC)

    # 図2：本当の上位2割が A になる割合、A のうち本当の上位2割（四捨五入）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6))
    for ax, key, ttl in [(axes[0], "p_a_pct85_95", "本当の順位が上から5〜15%の人が A になる割合"),
                         (axes[1], "p_a_bottom_half", "本当の順位が下半分の人が A になる割合")]:
        xe = np.arange(len(EVEN))
        ax.plot(xe, base.loc[EVEN, key] * 100, marker="o", ms=5, lw=2, color=BLUE, label="チームごとに上位2割")
        for xi, v in zip(xe, base.loc[EVEN, key] * 100):
            if key == "p_a_pct85_95":
                ax.text(xi, v - 6, f"{v:.1f}%", ha="center", va="top", fontsize=8.5)
            else:
                ax.text(xi, v + 0.3, f"{v:.1f}%", ha="center", va="bottom", fontsize=8.5)
        ax.axhline(cw_m[key] * 100, color=ORANGE, lw=1.5, ls="--", label="会社全体で上位2割")
        ax.text(1.5 if key == "p_a_pct85_95" else 0.35, cw_m[key] * 100 * 1.04 + (0 if key == "p_a_pct85_95" else 0.15), f"会社全体 {cw_m[key]*100:.1f}%", ha="center", va="bottom", color=ORANGE, fontsize=8.5)
        ax.set_xticks(xe); ax.set_xticklabels([f"{s}人" for s in EVEN]); ax.set_xlabel("チームの人数（A がちょうど2割になる人数）")
        ax.set_title(ttl, fontsize=10.5)
    axes[0].set_ylabel("%（300社の平均）"); axes[0].set_ylim(0, 100); axes[1].set_ylim(0, 10)
    axes[0].legend(frameon=False, fontsize=9, loc="lower right")
    fig.suptitle("小さいチームほど、上位の人が A を逃し、下半分の人に A が付く（チームの差0.3・ぶれ0.5）", fontsize=12, y=1.03)
    save(fig, "a935_by_size.png", SRC, y=-0.04)

    # 図3：チームの差とぶれを変えたとき、会社全体より何ポイント取りこぼすか
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.6), sharey=True)
    ncol = {0.3: LIGHT, 0.5: BLUE, 0.8: INK}
    for ax, st in zip(axes, [0.0, 0.3, 0.6]):
        for nz in [0.3, 0.5, 0.8]:
            d = ge[(ge.sd_team == st) & (ge.noise == nz)]
            ax.plot(np.arange(len(EVEN)), d.recall_gap_vs_company * 100, marker="o", ms=4, lw=2, color=ncol[nz], label=f"ぶれ {nz}")
        ax.axhline(0, color=GRAY, lw=1)
        ax.set_xticks(np.arange(len(EVEN))); ax.set_xticklabels([f"{s}人" for s in EVEN], fontsize=9)
        ax.set_xlabel("チームの人数"); ax.set_title(f"チームの実力の差 {st}", fontsize=11)
    axes[0].set_ylabel("本当の上位2割が A になる割合の\n会社全体との差（ポイント）", fontsize=10, linespacing=1.6)
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle("チームごとの枠は、チームの差が大きいほど、人数が少ないほど取りこぼす", fontsize=12, y=1.03)
    save(fig, "a935_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
