"""934 5段階評価の「3」に集まると、何が見えなくなるのか？（架空のデータ）

架空の会社の社員300人。社員ごとに「本当の実力」（平均0・標準偏差1）を置き、評価者が見る印象は
本当の実力にぶれを足したもの。印象を5段階（1〜5）に区切るとき、区切りの位置で「3」の割合を決める。
「段階を広く使う」（1〜5が10・20・40・20・10%）と「3に集まる」（5・10・70・10・5%）を比べ、
本当の上位10%がどれだけ「3」に埋もれるか、上位30人を選べるか、実力が伸びた人の評価が上がるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 934
SRC = "架空の会社の人事評価（作成者が乱数で作成、seed 934）"
N = 300
N_REP = 300
NOISE = 0.5          # 印象のぶれ（本当の実力の標準偏差を1とした大きさ）
GAIN = 0.5           # 伸びた人の伸び（標準偏差の0.5）
GAIN_SHARE = 0.2     # 伸びた人の割合
WIDE = [0.10, 0.20, 0.40, 0.20, 0.10]
CENTER = [0.05, 0.10, 0.70, 0.10, 0.05]


def shares_for_mid(mid):
    """3の割合を mid にし、残りを 1:2:2:1 の比で両側に分ける"""
    r = (1 - mid) / 6
    return [r, 2 * r, mid, 2 * r, r]


def cuts(shares, noise):
    q = np.cumsum(shares)[:-1]
    return norm.ppf(q) * np.sqrt(1 + noise ** 2)


def grade(latent, c):
    return np.searchsorted(c, latent) + 1


def simulate(rng, shares, noise=NOISE, n_rep=N_REP):
    c = cuts(shares, noise)
    true = rng.normal(0, 1, (n_rep, N))
    g1 = grade(true + rng.normal(0, noise, (n_rep, N)), c)
    improved = rng.random((n_rep, N)) < GAIN_SHARE
    true2 = true + GAIN * improved
    # 2年目は区切りを1年目と同じ位置に置く（会社全体の実力が少し上がった分、上の段がわずかに増える）
    g2 = grade(true2 + rng.normal(0, noise, (n_rep, N)), c)
    tie = rng.random((n_rep, N))
    # 上位30人を評価で選ぶ（同じ段の中はくじで決める）
    key = g1 + tie * 0.5
    top_true = np.argsort(-true, axis=1)[:, :30]
    top_sel = np.argsort(-key, axis=1)[:, :30]
    prec = np.mean([len(set(a) & set(b)) / 30 for a, b in zip(top_true, top_sel)])
    thr = np.quantile(true, 0.9, axis=1, keepdims=True)
    top10 = true >= thr
    rc = [np.corrcoef(g1[i], true[i])[0, 1] for i in range(n_rep)]
    up = g2 > g1
    in3 = g1 == 3
    pct = (true.argsort(axis=1).argsort(axis=1) + 0.5) / N * 100
    return {"share_3": float(in3.mean()),
            "top10_rated3": float(in3[top10].mean()),
            "top10_rated_4or5": float((g1[top10] >= 4).mean()),
            "rated3_true_pct_p10": float(np.percentile(pct[in3], 10)),
            "rated3_true_pct_p90": float(np.percentile(pct[in3], 90)),
            "corr_grade_true": float(np.mean(rc)),
            "precision_top30": float(prec),
            "improved_up": float(up[improved].mean()),
            "not_improved_up": float(up[~improved].mean()),
            "up_really_improved": float(improved[up].mean()),
            "improved_same": float((g2 == g1)[improved].mean())}


def main():
    rng = np.random.default_rng(SEED)

    # 1) 1社分（data に置く）
    true = rng.normal(0, 1, N)
    lat = true + rng.normal(0, NOISE, N)
    one = pd.DataFrame({"person_id": np.arange(1, N + 1), "true": true.round(4), "impression": lat.round(4),
                        "grade_wide": grade(lat, cuts(WIDE, NOISE)), "grade_center": grade(lat, cuts(CENTER, NOISE))})
    one.to_csv(DATA / "grades_one_company.csv", index=False)
    top30 = one.nlargest(30, "true")
    one_res = {"top30_true_rated3_center": int((top30.grade_center == 3).sum()),
               "top30_true_rated3_wide": int((top30.grade_wide == 3).sum()),
               "n_rated3_center": int((one.grade_center == 3).sum()),
               "n_rated3_wide": int((one.grade_wide == 3).sum())}

    # 2) 段階を広く使う と 3に集まる（300社）
    main_res = {"wide": simulate(np.random.default_rng(SEED * 10 + 1), WIDE),
                "center": simulate(np.random.default_rng(SEED * 10 + 2), CENTER),
                "continuous_corr_reference": round(float(1 / np.sqrt(1 + NOISE ** 2)), 4)}
    main_res = {k: ({kk: round(vv, 4) for kk, vv in v.items()} if isinstance(v, dict) else v) for k, v in main_res.items()}
    pd.DataFrame({k: main_res[k] for k in ["wide", "center"]}).to_csv(RES / "wide_vs_center.csv")

    # 3) 確かめ：3の割合 × 印象のぶれ
    rows = []
    for i, mid in enumerate([0.4, 0.55, 0.7, 0.85]):
        for j, nz in enumerate([0.3, 0.5, 0.8]):
            # 3が70%・ぶれ0.5 は「3に集まる」（5・10・70・10・5%）と同じ置き方なので、2)と同じ乱数で数える
            sd_ = SEED * 10 + 2 if (mid, nz) == (0.7, NOISE) else SEED * 1000 + i * 10 + j
            r = simulate(np.random.default_rng(sd_), shares_for_mid(mid), nz)
            rows.append({"share3_target": mid, "noise": nz, **{k: round(v, 4) for k, v in r.items()}})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "robustness_share3_noise.csv", index=False)

    out = {"setup": {"n_people": N, "n_rep": N_REP, "noise": NOISE, "gain_sd": GAIN, "gain_share": GAIN_SHARE,
                     "wide_shares": WIDE, "center_shares": CENTER, "grid_shares": "3の割合 mid、残りを1:2:2:1"},
           "one_company": one_res, "main": main_res,
           "grid_ranges": {k: [float(grid[k].min()), float(grid[k].max())]
                           for k in ["top10_rated3", "corr_grade_true", "precision_top30", "improved_up",
                                     "up_really_improved"]},
           "grid_by_share3": {str(m): {k: [float(d[k].min()), float(d[k].max())]
                                       for k in ["top10_rated3", "improved_up", "precision_top30"]}
                              for m, d in grid.groupby("share3_target")}}
    json.dump(out, open(RES / "a934_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1社分の本当の実力と段階
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 5.2), sharex=True)
    bins = np.linspace(-3.2, 3.2, 33)
    cols = {1: "#c7c6c1", 2: LIGHT, 3: GRAY, 4: BLUE, 5: ORANGE}
    for ax, col, ttl in [(axes[0], "grade_wide", "段階を広く使う（1〜5が10・20・40・20・10%）"),
                         (axes[1], "grade_center", "3に集まる（5・10・70・10・5%）")]:
        data = [one.loc[one[col] == g, "true"] for g in range(1, 6)]
        ax.hist(data, bins=bins, stacked=True, color=[cols[g] for g in range(1, 6)],
                label=[f"評価{g}" for g in range(1, 6)], edgecolor="white", lw=.4)
        ax.set_title(ttl, fontsize=11); ax.set_ylabel("人数"); ax.set_ylim(0, 40)
        ax.axvline(np.sort(true)[-30], color=INK, lw=1, ls="--")
    axes[0].text(np.sort(true)[-30] + .05, 24, "本当の上位30人", fontsize=8.5)
    axes[0].legend(frameon=False, fontsize=8, ncol=5, loc="upper left")
    axes[1].set_xlabel("本当の実力（平均0・標準偏差1）")
    fig.suptitle(f"3に集まると、本当の上位30人のうち{one_res['top30_true_rated3_center']}人が「3」になった（1社分）", fontsize=12, y=1.0)
    save(fig, "a934_one_company.png", SRC)

    # 図2：広く使う と 3に集まる の比べ
    items = [("top10_rated3", "本当の上位10%が「3」"), ("precision_top30", "評価で選んだ上位30人の当たり"),
             ("improved_up", "実力が伸びた人の評価が上がる"), ("not_improved_up", "伸びていない人の評価が上がる")]
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    y = np.arange(len(items))
    w = [main_res["wide"][k] * 100 for k, _ in items]
    cc = [main_res["center"][k] * 100 for k, _ in items]
    ax.barh(y - .2, w, height=.38, color=BLUE, label="段階を広く使う")
    ax.barh(y + .2, cc, height=.38, color=ORANGE, label="3に集まる")
    for i in range(len(items)):
        ax.text(w[i] + 1, i - .2, f"{w[i]:.1f}%", va="center", fontsize=8.5)
        ax.text(cc[i] + 1, i + .2, f"{cc[i]:.1f}%", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels([t for _, t in items]); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xlabel("%（300社の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("3に集まると、上位も伸びも「3」の中に隠れる", fontsize=12)
    save(fig, "a934_compare.png", SRC)

    # 図3：3の割合を変えると
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6))
    ncol = {0.3: LIGHT, 0.5: BLUE, 0.8: INK}
    for nz in [0.3, 0.5, 0.8]:
        d = grid[grid.noise == nz]
        axes[0].plot(d.share_3 * 100, d.top10_rated3 * 100, marker="o", ms=4, lw=2, color=ncol[nz], label=f"印象のぶれ {nz}")
        axes[1].plot(d.share_3 * 100, d.improved_up * 100, marker="o", ms=4, lw=2, color=ncol[nz], label=f"印象のぶれ {nz}")
    axes[0].set_ylabel("本当の上位10%のうち「3」の人（%）"); axes[1].set_ylabel("伸びた人のうち評価が上がった人（%）")
    for ax in axes:
        ax.set_xlabel("「3」の人の割合（%）"); ax.set_ylim(0, 100)
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("「3」が増えるほど、上位も伸びも見えなくなる（3の割合4通り×ぶれ3通り）", fontsize=12, y=1.02)
    save(fig, "a934_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
