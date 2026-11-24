"""1203 登録して間もない人ほどよく開くとき、全体の開封率の下がり方は、読者の入れかわりでどれだけ説明できるのか？（架空のデータ）

架空の店の会員向けのお知らせのメール。毎週1通、104週送る。会員は毎週入会し、毎週一定の割合でやめる。
1人ひとりの開きやすさ（もとの開く確率）と、登録してからの週数で開く確率が下がる形を作成者が置く。
「前の13週」と「後の13週」の開封率を比べ、登録してからの週数の内訳を前の期間にそろえた開封率と比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1203
SRC = "架空の店の会員向けメール（作成者が置いた開く確率と入会・退会からの乱数、seed 1203）"
PRE = 52           # 送り始める前の入会の週数（お知らせを始めて1年の会員がいる）
WEEKS = 104        # 送る週数
FIRST = np.arange(1, 14)
LAST = np.arange(92, 105)
BASE = dict(tau=12.0, floor=0.45, inflow_start=120, inflow_end=30, leave=0.004,
            mail_drop=0.0, cohort_drop=0.0, mean_b=0.35)
CAP = 52           # 52週以上は1つにまとめる
SCHEMES = {
    "1週ごと": None,
    "4週ごと": "w4",
    "3つ（12週未満・12〜51週・52週以上）": [0, 12, 52],
    "2つ（1年未満・1年以上）": [0, 52],
}


def inflow_series(p):
    pre = np.full(PRE, p["inflow_start"], dtype=float)          # 週 -155..0
    post = np.linspace(p["inflow_start"], p["inflow_end"], WEEKS)  # 週 1..104
    return np.concatenate([pre, post])


def simulate(p, rng, keep_people=False):
    joins_w = np.arange(-PRE + 1, WEEKS + 1)
    n_in = rng.poisson(inflow_series(p))
    join = np.repeat(joins_w, n_in)
    n = join.size
    a = 3.5
    bb = a * (1 - p["mean_b"]) / p["mean_b"]
    b = rng.beta(a, bb, n)
    # 後から入った人ほどもとの開く確率が低い（cohort_drop）
    coh = 1 - p["cohort_drop"] * np.clip(join, 0, WEEKS) / WEEKS
    b = b * coh
    # やめる週：入った週の次の週から毎週 leave の確率でやめる（その週からは送らない）
    life = rng.geometric(p["leave"], n)  # 送られる通数
    sent = np.zeros((WEEKS, CAP + 1))
    opens = np.zeros((WEEKS, CAP + 1))
    expv = np.zeros((WEEKS, CAP + 1))
    for t in range(1, WEEKS + 1):
        ten = t - join            # 0 なら入った週の配信
        alive = (ten >= 0) & (ten < life)
        idx = np.nonzero(alive)[0]
        tt = ten[idx]
        m = p["floor"] + (1 - p["floor"]) * np.exp(-tt / p["tau"])
        M = 1 - p["mail_drop"] * (t - 1) / (WEEKS - 1)
        prob = np.minimum(1, b[idx] * m * M)
        op = rng.random(idx.size) < prob
        tc = np.minimum(tt, CAP)
        sent[t - 1] = np.bincount(tc, minlength=CAP + 1)
        opens[t - 1] = np.bincount(tc, weights=op, minlength=CAP + 1)
        expv[t - 1] = np.bincount(tc, weights=prob, minlength=CAP + 1)
    wi, ti = np.nonzero(sent)
    out = pd.DataFrame({"week": wi + 1, "tenure": ti, "sent": sent[wi, ti].astype(int),
                        "opens": opens[wi, ti].astype(int), "expected": expv[wi, ti]})
    if keep_people:
        return out, pd.DataFrame({"member_id": np.arange(1, n + 1), "join_week": join, "base_prob": b.round(4),
                                  "sends_until_leave": life})
    return out


def bucket(ten, scheme):
    spec = SCHEMES[scheme]
    if spec is None:
        return ten
    if spec == "w4":
        return np.minimum(ten // 4, CAP // 4)
    return np.searchsorted(np.array(spec), ten, side="right") - 1


def decompose(tab, scheme):
    t = tab.copy()
    t["bk"] = bucket(t["tenure"].values, scheme)
    f = t[t.week.isin(FIRST)].groupby("bk")[["sent", "opens"]].sum()
    l = t[t.week.isin(LAST)].groupby("bk")[["sent", "opens"]].sum()
    r_first = f.opens.sum() / f.sent.sum()
    r_last = l.opens.sum() / l.sent.sum()
    rf = f.opens / f.sent
    rl = l.opens / l.sent
    wf = f.sent / f.sent.sum()
    wl = l.sent / l.sent.sum()
    common = rf.index.intersection(rl.index)
    # 前の期間の内訳にそろえた後の開封率（前の期間にない区分は使わない）
    wf_c = wf[common] / wf[common].sum()
    same_mix_last = float((wf_c * rl[common]).sum())
    wl_c = wl[common] / wl[common].sum()
    same_mix_first = float((wl_c * rf[common]).sum())  # 後の内訳にそろえた前の開封率
    d = r_last - r_first
    share_f = 1 - (same_mix_last - r_first) / d
    share_l = 1 - (r_last - same_mix_first) / d
    return dict(scheme=scheme, rate_first=r_first, rate_last=r_last, change=d,
                same_mix_last=same_mix_last, same_mix_first=same_mix_first,
                within_ratio_f=same_mix_last / r_first, within_ratio_l=r_last / same_mix_first,
                mix_share_f=share_f, mix_share_l=share_l)


def true_mail_ratio(p):
    w = np.arange(1, WEEKS + 1)
    M = 1 - p["mail_drop"] * (w - 1) / (WEEKS - 1)
    return float(M[LAST - 1].mean() / M[FIRST - 1].mean())


SCEN = {
    "S1 メールは変わらない": {},
    "S2 メールそのものが弱くなる（最後に15%）": {"mail_drop": 0.15},
    "S3 後から入る人ほどもともと開きにくい（最後に20%）": {"cohort_drop": 0.2},
    "S4 入会の勢いが落ちない": {"inflow_end": 120},
}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 1) 基本の1回分（データと図）
    tab, people = simulate(BASE, rng, keep_people=True)
    wk = tab.groupby("week")[["sent", "opens"]].sum()
    wk["open_rate"] = wk.opens / wk.sent
    new = tab[tab.tenure < 12].groupby("week").sent.sum()
    wk["share_tenure_lt12"] = (new / wk.sent).fillna(0)
    # 前の13週の内訳にそろえた週ごとの開封率（1週ごと）
    f = tab[tab.week.isin(FIRST)].groupby("tenure")[["sent", "opens"]].sum()
    wf = f.sent / f.sent.sum()
    sm = []
    for w, g in tab.groupby("week"):
        r = (g.set_index("tenure").opens / g.set_index("tenure").sent)
        c = wf.index.intersection(r.index)
        sm.append((wf[c] / wf[c].sum() * r[c]).sum())
    wk["same_mix_rate"] = sm
    wk = wk.reset_index()
    wk.round(5).to_csv(DATA / "weekly_example.csv", index=False)
    people.to_csv(DATA / "members_example.csv", index=False)
    by_ten = tab.groupby("tenure")[["sent", "opens"]].sum()
    by_ten["open_rate"] = by_ten.opens / by_ten.sent
    by_ten = by_ten.reset_index()
    by_ten.round(5).to_csv(RES / "open_by_tenure_example.csv", index=False)
    ex = {s: decompose(tab, s) for s in SCHEMES}

    # 2) 場面ごと×区分の分け方（各50回）
    rows = []
    for sname, ch in SCEN.items():
        p = dict(BASE, **ch)
        for r in range(50):
            tb = simulate(p, np.random.default_rng(SEED * 1000 + r))
            for s in SCHEMES:
                d = decompose(tb, s)
                d.update(scenario=sname, rep=r, true_mail_ratio=true_mail_ratio(p))
                rows.append(d)
    reps = pd.DataFrame(rows)
    reps.round(6).to_csv(RES / "reps_scenarios.csv", index=False)
    summ = []
    for (sname, s), g in reps.groupby(["scenario", "scheme"], sort=False):
        summ.append(dict(scenario=sname, scheme=s,
                         rate_first=g.rate_first.mean() * 100, rate_last=g.rate_last.mean() * 100,
                         change_pt=g.change.mean() * 100,
                         same_mix_last=g.same_mix_last.mean() * 100,
                         mix_share_f=g.mix_share_f.mean() * 100,
                         mix_share_f_p10=g.mix_share_f.quantile(0.1) * 100,
                         mix_share_f_p90=g.mix_share_f.quantile(0.9) * 100,
                         mix_share_l=g.mix_share_l.mean() * 100,
                         within_ratio_f=g.within_ratio_f.mean(), within_ratio_l=g.within_ratio_l.mean(),
                         true_mail_ratio=g.true_mail_ratio.mean()))
    summ = pd.DataFrame(summ)
    summ.round(4).to_csv(RES / "scenarios_summary.csv", index=False)

    # 3) 確かめ：置き方を変えた grid（各3回）
    grid = []
    for tau in [4.0, 12.0, 26.0]:
        for floor in [0.3, 0.45, 0.7]:
            for inf_end in [120, 60, 30, 10]:
                for md in [0.0, 0.15]:
                    p = dict(BASE, tau=tau, floor=floor, inflow_end=inf_end, mail_drop=md)
                    acc = {s: [] for s in SCHEMES}
                    for r in range(3):
                        tb = simulate(p, np.random.default_rng(SEED * 100000 + len(grid) * 10 + r))
                        for s in SCHEMES:
                            acc[s].append(decompose(tb, s))
                    row = dict(tau=tau, floor=floor, inflow_end=inf_end, mail_drop=md,
                               true_mail_ratio=true_mail_ratio(p))
                    for s, key in zip(SCHEMES, ["w1", "w4", "b3", "b2"]):
                        dd = pd.DataFrame(acc[s])
                        row["change_pt"] = dd.change.mean() * 100
                        row["raw_ratio"] = (dd.rate_last / dd.rate_first).mean()
                        row[f"mix_share_{key}"] = dd.mix_share_f.mean() * 100
                        row[f"within_ratio_{key}"] = dd.within_ratio_f.mean()
                    grid.append(row)
    grid = pd.DataFrame(grid)
    grid.round(5).to_csv(RES / "grid.csv", index=False)

    # まとめ
    S = lambda sc, sh, k: float(summ[(summ.scenario == sc) & (summ.scheme == sh)][k].iloc[0])
    s1, s2, s3, s4 = list(SCEN)
    w1, w4, b3, b2 = list(SCHEMES)
    g0 = grid[grid.mail_drop == 0]
    g15 = grid[grid.mail_drop == 0.15]
    gch = g0[g0.change_pt < -0.5]
    headline = {
        "s1_rate_first": round(S(s1, w1, "rate_first"), 2), "s1_rate_last": round(S(s1, w1, "rate_last"), 2),
        "s1_change_pt": round(S(s1, w1, "change_pt"), 2),
        "s1_mix_share": {sh: round(S(s1, sh, "mix_share_f"), 2) for sh in SCHEMES},
        "s1_mix_share_p10_p90_w1": [round(S(s1, w1, "mix_share_f_p10"), 2), round(S(s1, w1, "mix_share_f_p90"), 2)],
        "s1_mix_share_lastweights": {sh: round(S(s1, sh, "mix_share_l"), 2) for sh in SCHEMES},
        "s2_change_pt": round(S(s2, w1, "change_pt"), 2),
        "s2_within_ratio": {sh: round(S(s2, sh, "within_ratio_f"), 4) for sh in SCHEMES},
        "s2_true_mail_ratio": round(S(s2, w1, "true_mail_ratio"), 4),
        "s2_mix_share": {sh: round(S(s2, sh, "mix_share_f"), 2) for sh in SCHEMES},
        "s3_change_pt": round(S(s3, w1, "change_pt"), 2),
        "s3_mix_share": {sh: round(S(s3, sh, "mix_share_f"), 2) for sh in SCHEMES},
        "s3_mix_share_lastweights": {sh: round(S(s3, sh, "mix_share_l"), 2) for sh in SCHEMES},
        "s3_within_ratio_w1": round(S(s3, w1, "within_ratio_f"), 4),
        "s4_change_pt": round(S(s4, w1, "change_pt"), 2),
        "s1_within_ratio": {sh: round(S(s1, sh, "within_ratio_f"), 4) for sh in SCHEMES},
        "s4_mix_share_w1": round(S(s4, w1, "mix_share_f"), 2),
        "example_share_lt12_first": round(float(wk[wk.week.isin(FIRST)].share_tenure_lt12.mean() * 100), 2),
        "example_share_lt12_last": round(float(wk[wk.week.isin(LAST)].share_tenure_lt12.mean() * 100), 2),
        "example_open_tenure0": round(float(by_ten.open_rate.iloc[0] * 100), 2),
        "example_open_tenure52plus": round(float(by_ten[by_ten.tenure >= 52].opens.sum() / by_ten[by_ten.tenure >= 52].sent.sum() * 100), 2),
        "example_members_total": int(len(people)),
    }
    robust = {
        "n_grid": int(len(grid)),
        "mail_same_change_pt_range": [round(g0.change_pt.min(), 2), round(g0.change_pt.max(), 2)],
        "mail_same_dropping_n": int(len(gch)),
        "mail_same_dropping_mix_share_w1_range": [round(gch.mix_share_w1.min(), 2), round(gch.mix_share_w1.max(), 2)],
        "mail_same_dropping_mix_share_w4_range": [round(gch.mix_share_w4.min(), 2), round(gch.mix_share_w4.max(), 2)],
        "mail_same_dropping_mix_share_b3_range": [round(gch.mix_share_b3.min(), 2), round(gch.mix_share_b3.max(), 2)],
        "mail_same_dropping_mix_share_b2_range": [round(gch.mix_share_b2.min(), 2), round(gch.mix_share_b2.max(), 2)],
        "mail_same_dropping_b2_median": round(float(gch.mix_share_b2.median()), 2),
        "mail_drop_true_ratio": round(float(g15.true_mail_ratio.iloc[0]), 4),
        "mail_drop_within_w1_range": [round(g15.within_ratio_w1.min(), 4), round(g15.within_ratio_w1.max(), 4)],
        "mail_drop_within_b2_range": [round(g15.within_ratio_b2.min(), 4), round(g15.within_ratio_b2.max(), 4)],
        "mail_same_within_w1_range": [round(g0.within_ratio_w1.min(), 4), round(g0.within_ratio_w1.max(), 4)],
    }
    # 4週ごとより粗い分け方で、メールが変わらないのに「メールが弱くなった」と読む大きさ
    robust["mail_same_raw_ratio_range"] = [round(g0.raw_ratio.min(), 4), round(g0.raw_ratio.max(), 4)]
    robust["mail_drop_raw_ratio_range"] = [round(g15.raw_ratio.min(), 4), round(g15.raw_ratio.max(), 4)]
    robust["mail_same_within_w1_outside_2pct"] = int(((g0.within_ratio_w1 - 1).abs() > 0.02).sum())
    robust["mail_same_within_b2_below_095"] = int((g0.within_ratio_b2 < 0.95).sum())
    robust["mail_same_within_b2_range"] = [round(g0.within_ratio_b2.min(), 4), round(g0.within_ratio_b2.max(), 4)]
    run_sec = round(time.time() - t0, 1)
    json.dump({"base": BASE, "first_weeks": [1, 13], "last_weeks": [92, 104], "headline": headline,
               "robust": robust, "example_decompose": ex},
              open(RES / "a1203_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：登録してからの週数ごとの開封率と、週ごとの全体の開封率
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    bt = by_ten[by_ten.tenure <= 104]
    ax[0].plot(bt.tenure, bt.open_rate * 100, color=BLUE, lw=1.5)
    ax[0].set_ylim(0, 40)
    ax[0].set_xlabel("登録してからの週数")
    ax[0].set_ylabel("開封率（%）")
    ax[0].set_title("登録して間もない人ほどよく開く（置いた形）")
    ax[1].plot(wk.week, wk.open_rate * 100, color=ORANGE, lw=1.5, label="全体の開封率")
    ax[1].plot(wk.week, wk.same_mix_rate * 100, color=BLUE, lw=1.5, label="週数の内訳を前の13週にそろえた開封率")
    ax[1].set_ylim(0, 40)
    ax[1].set_xlabel("送った週")
    ax[1].set_ylabel("開封率（%）")
    ax[1].set_title("メールが変わらなくても全体は下がる（S1、1回分）")
    ax[1].legend(fontsize=8.5, loc="lower left", frameon=False)
    save(fig, "a1203_weekly.png", SRC)

    # 図2：分け方ごとの「入れかわりで説明できる割合」
    fig, ax = plt.subplots(figsize=(10, 4.4))
    scs = [s1, s2, s3]
    labs = ["S1 メールは変わらない", "S2 メールが弱くなる", "S3 後から入る人が開きにくい"]
    cols = [BLUE, ORANGE, GREEN]
    x = np.arange(len(SCHEMES))
    wdt = 0.26
    for i, (sc, lb, c) in enumerate(zip(scs, labs, cols)):
        v = [S(sc, sh, "mix_share_f") for sh in SCHEMES]
        ax.bar(x + (i - 1) * wdt, v, wdt, color=c, label=lb)
        for xi, vi in zip(x, v):
            ax.text(xi + (i - 1) * wdt, vi + 1.5, f"{vi:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(["1週ごと", "4週ごと", "3つ", "2つ（1年で分ける）"])
    ax.set_ylim(0, 115)
    ax.set_ylabel("下がり幅のうち入れかわりで説明できる割合（%）")
    ax.set_xlabel("登録してからの週数の分け方（前の13週の内訳にそろえる）")
    ax.set_title("粗く分けるほど、入れかわりの分が小さく出る（各50回の平均）")
    ax.legend(fontsize=8.5, frameon=False, loc="upper right", ncol=3)
    save(fig, "a1203_share_by_scheme.png", SRC)

    # 図3：確かめの置き方ごと（72通り）
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for md, mk, lbm in [(0.0, "o", "メールは変わらない"), (0.15, "^", "メールが最後に15%弱くなる")]:
        gg = grid[grid.mail_drop == md]
        ax.scatter(gg.raw_ratio, gg.within_ratio_w1, s=22, marker=mk, color=BLUE, alpha=0.85,
                   label=f"{lbm}・1週ごとにそろえる")
        ax.scatter(gg.raw_ratio, gg.within_ratio_b2, s=22, marker=mk, color=ORANGE, alpha=0.85,
                   label=f"{lbm}・2つ（1年で分ける）にそろえる")
    ax.axhline(1, color=INK, lw=0.8, ls=":")
    ax.axhline(robust["mail_drop_true_ratio"], color=INK, lw=0.8, ls="--")
    ax.text(0.655, 1.006, "メールが変わらないときの本当の値 1", fontsize=8, color=INK)
    ax.text(0.655, robust["mail_drop_true_ratio"] + 0.006, f"メールが弱くなるときの本当の値 {robust['mail_drop_true_ratio']}", fontsize=8, color=INK)
    ax.set_xlabel("そのまま比べた比（後の13週の開封率÷前の13週の開封率）")
    ax.set_ylabel("週数の内訳をそろえた比")
    ax.set_title("72通り：1週ごとなら本当の値の近く、2つでは下に外れる")
    ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    save(fig, "a1203_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False, indent=1))
    print(json.dumps(robust, ensure_ascii=False, indent=1))
    print("run_sec", run_sec)


if __name__ == "__main__":
    main()
