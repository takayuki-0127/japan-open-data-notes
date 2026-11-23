"""1004 「過去最高の来場」は、数え方を変えた年と比べられるのか？（架空のデータ）

架空の年1回の展示会（3日間）。2013〜2026年の本当の来場者数（延べ）を作成者が乱数で置き、
2020年までは「受付の集計と係の見込み」（旧い数え方）、2021年からは「ゲートの機械で通った回数」（新しい数え方。
再入場も数えるため、同じ来場でも平均1.2倍に出る）で発表したとして、「過去最高」の発表がどれだけ本当に過去最高かを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1004
SRC = "架空の展示会の来場者数（作成者が乱数で作成、seed 1004）"
YEARS = np.arange(2013, 2027)
C = 2021                      # 新しい数え方の最初の年（この年だけ両方で数えた）
IC = int(np.where(YEARS == C)[0][0])
BASE = dict(R=1.2, sigma=0.08, s_r=0.05, s_old=0.03, g=0.01)
N_WORLD = 5000


def make(rng, n, p):
    ny = len(YEARS)
    t = np.arange(ny)
    true = 50000 * np.exp(p["g"] * t[None, :] + rng.normal(0, p["sigma"], (n, ny)))
    old = true * np.exp(rng.normal(0, p["s_old"], (n, ny)))
    r = p["R"] * np.exp(rng.normal(0, p["s_r"], (n, ny)))
    new = true * r
    rec = np.where(t[None, :] < IC, old, new)
    ratio_hat = new[:, IC] / old[:, IC]                       # 2021年の両方の数から出した比
    adj = np.where(t[None, :] < IC, old * ratio_hat[:, None], new)       # 旧い年を比で直す
    adj_exact = np.where(t[None, :] < IC, old * p["R"], new)             # 本当の平均の比 R で直す
    return dict(true=true, old=old, new=new, rec=rec, adj=adj, adj_exact=adj_exact, r=r, ratio_hat=ratio_hat)


def is_record(x):
    """各年が、それより前のすべての年を上回るか（2014年以降）"""
    prev = np.maximum.accumulate(x, axis=1)
    out = np.zeros_like(x, dtype=bool)
    out[:, 1:] = x[:, 1:] > prev[:, :-1]
    return out


def margin_record(x, m):
    prev = np.maximum.accumulate(x, axis=1)
    out = np.zeros_like(x, dtype=bool)
    out[:, 1:] = x[:, 1:] > prev[:, :-1] * (1 + m)
    return out


def summarize(d, after=slice(IC, None)):
    tr = is_record(d["true"])[:, after]
    res = {"true_records_per_world": float(tr.sum(1).mean())}
    for k in ["rec", "adj", "adj_exact"]:
        cl = is_record(d[k])[:, after]
        res[f"{k}_claims_per_world"] = float(cl.sum(1).mean())
        res[f"{k}_precision_pct"] = float((tr & cl).sum() / max(cl.sum(), 1) * 100)
        res[f"{k}_recall_pct"] = float((tr & cl).sum() / max(tr.sum(), 1) * 100)
    # 新しい数え方の年どうしだけで比べる
    newonly = d["rec"][:, IC:]
    cl = is_record(newonly)[:, 1:]
    trn = is_record(d["true"][:, IC:])[:, 1:]
    res["newonly_claims_per_world"] = float(cl.sum(1).mean())
    res["newonly_precision_vs_newonly_truth_pct"] = float((trn & cl).sum() / max(cl.sum(), 1) * 100)
    return res


def main():
    rng = np.random.default_rng(SEED)
    d = make(rng, N_WORLD, BASE)

    # 1) 年ごと（2021〜2026年）
    tr, cl_raw, cl_adj, cl_ex = is_record(d["true"]), is_record(d["rec"]), is_record(d["adj"]), is_record(d["adj_exact"])
    rows = []
    for j in range(IC, len(YEARS)):
        rows.append({"year": int(YEARS[j]),
                     "true_record_pct": round(tr[:, j].mean() * 100, 2),
                     "claimed_raw_pct": round(cl_raw[:, j].mean() * 100, 2),
                     "true_given_raw_pct": round(tr[cl_raw[:, j], j].mean() * 100, 2),
                     "claimed_adj_pct": round(cl_adj[:, j].mean() * 100, 2),
                     "true_given_adj_pct": round(tr[cl_adj[:, j], j].mean() * 100, 2),
                     "claimed_adj_exact_pct": round(cl_ex[:, j].mean() * 100, 2),
                     "true_given_adj_exact_pct": round(tr[cl_ex[:, j], j].mean() * 100, 2)})
    by_year = pd.DataFrame(rows)
    by_year.to_csv(RES / "by_year_base.csv", index=False)

    base = {k: round(v, 3) for k, v in summarize(d).items()}
    # 2021年の比の見込みのずれ
    base["adj_exact_minus_adj_pct"] = round(base["adj_exact_precision_pct"] - base["adj_precision_pct"], 2)
    base["ratio_hat_mean"] = round(float(d["ratio_hat"].mean()), 4)
    base["ratio_hat_p5"] = round(float(np.quantile(d["ratio_hat"], .05)), 4)
    base["ratio_hat_p95"] = round(float(np.quantile(d["ratio_hat"], .95)), 4)
    # 2021年に「過去最高」と言えた世界のうち、本当の伸び（2021÷それまでの最高）
    prevmax_true = np.max(d["true"][:, :IC], axis=1)
    gain = d["true"][:, IC] / prevmax_true - 1
    c21 = cl_raw[:, IC]
    base["raw_2021_claimed_pct"] = round(float(c21.mean() * 100), 2)
    base["raw_2021_claimed_true_gain_median_pct"] = round(float(np.median(gain[c21]) * 100), 2)
    base["raw_2021_claimed_true_gain_neg_share_pct"] = round(float((gain[c21] < 0).mean() * 100), 2)
    rec_gain = d["rec"][:, IC] / np.max(d["rec"][:, :IC], axis=1) - 1
    base["raw_2021_claimed_shown_gain_median_pct"] = round(float(np.median(rec_gain[c21]) * 100), 2)
    # 発表の伸びの幅で区切る（直したあとの数で、前の最高を何%上回ったら言うか）
    mg = []
    trA = tr[:, IC:]
    for m in [0.0, 0.02, 0.05, 0.10]:
        cl = margin_record(d["adj"], m)[:, IC:]
        mg.append({"margin_pct": m * 100, "claims_per_world": round(float(cl.sum(1).mean()), 3),
                   "precision_pct": round(float((trA & cl).sum() / max(cl.sum(), 1) * 100), 2),
                   "recall_pct": round(float((trA & cl).sum() / max(trA.sum(), 1) * 100), 2)})
    mg = pd.DataFrame(mg)
    mg.to_csv(RES / "by_margin_adj.csv", index=False)

    # 1つの世界（data）
    w = 0
    pd.DataFrame({"year": YEARS, "true": d["true"][w].round(0).astype(int), "old_method": d["old"][w].round(0).astype(int),
                  "new_method": d["new"][w].round(0).astype(int), "recorded": d["rec"][w].round(0).astype(int),
                  "adjusted": d["adj"][w].round(0).astype(int),
                  "method": np.where(YEARS < C, "旧い数え方", "新しい数え方")}).assign(
        new_method=lambda x: x.new_method.where(x.year >= C).astype("Int64"),
        old_method=lambda x: x.old_method.where(x.year <= C).astype("Int64")).to_csv(DATA / "series_world1.csv", index=False)
    world1 = {"ratio_hat": round(float(d["ratio_hat"][w]), 4),
              "raw_claim_years": [int(y) for y in YEARS[cl_raw[w] & (YEARS >= C)]],
              "true_record_years": [int(y) for y in YEARS[tr[w] & (YEARS >= C)]],
              "adj_claim_years": [int(y) for y in YEARS[cl_adj[w] & (YEARS >= C)]]}

    # 2) 確かめ：比 R × 年ごとの振れ sigma × 比の年ごとの振れ s_r（36通り、各2,000）
    grid = []
    gi = 0
    for R in [1.0, 1.1, 1.2, 1.35]:
        for sg in [0.04, 0.08, 0.15]:
            for sr in [0.02, 0.05, 0.10]:
                p = dict(BASE, R=R, sigma=sg, s_r=sr)
                dd = make(np.random.default_rng(SEED * 10 + gi), 2000, p); gi += 1
                s = summarize(dd)
                grid.append({"R": R, "sigma": sg, "s_r": sr, "true_records": round(s["true_records_per_world"], 3),
                             "raw_claims": round(s["rec_claims_per_world"], 3),
                             "raw_precision_pct": round(s["rec_precision_pct"], 2),
                             "adj_claims": round(s["adj_claims_per_world"], 3),
                             "adj_precision_pct": round(s["adj_precision_pct"], 2),
                             "adj_recall_pct": round(s["adj_recall_pct"], 2)})
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid_R_sigma_sr.csv", index=False)
    # 伸び g
    gg = []
    for k, g in enumerate([0.0, 0.01, 0.03]):
        dd = make(np.random.default_rng(SEED * 100 + k), 2000, dict(BASE, g=g))
        s = summarize(dd)
        gg.append({"g": g, **{kk: round(v, 3) for kk, v in s.items()}})
    gg = pd.DataFrame(gg)
    gg.to_csv(RES / "by_growth.csv", index=False)

    gR = gd[gd.R > 1.0]
    out = {"base": base, "by_year": by_year.to_dict("records"), "by_margin_adj": mg.to_dict("records"),
           "world1": world1,
           "grid_summary": {"raw_precision_R1_min": float(gd[gd.R == 1.0].raw_precision_pct.min()),
                            "raw_precision_R1_max": float(gd[gd.R == 1.0].raw_precision_pct.max()),
                            "raw_precision_Rgt1_min": float(gR.raw_precision_pct.min()),
                            "raw_precision_Rgt1_max": float(gR.raw_precision_pct.max()),
                            "adj_precision_min": float(gd.adj_precision_pct.min()),
                            "adj_precision_max": float(gd.adj_precision_pct.max()),
                            "adj_minus_raw_R1_min": round(float((gd[gd.R == 1.0].adj_precision_pct - gd[gd.R == 1.0].raw_precision_pct).min()), 2),
                            "adj_minus_raw_R1_max": round(float((gd[gd.R == 1.0].adj_precision_pct - gd[gd.R == 1.0].raw_precision_pct).max()), 2),
                            "adj_minus_raw_Rgt1_min": round(float((gR.adj_precision_pct - gR.raw_precision_pct).min()), 2),
                            "raw_claims_Rgt1_min": float(gR.raw_claims.min()), "raw_claims_Rgt1_max": float(gR.raw_claims.max()),
                            "true_records_min": float(gd.true_records.min()), "true_records_max": float(gd.true_records.max()),
                            "adj_precision_sr010_min": float(gd[gd.s_r == 0.10].adj_precision_pct.min()),
                            "adj_precision_sr010_max": float(gd[gd.s_r == 0.10].adj_precision_pct.max()),
                            "adj_precision_sr002_min": float(gd[gd.s_r == 0.02].adj_precision_pct.min()),
                            "adj_precision_sr002_max": float(gd[gd.s_r == 0.02].adj_precision_pct.max()),
                            "n": int(len(gd))},
           "grid": gd.to_dict("records"), "by_growth": gg.to_dict("records")}
    json.dump(out, open(RES / "a1004_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1つの世界の発表の数
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(YEARS, d["true"][w] / 1e4, "o-", color=INK, lw=1.4, ms=4, label="本当の来場者数")
    ax.plot(YEARS, d["rec"][w] / 1e4, "s-", color=ORANGE, lw=1.4, ms=4, label="発表した数（2021年から新しい数え方）")
    ax.plot(YEARS[:IC], d["adj"][w, :IC] / 1e4, "^--", color=BLUE, lw=1.2, ms=4, label="旧い年を2021年の比で直した数")
    for y in world1["raw_claim_years"]:
        j = int(np.where(YEARS == y)[0][0])
        ax.annotate("過去最高と発表", (y, d["rec"][w, j] / 1e4), xytext=(0, 10), textcoords="offset points",
                    ha="center", fontsize=8, color=ORANGE)
    ax.set_ylim(top=max(d["rec"][w].max(), d["adj"][w, :IC].max()) / 1e4 * 1.07)
    ax.axvline(C - 0.5, color=GRAY, lw=1, ls=":")
    ax.text(C - 0.4, ax.get_ylim()[0] + 0.1, "数え方を変えた", color=GRAY, fontsize=9)
    ax.set_ylabel("来場者数（万人、3日間の延べ）")
    ax.set_xticks(YEARS[::2])
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("数え方を変えた年から、発表の数が一段上がる（1つの例）")
    save(fig, "a1004_example.png", SRC)

    # 図2：年ごとの「過去最高」と発表した割合と、そのうち本当に過去最高だった割合
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(by_year))
    ax.bar(x - 0.27, by_year.true_record_pct, 0.27, color=INK, label="本当に過去最高だった")
    ax.bar(x, by_year.claimed_raw_pct, 0.27, color=ORANGE, label="発表した数で過去最高（そのまま）")
    ax.bar(x + 0.27, by_year.claimed_adj_pct, 0.27, color=BLUE, label="旧い年を2021年の比で直して過去最高")
    for i in range(len(by_year)):
        ax.text(i, by_year.claimed_raw_pct.iloc[i] + 1.5, f"{by_year.claimed_raw_pct.iloc[i]:.1f}%", ha="center",
                fontsize=8, color=ORANGE)
    ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in by_year.year])
    ax.set_ylabel("5,000通りの世界のうちの割合（%）")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("そのまま比べると、数え方を変えた年に「過去最高」が集まる")
    save(fig, "a1004_by_year.png", SRC)

    # 図3：確かめ（比 R ごとの、発表のうち本当に過去最高だった割合）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    sub = gd[gd.s_r == 0.05]
    cols = {0.04: LIGHT, 0.08: BLUE, 0.15: INK}
    for sg in [0.04, 0.08, 0.15]:
        ss = sub[sub.sigma == sg]
        ax.plot(ss.R, ss.raw_precision_pct, "o--", color=cols[sg], lw=1.2, label=f"そのまま（年の振れ{sg:.2f}）")
        ax.plot(ss.R, ss.adj_precision_pct, "s-", color=cols[sg], lw=1.6, label=f"2021年の比で直す（年の振れ{sg:.2f}）")
    ax.set_xticks([1.0, 1.1, 1.2, 1.35]); ax.set_xticklabels(["1.0倍", "1.1倍", "1.2倍", "1.35倍"])
    ax.set_xlabel("新しい数え方が、同じ来場を平均何倍に数えるか")
    ax.set_ylabel("「過去最高」のうち本当に過去最高（%）")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=7.8, ncol=2, loc="lower left")
    ax.set_title("新しい数え方の倍率が大きいほど、そのままの「過去最高」は外れる（2021〜2026年、比の振れ0.05）", fontsize=10.5)
    save(fig, "a1004_robustness.png", SRC)

    print(json.dumps(base, ensure_ascii=False, indent=1)); print(by_year.to_string()); print(mg.to_string())
    print(world1); print(gd.to_string()); print(gg.to_string())


if __name__ == "__main__":
    main()
