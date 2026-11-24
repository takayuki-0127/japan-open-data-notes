"""1266 新しい取引先と前からの取引先をまぜた受注率は、まざる割合が変わるとどう動くのか？（架空のデータ）

架空の会社の法人向けの商談。1期（3か月）に決まる商談の件数、そのうち新しい取引先の商談の割合、
新しい取引先・前からの取引先それぞれの本当の受注の確率を作成者が置き、取れる・取れないを乱数で決める。
第1期から第8期まで、新しい取引先の割合を変えたとき、まぜた受注率と、割合を第1期にそろえた受注率を比べる。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1266
SRC = "架空の会社の法人向けの商談（作成者が置いた受注の確率と割合からの乱数、seed 1266）"
Q = 8
REPS = 500
GRID_REPS = 200
BASE = dict(n=200, p_new=0.15, p_ex=0.45, s_start=0.3, s_end=0.7, imp=0.0)
SCEN = {
    "S1 割合だけ変わる（新しい取引先3割→7割、区分ごとの率は同じ）": dict(),
    "S2 割合が変わり、区分ごとの率がどちらも3ポイント上がる": dict(imp=0.03),
    "S3 割合は3割のまま、区分ごとの率がどちらも3ポイント上がる": dict(imp=0.03, s_end=0.3),
    "S4 割合が逆に動く（新しい取引先7割→3割、区分ごとの率は同じ）": dict(s_start=0.7, s_end=0.3),
}


def params(p):
    t = np.arange(Q) / (Q - 1)
    s = p["s_start"] + (p["s_end"] - p["s_start"]) * t
    rn = p["p_new"] + p["imp"] * t
    re = p["p_ex"] + p["imp"] * t
    return s, rn, re


def simulate(p, reps, rng):
    """reps 回 × Q 期の件数と受注数"""
    s, rn, re = params(p)
    n = p["n"]
    nn = rng.binomial(n, np.broadcast_to(s, (reps, Q)))
    ne = n - nn
    wn = rng.binomial(nn, np.broadcast_to(rn, (reps, Q)))
    we = rng.binomial(ne, np.broadcast_to(re, (reps, Q)))
    return nn, ne, wn, we


def measures(p, nn, ne, wn, we):
    n = nn + ne
    with np.errstate(divide="ignore", invalid="ignore"):
        ov = (wn + we) / n
        rn = wn / nn
        re = we / ne
    s1 = nn[:, 0] / n[:, 0]
    std8 = s1 * rn[:, -1] + (1 - s1) * re[:, -1]
    d_raw = ov[:, -1] - ov[:, 0]
    d_std = std8 - ov[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        mix_share = 1 - d_std / d_raw
    rev = (d_raw < 0) & (rn[:, -1] > rn[:, 0]) & (re[:, -1] > re[:, 0])
    # 第8期の受注数の見込み
    act = wn[:, -1] + we[:, -1]
    past_ov = (wn[:, :4] + we[:, :4]).sum(1) / n[:, :4].sum(1)
    past_rn = wn[:, :4].sum(1) / nn[:, :4].sum(1)
    past_re = we[:, :4].sum(1) / ne[:, :4].sum(1)
    f_ov = past_ov * n[:, -1]
    f_seg = past_rn * nn[:, -1] + past_re * ne[:, -1]
    f_q7 = ov[:, -2] * n[:, -1]
    return dict(ov1=ov[:, 0], ov8=ov[:, -1], rn1=rn[:, 0], rn8=rn[:, -1], re1=re[:, 0], re8=re[:, -1],
                std8=std8, d_raw=d_raw, d_std=d_std, mix_share=mix_share, rev=rev,
                std_up=d_std > 0, raw_down=d_raw < 0, both_up=(rn[:, -1] > rn[:, 0]) & (re[:, -1] > re[:, 0]),
                act=act, f_ov=f_ov, f_seg=f_seg, f_q7=f_q7,
                ov_all=ov)


def expected(p):
    s, rn, re = params(p)
    ov = s * rn + (1 - s) * re
    std8 = s[0] * rn[-1] + (1 - s[0]) * re[-1]
    past = (s[:4] * rn[:4] + (1 - s[:4]) * re[:4]).mean()
    return dict(ov=ov, ov1=ov[0], ov8=ov[-1], std8=std8, past_ov=past)


def fc(m, key):
    """見込みの外れ：偏り＝(見込みの合計−実績の合計)÷実績の合計、外れ＝|見込み−実績|の平均÷実績の平均"""
    f, a = m[key], m["act"]
    return float((f.sum() - a.sum()) / a.sum()), float(np.abs(f - a).mean() / a.mean())


def pct(x, k=2):
    return round(float(x) * 100, k)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows, per_q = [], []
    store = {}
    for name, ch in SCEN.items():
        p = {**BASE, **ch}
        nn, ne, wn, we = simulate(p, REPS, rng)
        m = measures(p, nn, ne, wn, we)
        ex = expected(p)
        store[name] = (p, m, ex)
        rows.append(dict(
            scenario=name, n=p["n"], s_start=p["s_start"], s_end=p["s_end"], imp=p["imp"],
            exp_rate_q1=pct(ex["ov1"]), exp_rate_q8=pct(ex["ov8"]), exp_std_q8=pct(ex["std8"]),
            rate_q1=pct(m["ov1"].mean()), rate_q8=pct(m["ov8"].mean()), std_q8=pct(m["std8"].mean()),
            new_q1=pct(m["rn1"].mean()), new_q8=pct(m["rn8"].mean()), ex_q1=pct(m["re1"].mean()), ex_q8=pct(m["re8"].mean()),
            change_raw_pt=pct(m["d_raw"].mean()), change_std_pt=pct(m["d_std"].mean()),
            change_std_p10=pct(np.quantile(m["d_std"], 0.1)), change_std_p90=pct(np.quantile(m["d_std"], 0.9)),
            change_raw_p10=pct(np.quantile(m["d_raw"], 0.1)), change_raw_p90=pct(np.quantile(m["d_raw"], 0.9)),
            share_raw_down=pct(m["raw_down"].mean(), 1), share_std_up=pct(m["std_up"].mean(), 1),
            share_both_up=pct(m["both_up"].mean(), 1), share_reversal=pct(m["rev"].mean(), 1),
            fc_overall_bias=pct(fc(m, "f_ov")[0]), fc_overall_abs=pct(fc(m, "f_ov")[1]),
            fc_segment_bias=pct(fc(m, "f_seg")[0]), fc_segment_abs=pct(fc(m, "f_seg")[1]),
            fc_q7_bias=pct(fc(m, "f_q7")[0]), fc_q7_abs=pct(fc(m, "f_q7")[1]),
        ))
        for q in range(Q):
            per_q.append(dict(scenario=name, quarter=q + 1, exp_rate=pct(ex["ov"][q]),
                              rate_mean=pct(m["ov_all"][:, q].mean()),
                              rate_p10=pct(np.quantile(m["ov_all"][:, q], 0.1)),
                              rate_p90=pct(np.quantile(m["ov_all"][:, q], 0.9))))
    summ = pd.DataFrame(rows)
    summ.to_csv(RES / "scenarios_summary.csv", index=False)
    pq = pd.DataFrame(per_q)
    pq.to_csv(RES / "by_quarter.csv", index=False)

    # 1回分のデータ（S2）
    names = list(SCEN)
    rng_ex = np.random.default_rng(SEED + 1)
    p2 = {**BASE, **SCEN[names[1]]}
    s, rn, re = params(p2)
    deal_rows, q_rows = [], []
    did = 0
    for q in range(Q):
        typ = np.where(rng_ex.random(p2["n"]) < s[q], "新しい取引先", "前からの取引先")
        pr = np.where(typ == "新しい取引先", rn[q], re[q])
        won = (rng_ex.random(p2["n"]) < pr).astype(int)
        for tp, w in zip(typ, won):
            did += 1
            deal_rows.append(dict(deal_id=did, quarter=q + 1, client=tp, won=w))
        isn = typ == "新しい取引先"
        q_rows.append(dict(quarter=q + 1, deals=p2["n"], new_deals=int(isn.sum()), new_wins=int(won[isn].sum()),
                           ex_deals=int((~isn).sum()), ex_wins=int(won[~isn].sum())))
    deals = pd.DataFrame(deal_rows)
    deals.to_csv(DATA / "deals_example_s2.csv", index=False)
    qx = pd.DataFrame(q_rows)
    qx["rate"] = ((qx.new_wins + qx.ex_wins) / qx.deals * 100).round(2)
    qx["new_rate"] = (qx.new_wins / qx.new_deals * 100).round(2)
    qx["ex_rate"] = (qx.ex_wins / qx.ex_deals * 100).round(2)
    s1x = qx.new_deals[0] / qx.deals[0]
    qx["same_mix_rate"] = (s1x * qx.new_rate + (1 - s1x) * qx.ex_rate).round(2)
    qx.to_csv(DATA / "quarters_example_s2.csv", index=False)

    # 確かめ：置き方を変える
    grid_rows = []
    for pn, pe, se, n, imp in itertools.product([0.1, 0.2, 0.3], [0.35, 0.5, 0.65], [0.1, 0.3, 0.5, 0.7, 0.9],
                                                [50, 200, 800], [0.0, 0.03]):
        p = dict(n=n, p_new=pn, p_ex=pe, s_start=0.3, s_end=se, imp=imp)
        m = measures(p, *simulate(p, GRID_REPS, rng))
        ex = expected(p)
        grid_rows.append(dict(p_new=pn, p_ex=pe, s_end=se, n=n, imp=imp,
                              exp_change_raw_pt=pct(ex["ov8"] - ex["ov1"]), exp_change_std_pt=pct(ex["std8"] - ex["ov1"]),
                              change_raw_pt=pct(m["d_raw"].mean()), change_std_pt=pct(m["d_std"].mean()),
                              share_raw_down=pct(m["raw_down"].mean(), 1), share_std_up=pct(m["std_up"].mean(), 1),
                              share_both_up=pct(m["both_up"].mean(), 1), share_reversal=pct(m["rev"].mean(), 1),
                              fc_overall_bias=pct(fc(m, "f_ov")[0]), fc_segment_bias=pct(fc(m, "f_seg")[0]),
                              fc_overall_abs=pct(fc(m, "f_ov")[1]), fc_segment_abs=pct(fc(m, "f_seg")[1])))
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # まとめ
    S = lambda i, k: summ.iloc[i][k]
    g = grid
    g_imp = g[g.imp == 0.03]
    g_same = g[g.imp == 0]
    g_shift_up = g_imp[g_imp.s_end >= 0.5]        # 新しい取引先が増える（3割→5〜9割）
    rev_possible = g_imp[g_imp.exp_change_raw_pt < 0]  # 式どおりでもまぜた率が下がる置き方
    headline = {s_i: {k: (float(v) if not isinstance(v, str) else v) for k, v in summ.iloc[i].items()}
                for i, s_i in enumerate(["S1", "S2", "S3", "S4"])}
    robust = {
        "n_grid": int(len(g)), "grid_reps": GRID_REPS,
        "same_rate_change_raw_range": [float(g_same.change_raw_pt.min()), float(g_same.change_raw_pt.max())],
        "same_rate_change_std_range": [float(g_same.change_std_pt.min()), float(g_same.change_std_pt.max())],
        "imp_change_std_range": [float(g_imp.change_std_pt.min()), float(g_imp.change_std_pt.max())],
        "imp_raw_down_expected_n": int(len(rev_possible)),
        "imp_raw_down_expected_change_range": [float(rev_possible.exp_change_raw_pt.min()), float(rev_possible.exp_change_raw_pt.max())],
        "imp_std_up_by_n": {int(n): [float(g_imp[g_imp.n == n].share_std_up.min()), float(g_imp[g_imp.n == n].share_std_up.max())] for n in [50, 200, 800]},
        "imp_both_up_by_n": {int(n): [float(g_imp[g_imp.n == n].share_both_up.min()), float(g_imp[g_imp.n == n].share_both_up.max())] for n in [50, 200, 800]},
        "imp_reversal_max_by_n": {int(n): float(rev_possible[rev_possible.n == n].share_reversal.max()) for n in [50, 200, 800]},
        "fc_overall_bias_range_shift_up_same": [float(g_same[g_same.s_end >= 0.5].fc_overall_bias.min()), float(g_same[g_same.s_end >= 0.5].fc_overall_bias.max())],
        "fc_overall_bias_range_shift_down_same": [float(g_same[g_same.s_end == 0.1].fc_overall_bias.min()), float(g_same[g_same.s_end == 0.1].fc_overall_bias.max())],
        "fc_segment_bias_range_same": [float(g_same.fc_segment_bias.min()), float(g_same.fc_segment_bias.max())],
        "fc_overall_bias_range_noshift_same": [float(g_same[g_same.s_end == 0.3].fc_overall_bias.min()), float(g_same[g_same.s_end == 0.3].fc_overall_bias.max())],
    }
    robust["imp_raw_down_expected_median_by_n"] = {
        col: {int(n): float(rev_possible[rev_possible.n == n][col].median()) for n in [50, 200, 800]}
        for col in ["share_raw_down", "share_both_up", "share_std_up", "share_reversal"]}
    robust["imp_raw_down_expected_settings_per_n"] = int(len(rev_possible) // 3)
    ex1 = {"s1_quarter1_share_new": round(float(s1x) * 100, 2),
           "q1": qx.iloc[0].to_dict(), "q8": qx.iloc[-1].to_dict()}
    run_sec = round(time.time() - t0, 1)
    json.dump({"base": BASE, "quarters": Q, "reps": REPS, "headline": headline, "robust": robust,
               "example_s2": ex1},
              open(RES / "a1266_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：S1・S2 の期ごとの受注率（式どおりの値）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    qs = np.arange(1, Q + 1)
    for a, nm, ttl in [(ax[0], names[0], "S1 区分ごとの率は変わらない"), (ax[1], names[1], "S2 区分ごとの率がどちらも3ポイント上がる")]:
        p, m, exv = store[nm]
        s, rn, re = params(p)
        a.plot(qs, rn * 100, color=GREEN, lw=1.5, marker="o", ms=3.5, label="新しい取引先")
        a.plot(qs, re * 100, color=BLUE, lw=1.5, marker="o", ms=3.5, label="前からの取引先")
        a.plot(qs, exv["ov"] * 100, color=ORANGE, lw=2.2, marker="o", ms=3.5, label="まぜた受注率")
        a.fill_between(qs, pq[pq.scenario == nm].rate_p10, pq[pq.scenario == nm].rate_p90, color=ORANGE, alpha=0.15,
                       lw=0, label="まぜた率の10〜90%（200件の期）")
        a.set_xlabel("期（新しい取引先の割合は第1期30%→第8期70%）")
        a.set_title(ttl)
        a.set_ylim(0, 62)
        a.set_xticks(qs)
    ax[0].set_ylabel("受注率（%、線は式どおりの値）")
    ax[0].legend(fontsize=8.5, frameon=False, loc="upper center", ncol=2)
    save(fig, "a1266_quarters.png", SRC)

    # 図2：S1〜S4 のそのまま比べた差と、割合をそろえた差
    fig, ax = plt.subplots(figsize=(10, 4.4))
    x = np.arange(4)
    raw = summ.change_raw_pt.values
    std = summ.change_std_pt.values
    w = 0.36
    ax.bar(x - w / 2, raw, w, color=ORANGE, label="まぜた受注率をそのまま比べた差")
    ax.bar(x + w / 2, std, w, color=BLUE, label="新しい取引先の割合を第1期にそろえた差")
    for xi, v in zip(x - w / 2, raw):
        ax.text(xi, v + (0.4 if v >= 0 else -0.4), f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
    for xi, v in zip(x + w / 2, std):
        ax.text(xi, v + (0.4 if v >= 0 else -0.4), f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["S1 割合だけ\n3割→7割", "S2 割合3割→7割\n＋率が3ポイント上がる", "S3 割合3割のまま\n＋率が3ポイント上がる", "S4 割合だけ\n7割→3割"], fontsize=9)
    ax.set_ylim(-15, 15)
    ax.set_ylabel("第8期−第1期（ポイント、500回の平均）")
    ax.set_title("割合が動くと、まぜた受注率の差は区分ごとの率の動きと逆向きにもなる")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1266_change.png", SRC)

    # 図3：件数ごとに、上がりが見える割合（区分ごとの率が3ポイント上がり、まぜた率が式どおりでも下がる置き方）
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    rp = rev_possible
    for k, (col, lab, c) in enumerate([("share_raw_down", "まぜた率が下がって見えた", ORANGE),
                                        ("share_both_up", "新しい・前からの両方の率が上がって見えた", GREEN),
                                        ("share_std_up", "割合をそろえた率が上がって見えた", BLUE)]):
        med = [robust["imp_raw_down_expected_median_by_n"][col][n] for n in [50, 200, 800]]
        ax.plot([0, 1, 2], med, color=c, marker="o", lw=1.8, label=lab)
        for xx, v in zip([0, 1, 2], med):
            ax.text(xx, v + 2.5, f"{v:.1f}", ha="center", fontsize=8.5, color=c)
    ax.set_xticks([0, 1, 2])
    ax.set_xlim(-0.3, 2.3)
    ax.set_xticklabels(["50件", "200件", "800件"])
    ax.set_ylim(0, 110)
    ax.set_xlabel("1期に決まる商談の件数")
    ax.set_ylabel("200回のうちの割合（%、置き方の中央値）")
    ax.set_title(f"区分ごとの率は上がるのに、まぜた率は式どおりでも下がる{len(rp) // 3}通り（件数ごと）", fontsize=12)
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    save(fig, "a1266_by_n.png", SRC)

    print(summ.T.to_string())
    print(json.dumps(robust, ensure_ascii=False, indent=1))
    print("run_sec", run_sec)


if __name__ == "__main__":
    main()
