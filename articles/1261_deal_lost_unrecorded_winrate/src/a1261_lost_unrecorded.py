"""1261 失注した商談の一部が記録に残らないと、受注率はどれだけ高く出るのか？（架空のデータ）

架空の会社の法人向けの商談。商談ごとに、取れるか取れないか、取れない商談はどの段階で終わったか
（1 初回の打ち合わせのあと・2 提案のあと・3 見積もりのあと）、金額の大きさ（小さい・大きい）を作成者が置く。
取れた商談はすべて記録に残り、取れなかった商談は段階と金額の大きさで決めた確率で記録に残ると置いて、
記録から数えた受注率が本当の受注の確率からどれだけずれるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1261
SRC = "架空の会社の商談（作成者が乱数で作成、seed 1261）"
NQ, PER_Q = 12, 180          # 12期、1期に180件
CHANGE_Q = 6                 # 7期目（0から数えて6）から記録の決まりを変える
REPS = 200
P_SMALL, P_LARGE = 0.18, 0.22                 # 本当の受注の確率（金額の小さい商談・大きい商談）
STAGE_SHARE = (0.5, 0.3, 0.2)                 # 取れなかった商談が終わった段階の割合
REC_BASE = {"s1_small": 0.2, "s1_large": 0.7, "s2": 0.9, "s3": 1.0}   # 取れなかった商談が記録に残る確率
REC_AFTER = {"s1_small": 0.95, "s1_large": 0.95, "s2": 0.98, "s3": 1.0}


def make(rng, n, p_small=P_SMALL, p_large=P_LARGE, share=STAGE_SHARE, rec=REC_BASE):
    large = rng.random(n) < 0.5
    won = rng.random(n) < np.where(large, p_large, p_small)
    stage = rng.choice([1, 2, 3], size=n, p=share)
    stage = np.where(won, 4, stage)           # 4 は取れた商談
    pr = np.select([stage == 4, (stage == 1) & ~large, (stage == 1) & large, stage == 2, stage == 3],
                   [1.0, rec["s1_small"], rec["s1_large"], rec["s2"], rec["s3"]])
    recd = rng.random(n) < pr
    return large, won, stage, recd


def rates(large, won, stage, recd, mask=None):
    m = np.ones(len(won), bool) if mask is None else mask
    s2 = m & (stage >= 2)
    return dict(
        true=won[m].mean() * 100,
        obs=won[m & recd].mean() * 100,
        true_s2=won[s2].mean() * 100,
        obs_s2=won[s2 & recd].mean() * 100,
        lost_recorded=recd[m & ~won].mean() * 100,
    )


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 取れなかった商談がでたらめに残らないとき（式 p ÷ (p＋(1−p)(1−m)) と比べる）
    rows = []
    for p in [0.10, 0.20, 0.30]:
        for m in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
            obs = []
            for r in range(REPS):
                won = rng.random(NQ * PER_Q) < p
                recd = won | (rng.random(NQ * PER_Q) >= m)
                obs.append(won[recd].mean() * 100)
            rows.append(dict(true_pct=p * 100, missing_lost_pct=m * 100, observed=round(float(np.mean(obs)), 2),
                             formula=round(p / (p + (1 - p) * (1 - m)) * 100, 2)))
    rand = pd.DataFrame(rows)
    rand.to_csv(RES / "random_missing.csv", index=False)

    # 2) 基本の置き方：初回の打ち合わせのあとで終わった商談ほど残らない。金額の小さい商談はさらに残らない
    reps = []
    for r in range(REPS):
        large, won, stage, recd = make(rng, NQ * PER_Q)
        a = rates(large, won, stage, recd)
        a.update({f"{k}_small": v for k, v in rates(large, won, stage, recd, ~large).items()})
        a.update({f"{k}_large": v for k, v in rates(large, won, stage, recd, large).items()})
        a["small_gt_large_obs"] = float(a["obs_small"] > a["obs_large"])
        a["rep"] = r
        reps.append(a)
    base = pd.DataFrame(reps)
    base.round(3).to_csv(RES / "base_reps.csv", index=False)
    bm = base.mean().round(2)
    # 式の値（全体）
    pbar = (P_SMALL + P_LARGE) / 2
    lost_small, lost_large = 1 - P_SMALL, 1 - P_LARGE
    def rec_lost(s1):
        return STAGE_SHARE[0] * s1 + STAGE_SHARE[1] * REC_BASE["s2"] + STAGE_SHARE[2] * REC_BASE["s3"]
    f_small = P_SMALL / (P_SMALL + lost_small * rec_lost(REC_BASE["s1_small"])) * 100
    f_large = P_LARGE / (P_LARGE + lost_large * rec_lost(REC_BASE["s1_large"])) * 100
    f_all = pbar / (pbar + (lost_small * rec_lost(REC_BASE["s1_small"]) + lost_large * rec_lost(REC_BASE["s1_large"])) / 2) * 100
    by_size = pd.DataFrame([
        dict(size="小さい商談", true=bm.true_small, observed=bm.obs_small, formula=round(f_small, 2),
             true_from_stage2=bm.true_s2_small, observed_from_stage2=bm.obs_s2_small, lost_recorded=bm.lost_recorded_small),
        dict(size="大きい商談", true=bm.true_large, observed=bm.obs_large, formula=round(f_large, 2),
             true_from_stage2=bm.true_s2_large, observed_from_stage2=bm.obs_s2_large, lost_recorded=bm.lost_recorded_large),
        dict(size="全体", true=bm.true, observed=bm.obs, formula=round(f_all, 2),
             true_from_stage2=bm.true_s2, observed_from_stage2=bm.obs_s2, lost_recorded=bm.lost_recorded),
    ])
    by_size.to_csv(RES / "base_by_size.csv", index=False)

    # 3) 7期目から記録の決まりを変える（初回の打ち合わせのあとで終わった商談も95%残す）
    qrows = []
    for r in range(REPS):
        for q in range(NQ):
            rec = REC_BASE if q < CHANGE_Q else REC_AFTER
            large, won, stage, recd = make(rng, PER_Q, rec=rec)
            a = rates(large, won, stage, recd)
            a.update(q=q + 1, rep=r, recorded_deals=int(recd.sum()))
            qrows.append(a)
    qd = pd.DataFrame(qrows)
    g = qd.groupby("q")
    qs = g[["true", "obs", "true_s2", "obs_s2", "recorded_deals"]].mean()
    for c in ["obs", "obs_s2"]:
        qs[c + "_p10"] = g[c].quantile(0.1)
        qs[c + "_p90"] = g[c].quantile(0.9)
    qs = qs.reset_index().round(2)
    qs.to_csv(RES / "rule_change_by_quarter.csv", index=False)
    before = qd[qd.q <= CHANGE_Q]; after = qd[qd.q > CHANGE_Q]
    # 6期目と7期目の差が「5ポイント以上下がった」回の割合
    pv = qd.pivot(index="rep", columns="q", values="obs")
    pv2 = qd.pivot(index="rep", columns="q", values="obs_s2")
    drop_all = float(((pv[CHANGE_Q] - pv[CHANGE_Q + 1]) >= 5).mean() * 100)
    drop_s2 = float(((pv2[CHANGE_Q] - pv2[CHANGE_Q + 1]) >= 5).mean() * 100)
    # 決まりを変えない期どうし（5期→6期）で5ポイント以上下がった割合（比べる相手）
    drop_all_ref = float(((pv[CHANGE_Q - 1] - pv[CHANGE_Q]) >= 5).mean() * 100)
    drop_s2_ref = float(((pv2[CHANGE_Q - 1] - pv2[CHANGE_Q]) >= 5).mean() * 100)

    # 4) 確かめ：本当の受注の確率 × 初回の打ち合わせのあとで終わる割合 × そこでの残りやすさ（27通り）
    grid = []
    for p in [0.10, 0.20, 0.30]:
        for sh1 in [0.3, 0.5, 0.7]:
            share = (sh1, (1 - sh1) * 0.6, (1 - sh1) * 0.4)
            for r1 in [0.2, 0.45, 0.7]:
                rec = {"s1_small": r1, "s1_large": r1, "s2": 0.9, "s3": 1.0}
                large, won, stage, recd = make(rng, 200000, p, p, share, rec)
                a = rates(large, won, stage, recd)
                miss = 1 - (share[0] * r1 + share[1] * 0.9 + share[2] * 1.0)
                grid.append(dict(true_pct=p * 100, stage1_share_pct=sh1 * 100, stage1_recorded_pct=r1 * 100,
                                 true=round(a["true"], 2), observed=round(a["obs"], 2),
                                 formula=round(p / (p + (1 - p) * (1 - miss)) * 100, 2),
                                 ratio=round(a["obs"] / a["true"], 3),
                                 true_from_stage2=round(a["true_s2"], 2), observed_from_stage2=round(a["obs_s2"], 2),
                                 gap_from_stage2=round(a["obs_s2"] - a["true_s2"], 2), gap_all=round(a["obs"] - a["true"], 2)))
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    # データ：基本の置き方の1回分
    r1 = np.random.default_rng(SEED + 1)
    large, won, stage, recd = make(r1, NQ * PER_Q)
    pd.DataFrame({"deal_id": np.arange(1, len(won) + 1), "size": np.where(large, "large", "small"),
                  "won": won.astype(int), "end_stage": stage, "recorded": recd.astype(int)}).to_csv(
        DATA / "deals_one_rep.csv", index=False)

    out = {
        "settings": {"quarters": NQ, "deals_per_quarter": PER_Q, "reps": REPS, "win_prob_small": P_SMALL,
                     "win_prob_large": P_LARGE, "lost_stage_share": STAGE_SHARE, "lost_recorded_prob": REC_BASE,
                     "lost_recorded_prob_after_change": REC_AFTER, "change_from_quarter": CHANGE_Q + 1, "seed": SEED},
        "random_missing_max_gap_to_formula": round(float((rand.observed - rand.formula).abs().max()), 2),
        "random_missing_p20": rand[rand.true_pct == 20].to_dict("records"),
        "base_by_size": by_size.to_dict("records"),
        "base_small_gt_large_obs_pct": round(float(base.small_gt_large_obs.mean() * 100), 2),
        "base_small_gt_large_true_pct": round(float((base.true_small > base.true_large).mean() * 100), 2),
        "base_obs_p10_p90": [round(float(base.obs.quantile(0.1)), 2), round(float(base.obs.quantile(0.9)), 2)],
        "rule_change": {
            "before_q1_6": {k: round(float(before[k].mean()), 2) for k in ["true", "obs", "true_s2", "obs_s2"]},
            "after_q7_12": {k: round(float(after[k].mean()), 2) for k in ["true", "obs", "true_s2", "obs_s2"]},
            "recorded_deals_before": round(float(before.recorded_deals.mean()), 2),
            "recorded_deals_after": round(float(after.recorded_deals.mean()), 2),
            "drop5_q6_to_q7_all_pct": round(drop_all, 2), "drop5_q6_to_q7_from_stage2_pct": round(drop_s2, 2),
            "drop5_q5_to_q6_all_pct": round(drop_all_ref, 2), "drop5_q5_to_q6_from_stage2_pct": round(drop_s2_ref, 2),
        },
        "base_gap_from_stage2_by_size": {r["size"]: round(r["observed_from_stage2"] - r["true_from_stage2"], 2) for r in by_size.to_dict("records")},
        "rule_change_from_stage2_shift": round(float(before.obs_s2.mean() - after.obs_s2.mean()), 2),
        "rule_change_from_stage2_quarter_p10_p90_range": [float(qs.obs_s2_p10.min()), float(qs.obs_s2_p90.max())],
        "rule_change_all_quarter_p10_p90_range": [float(qs.obs_p10.min()), float(qs.obs_p90.max())],
        "grid_range": {k: [float(grid[k].min()), float(grid[k].max())] for k in
                       ["observed", "ratio", "gap_all", "gap_from_stage2", "true_from_stage2"]},
        "grid_max_gap_to_formula": round(float((grid.observed - grid.formula).abs().max()), 2),
    }

    # 図1：でたらめに残らないとき（式どおり）
    fig, ax = plt.subplots(figsize=(7, 4))
    for p, col in zip([10, 20, 30], [GREEN, BLUE, ORANGE]):
        d = rand[rand.true_pct == p]
        ax.plot(d.missing_lost_pct, d.observed, marker="o", color=col, label=f"本当の受注の確率 {p}%")
        ax.axhline(p, color=col, lw=0.8, ls=":")
    ax.set_xlabel("取れなかった商談のうち、記録に残らない割合（%）")
    ax.set_ylabel("記録から数えた受注率（%）")
    ax.set_ylim(0, 55); ax.set_xticks([0, 10, 20, 30, 40, 50, 60])
    ax.set_title("取れなかった商談が残らないぶん、受注率は高く出る（式どおり）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1261_random_missing.png", SRC + "。点線は本当の受注の確率。取れなかった商談をでたらめに抜いた。200回の平均", y=-0.03)

    # 図2：金額の大きさごと（基本の置き方）
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(3); w = 0.26
    lab = by_size["size"].tolist()
    b1 = ax.bar(x - w, by_size["true"], w, color=GRAY, label="本当")
    b2 = ax.bar(x, by_size["observed"], w, color=ORANGE, label="記録から数えた受注率")
    b3 = ax.bar(x + w, by_size["observed_from_stage2"], w, color=BLUE, label="記録から数えた、提案まで進んだ商談の受注率")
    for bars in (b1, b2, b3):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{b.get_height():.2f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(lab)
    ax.set_ylim(0, 45); ax.set_ylabel("受注率（%）")
    ax.set_title("記録から数えると、金額の小さい商談のほうが高く見えた（200回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=1)
    save(fig, "a1261_by_size.png", SRC + "。本当は小さい商談18%・大きい商談22%。\n初回の打ち合わせのあとで終わった商談は、小さい商談20%・大きい商談70%だけ残る。200回の平均", y=-0.03)

    # 図3：記録の決まりを変えた期
    fig, ax = plt.subplots(figsize=(7.2, 4))
    ax.plot(qs.q, qs["true"], color=GRAY, lw=2.5, label="本当の受注の確率（全体）")
    ax.plot(qs.q, qs["obs"], color=ORANGE, marker="o", label="記録から数えた受注率（全体）")
    ax.fill_between(qs.q, qs["obs_p10"], qs["obs_p90"], color=ORANGE, alpha=0.15, lw=0)
    ax.plot(qs.q, qs["true_s2"], color=GRAY, lw=2.5, ls="--", label="本当（提案まで進んだ商談）")
    ax.plot(qs.q, qs["obs_s2"], color=BLUE, marker="s", label="記録から数えた（提案まで進んだ商談）")
    ax.fill_between(qs.q, qs["obs_s2_p10"], qs["obs_s2_p90"], color=LIGHT, alpha=0.4, lw=0)
    ax.axvline(CHANGE_Q + 0.5, color=INK, lw=0.8, ls=":")
    ax.set_xticks(range(1, NQ + 1)); ax.set_xlabel("期"); ax.set_ylabel("受注率（%）"); ax.set_ylim(0, 50)
    ax.set_title("7期目から失注も残すようにすると、受注率は下がって見えた")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    save(fig, "a1261_rule_change.png", SRC + "。本当の受注の確率は変えていない。200回の平均（帯は10〜90%の範囲）", y=-0.13)

    json.dump(out, open(RES / "a1261_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(qs.to_string()); print(grid.to_string())
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
