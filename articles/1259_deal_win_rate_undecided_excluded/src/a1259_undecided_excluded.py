"""1259 「確度50%」と付けた商談のうち実際に取れた割合は、まだ決まっていない商談を除いて数えるとどう見えるのか？（架空のデータ）

架空の会社の法人向けの商談。「確度50%」と付けた商談が、数える日の前の一定の期間に毎日同じ割合で始まる。
商談ごとに最後に取れるか（確率 p）を決め、取れる商談・取れない商談それぞれに、決まるまでの日数を作成者が置いた分布から引く。
数える日までに決まった商談だけで受注の割合を数えると、本当の割合 p とどれだけずれるかを見る。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1259
SRC = "架空の会社の商談の記録（作成者が乱数で作成、seed 1259）"
BASE = {"p": 0.5, "win_median_days": 40, "loss_median_days": 100, "log_sd": 0.6, "window_days": 360,
        "n_deals": 600, "age_cut_days": 120}
REPS = 2000


def simulate(rng, p, mw, ml, sd, W, n, reps):
    start_age = rng.random((reps, n)) * W            # 数える日から見て何日前に始まったか
    win = rng.random((reps, n)) < p
    med = np.where(win, mw, ml)
    T = med * np.exp(sd * rng.standard_normal((reps, n)))
    decided = T <= start_age
    return start_age, win, decided


def measures(start_age, win, decided, age_cut):
    won_d = (win & decided).sum(axis=1)
    lost_d = (~win & decided).sum(axis=1)
    old = start_age >= age_cut
    won_o = (win & decided & old).sum(axis=1)
    lost_o = (~win & decided & old).sum(axis=1)
    n = win.shape[1]
    return {
        "m1_decided_only": won_d / np.maximum(won_d + lost_d, 1),
        "m2_undecided_as_loss": won_d / n,
        "m3_old_decided_only": won_o / np.maximum(won_o + lost_o, 1),
        "m4_final": win.mean(axis=1),
        "undecided_share": 1 - decided.mean(axis=1),
        "old_undecided_share": 1 - (decided & old).sum(axis=1) / np.maximum(old.sum(axis=1), 1),
    }


def cdf_logn(t, med, sd):
    if t <= 0:
        return 0.0
    return 0.5 * (1 + math.erf(math.log(t / med) / (sd * math.sqrt(2))))


def formula_m1(p, mw, ml, sd, W, lo=0.0):
    """数える日までに決まった商談だけの受注の割合（年齢が lo〜W に一様）の式の値"""
    ages = np.linspace(lo, W, 4001)
    fw = np.array([cdf_logn(a, mw, sd) for a in ages])
    fl = np.array([cdf_logn(a, ml, sd) for a in ages])
    return float(p * fw.mean() / (p * fw.mean() + (1 - p) * fl.mean()))


def summ(x):
    return {"mean": round(float(np.mean(x)), 4), "p10": round(float(np.quantile(x, 0.1)), 4),
            "p90": round(float(np.quantile(x, 0.9)), 4)}


def main():
    t0 = time.time()
    b = BASE
    # 1) 基本：600件×2,000回
    sa, win, dec = simulate(np.random.default_rng(SEED), b["p"], b["win_median_days"], b["loss_median_days"], b["log_sd"],
                            b["window_days"], b["n_deals"], REPS)
    m = measures(sa, win, dec, b["age_cut_days"])
    base = {k: summ(v) for k, v in m.items()}
    base["share_runs_m1_ge_0_6"] = round(float((m["m1_decided_only"] >= 0.6).mean()), 4)
    base["formula_m1"] = round(formula_m1(b["p"], b["win_median_days"], b["loss_median_days"], b["log_sd"], b["window_days"]), 4)
    base["formula_m3"] = round(formula_m1(b["p"], b["win_median_days"], b["loss_median_days"], b["log_sd"],
                                          b["window_days"], lo=b["age_cut_days"]), 4)
    # 1回分の記録
    rec = pd.DataFrame({"deal_id": np.arange(1, b["n_deals"] + 1), "days_since_start": np.floor(sa[0]).astype(int),
                        "final_won": win[0].astype(int), "decided_by_count_day": dec[0].astype(int)})
    rec["status_on_count_day"] = np.where(rec.decided_by_count_day == 0, "未決定", np.where(rec.final_won == 1, "受注", "失注"))
    rec.to_csv(DATA / "deals_one_run.csv", index=False)

    # 2) 始まった月ごと（30日ごと）に、決まったものだけの受注の割合（2,000回をまとめて）
    rows = []
    for k in range(12):
        sel = (sa >= k * 30) & (sa < (k + 1) * 30)
        d = sel & dec
        rows.append({"days_since_start_from": k * 30, "days_since_start_to": (k + 1) * 30,
                     "decided_only_win_rate": round(float((d & win).sum() / d.sum()), 4),
                     "undecided_share": round(float(1 - d.sum() / sel.sum()), 4),
                     "final_win_rate": round(float((sel & win).sum() / sel.sum()), 4)})
    by_age = pd.DataFrame(rows)
    by_age.to_csv(RES / "by_start_age.csv", index=False)

    # 3) 場面：決まる速さが同じ／取れない商談のほうが早く決まる
    scen = {}
    for name, mw, ml in [("base_loss_slower", 40, 100), ("same_speed", 40, 40), ("loss_faster", 40, 16)]:
        r = np.random.default_rng(SEED + len(scen) + 1)
        mm = measures(*simulate(r, b["p"], mw, ml, b["log_sd"], b["window_days"], b["n_deals"], REPS), b["age_cut_days"])
        scen[name] = {"win_median_days": mw, "loss_median_days": ml, **{k: summ(v)["mean"] for k, v in mm.items()},
                      "m1_p10": summ(mm["m1_decided_only"])["p10"], "m1_p90": summ(mm["m1_decided_only"])["p90"],
                      "formula_m1": round(formula_m1(b["p"], mw, ml, b["log_sd"], b["window_days"]), 4)}
    pd.DataFrame([{"scenario": k, **v} for k, v in scen.items()]).to_csv(RES / "scenarios.csv", index=False)

    # 4) 確かめ：速さの比3通り×始まる期間3通り×本当の割合3通り＝27通り（各600件×400回）
    grid = []
    gi = 0
    for ml in [16, 40, 100]:
        for W in [180, 360, 720]:
            for p in [0.3, 0.5, 0.7]:
                r = np.random.default_rng(SEED * 100 + gi)
                gi += 1
                mm = measures(*simulate(r, p, 40, ml, b["log_sd"], W, b["n_deals"], 400), b["age_cut_days"])
                grid.append({"loss_median_days": ml, "win_median_days": 40, "window_days": W, "p": p,
                             **{k: round(float(np.mean(v)), 4) for k, v in mm.items()},
                             "formula_m1": round(formula_m1(p, 40, ml, b["log_sd"], W), 4)})
    grid = pd.DataFrame(grid)
    for c in ["m1_decided_only", "m2_undecided_as_loss", "m3_old_decided_only"]:
        grid[c.split("_")[0] + "_minus_p"] = (grid[c] - grid.p).round(4)
    grid.to_csv(RES / "grid.csv", index=False)

    def rng_of(df, c):
        return [float(df[c].min()), float(df[c].max())]
    main_json = {
        "base_setting": {**b, "reps": REPS},
        "base": base,
        "scenarios": scen,
        "grid_n": int(len(grid)),
        "grid_m1_minus_p_by_loss_median": {int(k): rng_of(g, "m1_minus_p") for k, g in grid.groupby("loss_median_days")},
        "grid_m2_minus_p_range": rng_of(grid, "m2_minus_p"),
        "grid_m3_minus_p_by_loss_median": {int(k): rng_of(g, "m3_minus_p") for k, g in grid.groupby("loss_median_days")},
        "grid_m1_abs_gt_m3_abs_n": int((grid.m1_minus_p.abs() > grid.m3_minus_p.abs()).sum()),
        "grid_m1_abs_gt_m3_abs_n_of_unequal": int((grid[grid.loss_median_days != 40].m1_minus_p.abs() >
                                                    grid[grid.loss_median_days != 40].m3_minus_p.abs()).sum()),
        "grid_n_unequal": int((grid.loss_median_days != 40).sum()),
        "grid_max_abs_m1_minus_formula": round(float((grid.m1_decided_only - grid.formula_m1).abs().max()), 4),
        "grid_same_speed_max_abs_m1_minus_p": round(float(grid[grid.loss_median_days == 40].m1_minus_p.abs().max()), 4),
        "grid_m1_minus_p_W720_ml100": grid[(grid.window_days == 720) & (grid.loss_median_days == 100)].set_index("p").m1_minus_p.to_dict(),
        "grid_m1_minus_p_W180_ml100": grid[(grid.window_days == 180) & (grid.loss_median_days == 100)].set_index("p").m1_minus_p.to_dict(),
        "by_age_first_month": rows[0], "by_age_last_month": rows[-1],
    }
    with open(RES / "a1259_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：4つの数え方（基本）
    fig, ax = plt.subplots(figsize=(7.5, 4))
    keys = ["m1_decided_only", "m2_undecided_as_loss", "m3_old_decided_only", "m4_final"]
    labs = ["① 決まった商談だけ", "② 決まっていないものを\n取れなかったと数える", "③ 始めて120日以上の\n決まった商談だけ", "④ 最後まで待った\n本当の割合"]
    cols = [ORANGE, GRAY, BLUE, INK]
    for i, (k, c) in enumerate(zip(keys, cols)):
        s = base[k]
        ax.bar(i, s["mean"] * 100, color=c, width=0.6)
        ax.errorbar(i, s["mean"] * 100, yerr=[[(s["mean"] - s["p10"]) * 100], [(s["p90"] - s["mean"]) * 100]], color=INK,
                    capsize=4, lw=1)
        ax.text(i, s["mean"] * 50, f"{s['mean'] * 100:.2f}%", ha="center", va="center", fontsize=10, color="white")
    ax.axhline(50, color=INK, lw=0.8, ls="--")
    ax.set_xticks(range(4))
    ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_ylabel("「確度50%」の商談の受注の割合（%）")
    ax.set_title("取れない商談ほど決まるのが遅いと置くと、決まったものだけでは高く出た", fontsize=12)
    save(fig, "a1259_measures.png", SRC + "。600件×2,000回の平均、線は10〜90%の範囲。決まるまでの日数の中央値は取れる40日・取れない100日")

    # 図2：始まってからの日数ごと
    fig, ax = plt.subplots(figsize=(8, 4.2))
    mid = (by_age.days_since_start_from + 15)
    ax.plot(mid, by_age.decided_only_win_rate * 100, "o-", color=ORANGE, label="決まった商談だけの受注の割合")
    ax.plot(mid, by_age.undecided_share * 100, "s--", color=GRAY, label="まだ決まっていない商談の割合")
    ax.axhline(50, color=INK, lw=0.8, ls=":")
    ax.text(200, 48, "本当の割合 50%", fontsize=8.5, ha="left", va="top")
    ax.set_xlim(0, 365)
    ax.set_ylim(0, 105)
    ax.set_xlabel("数える日から見て、商談が始まったのは何日前か（30日ごと）")
    ax.set_ylabel("%")
    ax.set_title("始まって間もない商談ほど、決まったものは受注に偏る", fontsize=12)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a1259_by_age.png", SRC + "。基本の置き方、2,000回をまとめた値")

    # 図3：27通りで ① と ③ のずれ
    fig, axs = plt.subplots(1, 3, figsize=(11, 4), sharey=True)
    for ax, ml, ttl in zip(axs, [16, 40, 100], ["取れない商談が早く決まる\n（中央値16日）", "同じ速さ\n（40日）", "取れない商談が遅く決まる\n（100日）"]):
        g = grid[grid.loss_median_days == ml]
        for W, c, mk in [(180, ORANGE, "o"), (360, BLUE, "s"), (720, GREEN, "^")]:
            gg = g[g.window_days == W]
            ax.plot(gg.p * 100, gg.m1_minus_p * 100, mk + "-", color=c, label=f"① 過去{W}日に始まった商談")
            ax.plot(gg.p * 100, gg.m3_minus_p * 100, mk + ":", color=c, alpha=0.6, label=f"③ 同じ（始めて120日以上だけ）")
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_xticks([30, 50, 70])
        ax.set_xlabel("本当の受注の割合（%）")
        ax.set_title(ttl, fontsize=10.5)
    axs[0].set_ylabel("数えた割合 − 本当の割合（ポイント）")
    axs[2].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.suptitle("決まった商談だけで数えたずれ（27通り、取れる商談の決まるまでの中央値は40日）", y=1.03)
    save(fig, "a1259_grid.png", SRC + "。各600件×400回の平均")
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
