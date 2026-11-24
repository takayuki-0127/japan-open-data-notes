"""1200 配信停止の少ない月は、読者が満足していた月なのか、もう読んでいない人が多い月なのか？（架空のデータ）

架空の店の会員向けのお知らせのメール（月4通、36か月）。会員は「読んでいる人」と「もう読んでいない人」の2つに分け、
読んでいる人は毎月一定の割合で読まなくなる。登録の多い月（作成者が置いた）には新しい会員がまとめて入る。
配信停止は、メールを開いた人がその月の不満の強さ（作成者が置いた）に応じて押すものと、開かずに停止するもの（少し）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1200
SRC = "架空の店の会員向けメール（作成者が乱数で作成、seed 1200）"
MONTHS, SENDS = 36, 4
A0, D0 = 6000, 2000          # はじめの読んでいる人・読んでいない人
JOIN = 200                   # 毎月の新しい会員（平均）
CAMP_P = 0.12                # 登録の多い月になる確率
PA, PD = 0.35, 0.02          # 1通を開く確率（読んでいる人・読んでいない人）
H = 0.05                     # 読んでいる人が1か月で読まなくなる割合
U0 = 0.006                   # 開いた1通あたりの停止の確率（不満がふつうの月）
BASE = dict(k=0.35, camp=2000, w=0.0002)


def sim_list(rng, k, camp, w, fixed=False):
    A, D = A0, D0
    rows = []
    for m in range(MONTHS):
        d = rng.normal()
        u = U0 * np.exp(k * d - k * k / 2)
        if fixed:
            A, D = A0, D0
        else:
            A += rng.poisson(JOIN) + (rng.poisson(camp) if rng.random() < CAMP_P else 0)
        sent = opens = unsub = unsub_open = 0
        dshare = 0.0
        for s in range(SENDS):
            n = A + D
            dshare += D / n / SENDS
            oA, oD = rng.binomial(A, PA), rng.binomial(D, PD)
            uA = rng.binomial(oA, u) + rng.binomial(A - oA, w)
            uD = rng.binomial(oD, u) + rng.binomial(D - oD, w)
            sent += n; opens += oA + oD; unsub += uA + uD
            A -= uA; D -= uD
        if not fixed:
            mv = rng.binomial(A, H)
            A -= mv; D += mv
        rows.append({"month": m + 1, "dissat": d, "sent": sent, "opens": opens, "unsub": unsub,
                     "dormant_share": dshare, "members_end": A + D})
    df = pd.DataFrame(rows)
    df["unsub_per_sent"] = df.unsub / df.sent
    df["open_rate"] = df.opens / df.sent
    df["unsub_per_open"] = df.unsub / df.opens
    return df


def list_metrics(df):
    third = MONTHS // 3
    sat = df.dissat.rank(method="first") <= third            # 不満の弱い3分の1の月
    dorm = df.dormant_share.rank(method="first", ascending=False) <= third
    low1 = df.unsub_per_sent.rank(method="first") <= 6
    low2 = df.unsub_per_open.rank(method="first") <= 6
    ls, lo, lu = np.log(df.unsub_per_sent.clip(lower=1e-9)), np.log(df.open_rate), np.log(df.unsub_per_open.clip(lower=1e-9))
    return {"corr_sent_dissat": df.unsub_per_sent.corr(df.dissat),
            "corr_open_dissat": df.unsub_per_open.corr(df.dissat),
            "corr_sent_dormant": df.unsub_per_sent.corr(df.dormant_share),
            "low6_sent_satisfied": sat[low1].mean(), "low6_sent_dormant_top": dorm[low1].mean(),
            "low6_open_satisfied": sat[low2].mean(), "low6_open_dormant_top": dorm[low2].mean(),
            "share_var_from_openrate": float(np.cov(ls, lo)[0, 1] / ls.var()),
            "share_var_from_per_open": float(np.cov(ls, lu)[0, 1] / ls.var()),
            "dormant_first": df.dormant_share.iloc[0], "dormant_last": df.dormant_share.iloc[-1],
            "year_ratio_per_sent": (df.unsub[24:].sum() / df.sent[24:].sum()) / (df.unsub[:12].sum() / df.sent[:12].sum()),
            "year_ratio_per_open": (df.unsub[24:].sum() / df.opens[24:].sum()) / (df.unsub[:12].sum() / df.opens[:12].sum()),
            "year_ratio_open_rate": (df.opens[24:].sum() / df.sent[24:].sum()) / (df.opens[:12].sum() / df.sent[:12].sum()),
            "year_dissat_diff": df.dissat[24:].mean() - df.dissat[:12].mean()}


def many(seed, n, fixed=False, **kw):
    out = [list_metrics(sim_list(np.random.default_rng(seed * 1000 + r), fixed=fixed, **kw)) for r in range(n)]
    return pd.DataFrame(out)


def r4(x):
    return round(float(x), 4)


def main():
    t0 = time.time()
    # 例の1つのリスト
    ex = sim_list(np.random.default_rng(SEED), **BASE)
    ex.to_csv(DATA / "example_list_months.csv", index=False, float_format="%.6f")
    third = MONTHS // 3
    ex_sat = ex.dissat.rank(method="first") <= third
    lowm = ex.loc[ex.unsub_per_sent.idxmin()]
    ex_sum = {"lowest_month": int(lowm.month), "lowest_unsub_per_sent_pct": r4(lowm.unsub_per_sent * 100),
              "lowest_month_dissat": r4(lowm.dissat), "lowest_month_dissat_rank_of36": int(ex.dissat.rank().loc[lowm.name]),
              "lowest_month_dormant_share_pct": r4(lowm.dormant_share * 100),
              "lowest_month_unsub_per_open_rank_of36": int(ex.unsub_per_open.rank().loc[lowm.name]),
              "first_year_unsub_per_sent_pct": r4(ex.unsub[:12].sum() / ex.sent[:12].sum() * 100),
              "last_year_unsub_per_sent_pct": r4(ex.unsub[24:].sum() / ex.sent[24:].sum() * 100),
              "first_year_unsub_per_open_pct": r4(ex.unsub[:12].sum() / ex.opens[:12].sum() * 100),
              "last_year_unsub_per_open_pct": r4(ex.unsub[24:].sum() / ex.opens[24:].sum() * 100),
              "first_year_dissat_mean": r4(ex.dissat[:12].mean()), "last_year_dissat_mean": r4(ex.dissat[24:].mean()),
              "dormant_first_pct": r4(ex.dormant_share.iloc[0] * 100), "dormant_last_pct": r4(ex.dormant_share.iloc[-1] * 100),
              "satisfied_months_in_low6": int(ex_sat[ex.unsub_per_sent.rank(method="first") <= 6].sum())}
    ex_m = {k: r4(v) for k, v in list_metrics(ex).items()}

    # 300のリスト（基本）と、読んでいない人の割合が動かない対照
    base = many(SEED, 300, **BASE)
    ctrl = many(SEED + 1, 300, fixed=True, **BASE)
    base.to_csv(RES / "lists300_base.csv", index=False, float_format="%.6f")
    keep_ctrl = ["corr_sent_dissat", "corr_open_dissat", "low6_sent_satisfied", "low6_open_satisfied",
                 "share_var_from_openrate", "year_ratio_per_sent", "year_ratio_per_open"]
    summ = {"base": {c: r4(base[c].mean()) for c in base.columns},
            "control_fixed_dormant": {c: r4(ctrl[c].mean()) for c in keep_ctrl}}
    fell = base.year_ratio_per_sent <= 0.8
    summ["base"]["share_lists_per_sent_fell20"] = r4(fell.mean())
    summ["base"]["share_lists_per_open_fell20"] = r4((base.year_ratio_per_open <= 0.8).mean())
    summ["base"]["among_fell20_share_more_satisfied"] = r4((base.year_dissat_diff[fell] < 0).mean())
    summ["control_fixed_dormant"]["share_lists_per_sent_fell20"] = r4((ctrl.year_ratio_per_sent <= 0.8).mean())
    summ["base"]["corr_sent_dissat_p5"] = r4(base.corr_sent_dissat.quantile(.05))
    summ["base"]["corr_sent_dissat_p95"] = r4(base.corr_sent_dissat.quantile(.95))
    summ["base"]["corr_open_dissat_p5"] = r4(base.corr_open_dissat.quantile(.05))
    summ["base"]["corr_open_dissat_p95"] = r4(base.corr_open_dissat.quantile(.95))

    # 確かめ：27通り（不満の効き k × 登録の多い月の人数 × 開かずに停止する確率）
    grid = []
    gi = 0
    for k in [0.15, 0.35, 0.6]:
        for camp in [0, 2000, 5000]:
            for w in [0.0, 0.0002, 0.001]:
                g = many(SEED * 10 + gi, 100, k=k, camp=camp, w=w)
                gi += 1
                row = {"k": k, "camp": camp, "w": w}
                row.update({c: r4(g[c].mean()) for c in ["corr_sent_dissat", "corr_open_dissat", "corr_sent_dormant",
                                                          "low6_sent_satisfied", "low6_open_satisfied",
                                                          "low6_sent_dormant_top", "share_var_from_openrate",
                                                          "dormant_first", "dormant_last", "year_ratio_per_sent",
                                                          "year_ratio_per_open"]})
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gsum = {"n": len(grid)}
    for c in ["corr_sent_dissat", "corr_open_dissat", "low6_sent_satisfied", "low6_open_satisfied",
              "share_var_from_openrate", "corr_sent_dormant", "year_ratio_per_sent", "year_ratio_per_open"]:
        gsum[c + "_min"] = r4(grid[c].min()); gsum[c + "_max"] = r4(grid[c].max())
    gsum["n_open_better_corr"] = int((grid.corr_open_dissat > grid.corr_sent_dissat).sum())
    gsum["n_open_better_low6"] = int((grid.low6_open_satisfied > grid.low6_sent_satisfied).sum())
    gsum["n_year_ratio_per_sent_below1"] = int((grid.year_ratio_per_sent < 1).sum())
    w0 = grid[grid.w == 0]
    gsum["w0_n"] = len(w0)
    gsum["w0_year_ratio_per_open_min"] = r4(w0.year_ratio_per_open.min())
    gsum["w0_year_ratio_per_open_max"] = r4(w0.year_ratio_per_open.max())
    worse = grid[grid.corr_open_dissat <= grid.corr_sent_dissat]
    gsum["open_not_better_n"] = len(worse)
    gsum["open_not_better_all_w0001"] = bool((worse.w == 0.001).all())
    gsum["n_low6_sent_below_third"] = int((grid.low6_sent_satisfied < 1 / 3).sum())

    out = {"setting": {"months": MONTHS, "sends_per_month": SENDS, "A0": A0, "D0": D0, "join_mean": JOIN,
                       "campaign_prob": CAMP_P, "open_active": PA, "open_dormant": PD, "to_dormant_per_month": H,
                       "unsub_per_open_base": U0, **BASE},
           "example_list": ex_sum, "example_list_metrics": ex_m, "lists300": summ, "grid27": gsum,
           "run_sec": round(time.time() - t0, 1)}
    out.pop("run_sec")
    json.dump(out, open(RES / "a1200_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例のリストの月ごとの停止率と、読んでいない人の割合
    fig, ax = plt.subplots(2, 1, figsize=(7.6, 5.6), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    a = ax[0]
    a.plot(ex.month, ex.unsub_per_sent * 100, color=BLUE, marker="o", ms=3.5, label="配信停止 ÷ 送った通数")
    a.plot(ex.month, ex.unsub_per_open * 100 / 4, color=ORANGE, marker="s", ms=3.5,
           label="配信停止 ÷ 開いた通数（÷4 して重ねた）")
    sat = ex[ex_sat]
    a.scatter(sat.month, sat.unsub_per_sent * 100, s=60, facecolor="none", edgecolor=GREEN, lw=1.3, zorder=5,
              label="不満の弱い3分の1の月（置いた値）")
    a.set_ylim(0, max(ex.unsub_per_sent.max(), ex.unsub_per_open.max() / 4) * 100 * 1.5); a.set_ylabel("%")
    a.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2)
    a.set_title("例のリスト：月ごとの配信停止と、読んでいない人の割合")
    b = ax[1]
    b.bar(ex.month, ex.dormant_share * 100, color=GRAY)
    b.set_ylim(0, 100); b.set_ylabel("読んでいない人の割合（%）"); b.set_xlabel("月")
    save(fig, "a1200_example.png", SRC)

    # 図2：基本と対照の相関
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    labels = ["停止÷送った通数\n（読んでいない人\nの割合が動く）", "停止÷開いた通数\n（読んでいない人\nの割合が動く）",
              "停止÷送った通数\n（割合が動かない\n対照）"]
    vals = [summ["base"]["corr_sent_dissat"], summ["base"]["corr_open_dissat"],
            summ["control_fixed_dormant"]["corr_sent_dissat"]]
    ax.bar(labels, vals, color=[BLUE, ORANGE, GRAY], width=.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{v:g}", ha="center", fontsize=9.5)
    ax.set_ylim(0, 1); ax.set_ylabel("その月の不満の強さとの相関\n（300のリストの平均）")
    ax.set_title("停止を送った通数で割ると、その月の不満の強さとの連動が弱かった")
    save(fig, "a1200_corr.png", SRC, y=-0.1)

    # 図3：27通りでの、3年目÷1年目
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(len(grid))
    ax.bar(x - 0.2, grid.year_ratio_per_sent, width=0.4, color=BLUE, label="停止÷送った通数")
    ax.bar(x + 0.2, grid.year_ratio_per_open, width=0.4, color=ORANGE, label="停止÷開いた通数")
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_ylim(0, 1.6); ax.set_xticks([])
    ax.set_xlabel("置き方の27通り（不満の効き × 登録の多い月の人数 × 開かずに停止する確率）")
    ax.set_ylabel("3年目 ÷ 1年目（倍）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("不満の強さは平均で同じでも、\n送った通数あたりの停止は3年目に下がった（27通り、各100リストの平均）")
    save(fig, "a1200_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
