"""886 稼働時間の「実働」と「拘束」で、時給はどう変わるのか？（架空のデータ）

架空の副業の人が受けている、時間帯を決めて対応する架空の継続案件。決まった時間帯（拘束）の中で、
問い合わせや依頼がでたらめな時刻に届き、届いた順に片付ける（実働）。依頼のない待ちの時間のうち、
「戻る手間 g 分」を引いて残る分だけを、ほかの仕事に使えると置く。
時給は3通りで割る：実働で割る・拘束で割る・拘束からほかの仕事に使えた時間を引いて割る（実質）。
時給は円ではなく、実働で割った時給の基準を100とする指数で表す。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 886
SRC = "架空の継続案件（作成者が乱数で作成、seed 886）"
DAY_MIN = 240            # 1日の拘束（4時間）
G_BASE = 15              # ほかの仕事に入って戻る手間（分）


def simulate_case(rng, days, lam_h, m_min, g=G_BASE, burst=1.0):
    """1つの案件の1か月。lam_h：1時間あたりの依頼の数、m_min：1件の平均の処理時間（分）。
    burst>1 のときは、依頼が平均 burst 件ずつまとまって届く（まとまりの数を 1/burst にして件数の平均はそろえる）。
    返り値：実働（分）・拘束（分）・ほかの仕事に使えた時間（分）・待ちの時間（分）"""
    active = usable = idle = bound = 0.0
    for _ in range(days):
        n_grp = rng.poisson(lam_h * DAY_MIN / 60 / burst)
        t_grp = np.sort(rng.uniform(0, DAY_MIN, n_grp))
        if burst > 1:
            size = rng.geometric(1 / burst, n_grp)
            arr = np.repeat(t_grp, size)
        else:
            arr = t_grp
        svc = rng.exponential(m_min, len(arr))
        t = 0.0
        for a, s in zip(arr, svc):
            if a > t:
                gap = a - t
                idle += gap; usable += max(gap - g, 0.0)
                t = a
            t += s
        if t < DAY_MIN:
            gap = DAY_MIN - t
            idle += gap; usable += max(gap - g, 0.0)
        active += svc.sum()
        bound += max(t, DAY_MIN)          # 時間内に終わらない分は延長して片付ける
    return active, bound, usable, idle


def rates(reward, active, bound, usable):
    return reward / (active / 60), reward / (bound / 60), reward / ((bound - usable) / 60)


def portfolio(rng, n=12, g=G_BASE, burst=1.0):
    rows = []
    for j in range(n):
        days = int(rng.integers(5, 21))                     # 月に5〜20日
        s = rng.uniform(0.2, 0.85)                          # 拘束のうち依頼の処理にかかる時間の割合（平均）
        m = float(np.exp(rng.uniform(np.log(5), np.log(60))))  # 1件の平均の処理時間（5〜60分）
        lam = s * 60 / m
        a = 100 * np.exp(rng.normal(0, 0.3))                # 実働で割った時給の置き方
        reward = a * s * days * DAY_MIN / 60                # 報酬は月ごとに決まっている（作成者の置き方）
        act, bnd, use, idle = simulate_case(rng, days, lam, m, g, burst)
        r_act, r_bnd, r_eff = rates(reward, act, bnd, use)
        rows.append({"case": chr(65 + j), "days": days, "share_planned": s, "mean_task_min": m, "req_per_hour": lam,
                     "active_h": act / 60, "bound_h": bnd / 60, "usable_h": use / 60, "idle_h": idle / 60,
                     "reward": reward, "hourly_active": r_act, "hourly_bound": r_bnd, "hourly_effective": r_eff})
    return pd.DataFrame(rows)


def rank_stats(df):
    ra, rb, re = (df[c].rank(ascending=False) for c in ["hourly_active", "hourly_bound", "hourly_effective"])
    return {"spearman_active_bound": float(ra.corr(rb)), "spearman_active_eff": float(ra.corr(re)),
            "spearman_bound_eff": float(rb.corr(re)),
            "top_same_active_bound": float(ra.idxmin() == rb.idxmin()),
            "top_same_active_eff": float(ra.idxmin() == re.idxmin()),
            "top_same_bound_eff": float(rb.idxmin() == re.idxmin()),
            "mean_abs_rank_move_active_to_eff": float((ra - re).abs().mean())}


def r3(x):
    if isinstance(x, dict):
        return {k: r3(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r3(v) for v in x]
    return round(float(x), 3)


def main():
    rng = np.random.default_rng(SEED)
    # 1) 12件の案件の1回分
    one = portfolio(rng)
    one.round(4).to_csv(DATA / "cases_one_month.csv", index=False)
    one_rank = rank_stats(one)
    tab = one[["case", "share_planned", "mean_task_min", "req_per_hour", "hourly_active", "hourly_bound", "hourly_effective"]].copy()
    tab["active_share"] = one.active_h / one.bound_h
    tab["usable_share_of_idle"] = one.usable_h / one.idle_h
    for c in ["hourly_active", "hourly_bound", "hourly_effective"]:
        tab["rank_" + c.split("_")[1]] = one[c].rank(ascending=False).astype(int)
    tab.round(3).to_csv(RES / "cases_one_month_rates.csv", index=False)

    # 2) 案件12件の組を作り直して300回：順位の入れ替わり（戻る手間 g と依頼のまとまり方を変える）
    rk = {}
    for g in [5, 15, 30]:
        for burst in [1.0, 3.0]:
            st = [rank_stats(portfolio(np.random.default_rng(SEED * 100 + i + g * 1000 + int(burst) * 7), g=g, burst=burst))
                  for i in range(300)]
            rk[f"g{g}_burst{burst:g}"] = {k: float(np.mean([s[k] for s in st])) for k in st[0]}
    pd.DataFrame(rk).T.round(3).to_csv(RES / "rank_change_300portfolios.csv")

    # 3) 実働の割合を50%にそろえ、依頼の細かさだけを変える（1日4時間×20日、各40回）
    rows = []
    for g in [5, 15, 30]:
        for burst in [1.0, 3.0]:
            for m in [60, 30, 15, 7.5, 3.75]:
                lam = 0.5 * 60 / m
                res = [simulate_case(np.random.default_rng(SEED * 10 + i + int(m * 100) + g * 100000 + int(burst) * 7), 20, lam, m, g, burst)
                       for i in range(40)]
                act, bnd, use, idle = np.array(res).sum(0)
                reward = 100 * act / 60                              # 実働で割った時給がちょうど100になる報酬
                r_act, r_bnd, r_eff = rates(reward, act, bnd, use)
                rows.append({"g": g, "burst": burst, "mean_task_min": m, "req_per_hour": lam,
                             "active_share": act / bnd, "usable_share_of_idle": use / idle,
                             "hourly_active": r_act, "hourly_bound": r_bnd, "hourly_effective": r_eff})
    fine = pd.DataFrame(rows).round(3)
    fine.to_csv(RES / "fineness_share50.csv", index=False)
    base_f = fine[(fine.g == 15) & (fine.burst == 1)]

    out = {"assumptions": {"day_min": DAY_MIN, "g_base": G_BASE, "cases": 12, "days": "5〜20",
                           "share_planned": "0.2〜0.85", "mean_task_min": "5〜60（対数で一様）",
                           "hourly_active_sd_log": 0.3},
           "one_month_rank": r3(one_rank),
           "one_month_bound_over_active": r3([float((one.hourly_bound / one.hourly_active).min()),
                                              float((one.hourly_bound / one.hourly_active).max())]),
           "rank_change_300": r3(rk),
           "spearman_active_bound_mean_of_6": r3(float(np.mean([rk[k]["spearman_active_bound"] for k in rk]))),
           "share50_base_g15": r3(base_f[["mean_task_min", "req_per_hour", "usable_share_of_idle", "hourly_bound",
                                          "hourly_effective"]].to_dict("records")),
           "share50_eff_range_all": r3([float(fine.hourly_effective.min()), float(fine.hourly_effective.max())]),
           "share50_bound_range_all": r3([float(fine.hourly_bound.min()), float(fine.hourly_bound.max())]),
           "share50_eff_over_bound_range_all": r3([float((fine.hourly_effective / fine.hourly_bound).min()),
                                                   float((fine.hourly_effective / fine.hourly_bound).max())]),
           "share50_active_share_range_all": r3([float(fine.active_share.min()), float(fine.active_share.max())])}
    json.dump(out, open(RES / "a886_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：12件の3つの時給の順位
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    xs = [0, 1, 2]
    for _, r in tab.iterrows():
        ys = [r.rank_active, r.rank_bound, r.rank_effective]
        top = r.rank_active <= 3
        ax.plot(xs, ys, color=BLUE if top else GRAY, lw=2 if top else 1, alpha=1 if top else .7, marker="o", ms=4)
        ax.text(-0.06, ys[0], f"{r.case}", ha="right", va="center", fontsize=9)
        ax.text(2.06, ys[2], f"{r.case}", ha="left", va="center", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels(["実働で割る", "拘束で割る", "実質（使えない待ちも入れる）"])
    ax.set_ylim(12.6, 0.4); ax.set_yticks(range(1, 13)); ax.set_ylabel("時給の順位（1が上）")
    ax.set_xlim(-0.3, 2.3)
    f1 = tab.loc[tab.rank_active == 1].iloc[0]
    ax.set_title(f"実働で1位の{f1.case}は、拘束で割ると{f1.rank_bound}位、実質では{f1.rank_effective}位（架空の案件12件）")
    save(fig, "a886_rank_slope.png", SRC)

    # 図2：実働の割合50%で、依頼の細かさと3つの時給
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    lab = [f"{m:g}分×{l:g}件" for m, l in zip(base_f.mean_task_min, base_f.req_per_hour)]
    x = np.arange(len(lab))
    ax.axhline(100, color=GRAY, lw=1, ls="--"); ax.text(len(lab) - 0.6, 101.5, "実働で割る（100）", color=GRAY, fontsize=8.5, ha="right")
    ax.plot(x, base_f.hourly_bound, color=ORANGE, marker="o", lw=2, label="拘束で割る")
    ax.plot(x, base_f.hourly_effective, color=BLUE, marker="o", lw=2, label="実質（戻る手間15分と置く）")
    sub3 = fine[(fine.g == 15) & (fine.burst == 3)]
    ax.plot(x, sub3.hourly_effective, color=LIGHT, marker="o", lw=2, ls="--", label="実質（戻る手間15分・依頼がまとまって届く）")
    ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=9)
    ax.set_xlabel("1件の平均の処理時間 × 1時間あたりの依頼の数（どれも実働の割合は50%）")
    ax.set_ylabel("時給（実働で割った時給＝100）"); ax.set_ylim(0, 112)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("依頼が細かく届くほど、待ちはほかの仕事に使えず、実質は拘束に近づく")
    save(fig, "a886_fineness.png", SRC)

    # 図3：戻る手間 g と依頼の届き方で、順位の入れ替わり（実働→実質）
    keys = list(rk.keys())
    vals = [rk[k]["spearman_active_eff"] for k in keys]
    labs = [f"戻る手間{k.split('_')[0][1:]}分・{'ばらばら' if k.endswith('burst1') else 'まとまって'}" for k in keys]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.barh(labs[::-1], vals[::-1], color=BLUE, height=0.6)
    ax.barh(["（参考）実働と拘束（6通りの平均）"], [np.mean([rk[k]["spearman_active_bound"] for k in keys])], color=ORANGE, height=0.6)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=9)
    vb = np.mean([rk[k]["spearman_active_bound"] for k in keys])
    ax.text(vb + 0.01, len(vals), f"{vb:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, 1); ax.set_xlabel("実働で割った順位と、実質の順位の順位相関（1なら同じ順位、300組の平均）")
    ax.set_title("実質の順位は拘束より実働に近いが、戻る手間が長いほど離れる（12件の組×300回）", fontsize=11.5)
    save(fig, "a886_rank_corr.png", SRC, y=-0.06)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(tab.round(2).to_string())


if __name__ == "__main__":
    main()
