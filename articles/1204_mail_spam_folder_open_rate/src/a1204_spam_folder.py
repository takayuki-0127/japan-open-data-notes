"""1204 迷惑メールに振り分けられた分は、開封率の数字のどこに表れるのか？（架空のデータ）

架空の店の会員2万人に、お知らせのメールを毎週1通、26週送る。
会員のアドレスは、受信側のメールサービスA・B・C（架空）に分かれる。
届いたメールは「受信箱」か「迷惑メールのフォルダ」に入り、迷惑メールのフォルダに入ったメールはほとんど開かれない。
送る側に見えるのは「届かなかった（宛先なし）」「届いた」「開いた」「クリックした」だけで、どちらのフォルダに入ったかは見えない。
同じだけ開封率が下がる3つの場面（Bで振り分けが増える・開かない人ほど振り分けられる・読む気が落ちる）で、
送る側に見える数字のどこが違うかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1204
SRC = "架空の店の会員向けメール（作成者が置いた開く確率と振り分けからの乱数、seed 1204）"
N = 20000
WEEKS = 26
FIRST = np.arange(1, 9)     # 1〜8週
LAST = np.arange(19, 27)    # 19〜26週
TYPES = np.array(["A", "B", "C"])
BASE = dict(share_b=0.3, rise=0.6, r=0.05, base_spam=0.02, bad_addr=0.02, k=3.0)
SCN = ["T", "P", "I"]
SCN_JA = {"T": "サービスBで振り分けが増える", "P": "開かない人ほど振り分けられる", "I": "読む気が落ちる（振り分けは同じ）"}


def ramp(t):
    """8週目までは0、18週目に1になり、そのあとは1"""
    return np.clip((t - 8) / 10, 0, 1)


_CACHE = {}


def scale_for_p(p):
    key = (p["share_b"], p["rise"], p["base_spam"], p["k"])
    if key not in _CACHE:
        _CACHE[key] = _scale_for_p(p)
    return _CACHE[key]


def _scale_for_p(p, a=3.0, bb=7.0):
    """P：開かない人ほど振り分けられるとき、開封の下がり幅が T と同じになる強さ c を求める（大きな乱数の標本で）"""
    rr = np.random.default_rng(SEED + 7)
    b = rr.beta(a, bb, 400000)
    target = p["share_b"] * p["rise"] * b.mean()   # T で増える振り分けの「開く人の重み」の分
    h = (1 - b) ** p["k"]
    lo, hi = 0.0, 50.0
    for _ in range(60):
        c = (lo + hi) / 2
        v = (b * np.minimum(1 - p["base_spam"], c * h)).mean()
        lo, hi = (c, hi) if v < target else (lo, c)
    c = (lo + hi) / 2
    return c, float(np.minimum(1 - p["base_spam"], c * h).mean())


def f_end_for_i(p):
    """I：読む気が落ちる倍率（18週目以降）。開封率の見込みが T と同じになる値"""
    keep_t = 1 - (p["base_spam"] + p["share_b"] * p["rise"]) * (1 - p["r"])
    keep_0 = 1 - p["base_spam"] * (1 - p["r"])
    return keep_t / keep_0


def make_people(p, rng):
    typ = rng.choice(3, N, p=[(1 - p["share_b"]) * 5 / 7, p["share_b"], (1 - p["share_b"]) * 2 / 7])
    b = rng.beta(3.0, 7.0, N)
    q = 0.05 + 0.4 * b                     # 開いた人がクリックする確率（よく開く人ほどよくクリックする）
    bad = rng.random(N) < p["bad_addr"]    # 届かないアドレス
    return typ, b, q, bad


def run(p, scen, rng, people=None, keep_week=False):
    typ, b, q, bad = people if people is not None else make_people(p, rng)
    deliv = ~bad
    if scen == "P":
        c, _ = scale_for_p(p)
        h = np.minimum(1 - p["base_spam"], c * (1 - b) ** p["k"])
    fe = f_end_for_i(p) if scen == "I" else 1.0
    last_open = np.full(N, -999)
    rec = []
    inactive = {}
    for t in range(1, WEEKS + 1):
        rt = ramp(t)
        spam_p = np.full(N, p["base_spam"])
        if scen == "T":
            spam_p = spam_p + (typ == 1) * p["rise"] * rt
        elif scen == "P":
            spam_p = spam_p + h * rt
        f = 1 - (1 - fe) * rt
        in_spam = rng.random(N) < spam_p
        po = b * f * np.where(in_spam, p["r"], 1.0)
        op = deliv & (rng.random(N) < po)
        cl = op & (rng.random(N) < q)
        last_open[op] = t
        for k in range(3):
            m = deliv & (typ == k)
            rec.append(dict(week=t, type=TYPES[k], sent=int((typ == k).sum()), delivered=int(m.sum()),
                            inbox=int((m & ~in_spam).sum()), opens=int((op & m).sum()),
                            clicks=int((cl & m).sum()), opens_inbox=int((op & m & ~in_spam).sum())))
        if t in (8, 26):
            inactive[t] = float((deliv & (last_open <= t - 8)).sum() / deliv.sum())
    w = pd.DataFrame(rec)
    return w, inactive


def period_stats(w):
    out = {}
    for name, wk in [("first", FIRST), ("last", LAST)]:
        g = w[w.week.isin(wk)]
        s = g[["sent", "delivered", "inbox", "opens", "clicks", "opens_inbox"]].sum()
        out[name] = dict(delivery_rate=s.delivered / s.sent, open_rate=s.opens / s.delivered,
                         click_rate=s.clicks / s.delivered, click_per_open=s.clicks / s.opens,
                         inbox_share=s.inbox / s.delivered, inbox_open_rate=s.opens_inbox / s.inbox)
        for k in TYPES:
            gk = g[g.type == k][["delivered", "opens"]].sum()
            out[name][f"open_rate_{k}"] = gk.opens / gk.delivered
            out[name][f"deliv_share_{k}"] = gk.delivered / s.delivered
    return out


def flat(st, inactive):
    row = {}
    for per in ("first", "last"):
        for k, v in st[per].items():
            row[f"{k}_{per}"] = float(v)
    row["open_drop_pt"] = (st["last"]["open_rate"] - st["first"]["open_rate"]) * 100
    # 下がり幅のうちサービスBの分（Bの開封率の変化×Bの届いた割合）
    contrib = {k: (st["last"][f"open_rate_{k}"] - st["first"][f"open_rate_{k}"]) * st["first"][f"deliv_share_{k}"]
               for k in TYPES}
    tot = sum(contrib.values())
    row["b_part_of_drop"] = contrib["B"] / tot if tot != 0 else np.nan
    row["cpo_change_pt"] = (st["last"]["click_per_open"] - st["first"]["click_per_open"]) * 100
    row["inactive8_w8"] = inactive[8]
    row["inactive8_w26"] = inactive[26]
    return row


def main():
    t0 = time.time()
    p = dict(BASE)
    # 1) 3つの場面（同じ会員で、各100回）
    rows = []
    example = None
    for r in range(100):
        rng = np.random.default_rng(SEED * 1000 + r)
        people = make_people(p, rng)
        for sc in SCN:
            w, ina = run(p, sc, np.random.default_rng(SEED * 1000 + r * 10 + SCN.index(sc) + 1), people)
            row = flat(period_stats(w), ina)
            row.update(scenario=sc, rep=r)
            rows.append(row)
            if r == 0:
                w["scenario"] = sc
                example = w if example is None else pd.concat([example, w], ignore_index=True)
    reps = pd.DataFrame(rows)
    reps.round(6).to_csv(RES / "reps_scenarios.csv", index=False)
    summ = reps.groupby("scenario", sort=False).mean(numeric_only=True).drop(columns="rep")
    summ.round(6).to_csv(RES / "scenarios_summary.csv")
    example.to_csv(DATA / "weekly_by_type_example.csv", index=False)

    # 2) 確かめ：T の置き方 27通り、P の置き方 12通り（各10回）
    grid = []
    gi = 0
    for sb in [0.1, 0.3, 0.5]:
        for rise in [0.2, 0.5, 0.8]:
            for rv in [0.0, 0.05, 0.2]:
                pp = dict(BASE, share_b=sb, rise=rise, r=rv)
                acc = []
                for r in range(10):
                    rng = np.random.default_rng(SEED * 100000 + gi * 100 + r)
                    w, ina = run(pp, "T", rng)
                    acc.append(flat(period_stats(w), ina))
                d = pd.DataFrame(acc).mean()
                exp_drop = -sb * rise * (1 - rv) * 0.3 * 100   # 式：B の割合×増えた振り分け×（1−r）×もとの開く確率の平均
                grid.append(dict(scenario="T", share_b=sb, rise=rise, r=rv, k=np.nan,
                                 open_drop_pt=d.open_drop_pt, formula_drop_pt=exp_drop,
                                 b_part_of_drop=d.b_part_of_drop, cpo_change_pt=d.cpo_change_pt,
                                 delivery_rate_change_pt=(d.delivery_rate_last - d.delivery_rate_first) * 100,
                                 inactive8_change_pt=(d.inactive8_w26 - d.inactive8_w8) * 100,
                                 open_rate_B_change_pt=(d.open_rate_B_last - d.open_rate_B_first) * 100,
                                 open_rate_A_change_pt=(d.open_rate_A_last - d.open_rate_A_first) * 100))
                gi += 1
    for kk in [0.0, 1.0, 3.0, 6.0]:
        for rv in [0.0, 0.05, 0.2]:
            pp = dict(BASE, k=kk, r=rv)
            acc = []
            for r in range(10):
                rng = np.random.default_rng(SEED * 100000 + gi * 100 + r)
                w, ina = run(pp, "P", rng)
                acc.append(flat(period_stats(w), ina))
            d = pd.DataFrame(acc).mean()
            _, folder = scale_for_p(pp)
            grid.append(dict(scenario="P", share_b=np.nan, rise=np.nan, r=rv, k=kk,
                             open_drop_pt=d.open_drop_pt, formula_drop_pt=np.nan,
                             b_part_of_drop=d.b_part_of_drop, cpo_change_pt=d.cpo_change_pt,
                             delivery_rate_change_pt=(d.delivery_rate_last - d.delivery_rate_first) * 100,
                             inactive8_change_pt=(d.inactive8_w26 - d.inactive8_w8) * 100,
                             open_rate_B_change_pt=(d.open_rate_B_last - d.open_rate_B_first) * 100,
                             open_rate_A_change_pt=(d.open_rate_A_last - d.open_rate_A_first) * 100,
                             added_folder_share=folder))
            gi += 1
    grid = pd.DataFrame(grid)
    grid.round(5).to_csv(RES / "grid.csv", index=False)

    # まとめ
    def v(sc, k, scale=100, nd=2):
        return round(float(summ.loc[sc, k]) * scale, nd)
    c_p, folder_p = scale_for_p(p)
    headline = {}
    for sc in SCN:
        headline[sc] = {
            "delivery_rate_first": v(sc, "delivery_rate_first"), "delivery_rate_last": v(sc, "delivery_rate_last"),
            "open_rate_first": v(sc, "open_rate_first"), "open_rate_last": v(sc, "open_rate_last"),
            "open_drop_pt": round(float(summ.loc[sc, "open_drop_pt"]), 2),
            "open_drop_pt_p5_p95": [round(float(reps[reps.scenario == sc].open_drop_pt.quantile(q)), 2) for q in (0.05, 0.95)],
            "click_rate_first": v(sc, "click_rate_first"), "click_rate_last": v(sc, "click_rate_last"),
            "click_per_open_first": v(sc, "click_per_open_first"), "click_per_open_last": v(sc, "click_per_open_last"),
            "cpo_change_pt": round(float(summ.loc[sc, "cpo_change_pt"]), 2),
            "cpo_change_pt_p5_p95": [round(float(reps[reps.scenario == sc].cpo_change_pt.quantile(q)), 2) for q in (0.05, 0.95)],
            "open_rate_by_type_first": {k: v(sc, f"open_rate_{k}_first") for k in TYPES},
            "open_rate_by_type_last": {k: v(sc, f"open_rate_{k}_last") for k in TYPES},
            "open_change_by_type_pt": {k: round(float((summ.loc[sc, f"open_rate_{k}_last"] - summ.loc[sc, f"open_rate_{k}_first"]) * 100), 2) + 0.0 for k in TYPES},
            "b_part_of_drop": v(sc, "b_part_of_drop"),
            "inactive8_w8": v(sc, "inactive8_w8"), "inactive8_w26": v(sc, "inactive8_w26"),
            "inbox_share_first": v(sc, "inbox_share_first"), "inbox_share_last": v(sc, "inbox_share_last"),
            "inbox_open_rate_first": v(sc, "inbox_open_rate_first"), "inbox_open_rate_last": v(sc, "inbox_open_rate_last"),
        }
    gt = grid[grid.scenario == "T"]
    gp = grid[grid.scenario == "P"]
    robust = {
        "T_n": int(len(gt)),
        "T_open_drop_range": [round(gt.open_drop_pt.min(), 2), round(gt.open_drop_pt.max(), 2)],
        "T_formula_gap_max": round(float((gt.open_drop_pt - gt.formula_drop_pt).abs().max()), 2),
        "T_b_part_range": [round(gt.b_part_of_drop.min() * 100, 2), round(gt.b_part_of_drop.max() * 100, 2)],
        "T_cpo_change_range": [round(gt.cpo_change_pt.min(), 2), round(gt.cpo_change_pt.max(), 2)],
        "T_delivery_change_range": [round(gt.delivery_rate_change_pt.min(), 3), round(gt.delivery_rate_change_pt.max(), 3)],
        "T_b_share10_b_part_range": [round(gt[gt.share_b == 0.1].b_part_of_drop.min() * 100, 2),
                                     round(gt[gt.share_b == 0.1].b_part_of_drop.max() * 100, 2)],
        "T_b_share10_rise20_drop": [round(gt[(gt.share_b == 0.1) & (gt.rise == 0.2)].open_drop_pt.min(), 2),
                                    round(gt[(gt.share_b == 0.1) & (gt.rise == 0.2)].open_drop_pt.max(), 2)],
        "T_inactive8_change_range": [round(gt.inactive8_change_pt.min(), 2), round(gt.inactive8_change_pt.max(), 2)],
        "P_n": int(len(gp)),
        "P_cpo_change_by_k": {str(kk): [round(gp[gp.k == kk].cpo_change_pt.min(), 2), round(gp[gp.k == kk].cpo_change_pt.max(), 2)] for kk in [0.0, 1.0, 3.0, 6.0]},
        "P_b_part_range": [round(gp.b_part_of_drop.min() * 100, 2), round(gp.b_part_of_drop.max() * 100, 2)],
        "P_added_folder_by_k": {str(kk): round(float(gp[gp.k == kk].added_folder_share.iloc[0]) * 100, 2) for kk in [0.0, 1.0, 3.0, 6.0]},
        "P_inactive8_change_range": [round(gp.inactive8_change_pt.min(), 2), round(gp.inactive8_change_pt.max(), 2)],
    }
    base_info = {"added_folder_T": round(BASE["share_b"] * BASE["rise"] * 100, 2), "added_folder_P": round(folder_p * 100, 2),
                 "read_drop_factor_I": round(f_end_for_i(BASE), 4),
                 "formula_drop_T_pt": round(-BASE["share_b"] * BASE["rise"] * (1 - BASE["r"]) * 0.3 * 100, 2)}
    json.dump({"base": BASE, "first_weeks": [1, 8], "last_weeks": [19, 26], "base_info": base_info,
               "headline": headline, "robust": robust},
              open(RES / "a1204_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：週ごとの開封率と届いた割合（1回分）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    cols = {"T": ORANGE, "P": GREEN, "I": BLUE}
    for sc in SCN:
        g = example[example.scenario == sc].groupby("week")[["sent", "delivered", "opens"]].sum()
        ax[0].plot(g.index, g.opens / g.delivered * 100, color=cols[sc], lw=1.6, label=SCN_JA[sc])
        ax[1].plot(g.index, g.delivered / g.sent * 100, color=cols[sc], lw=1.6, label=SCN_JA[sc])
    ax[0].set_ylim(0, 35)
    ax[0].set_title("開封率は3つとも同じだけ下がる（そう置いた）")
    ax[0].set_ylabel("開封率（%）")
    ax[1].set_ylim(0, 105)
    ax[1].set_title("届いた割合は3つとも変わらない（線が重なる）")
    ax[1].set_ylabel("届いた通数÷送った通数（%）")
    for a in ax:
        a.set_xlabel("送った週")
        a.axvspan(8, 18, color=LIGHT, alpha=0.3, lw=0)
    ax[0].legend(fontsize=8.5, frameon=False, loc="lower left")
    ax[0].text(13, 33, "変わっていく週", ha="center", fontsize=8, color=GRAY)
    save(fig, "a1204_weekly.png", SRC)

    # 図2：サービスごとの開封率の変化（ポイント、100回の平均）
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(3)
    wdt = 0.26
    for i, sc in enumerate(SCN):
        vals = [(summ.loc[sc, f"open_rate_{k}_last"] - summ.loc[sc, f"open_rate_{k}_first"]) * 100 for k in TYPES]
        ax.bar(x + (i - 1) * wdt, vals, wdt, color=cols[sc], label=SCN_JA[sc])
        for xi, vi in zip(x, vals):
            lbl = f"{vi:.2f}".replace("-0.00", "0.00")
            ax.text(xi + (i - 1) * wdt, vi - 0.4, lbl, ha="center", va="top", fontsize=8)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(["サービスA（会員の50%）", "サービスB（30%）", "サービスC（20%）"])
    ax.set_ylim(-20, 1.5)
    ax.set_ylabel("開封率の変化（ポイント、後の8週−前の8週）")
    ax.set_title("サービスごとに分けると、Bで振り分けが増えた場合だけ形が違う")
    ax.legend(fontsize=8.5, frameon=False, loc="lower left")
    save(fig, "a1204_by_type.png", SRC)

    # 図3：開いた人あたりのクリックの変化と、8週続けて開いていない人の割合
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    lab = ["サービスBで\n振り分けが増える", "開かない人ほど\n振り分けられる", "読む気が落ちる"]
    v1 = [summ.loc[s, "cpo_change_pt"] for s in SCN]
    ax[0].bar(range(3), v1, color=[cols[s] for s in SCN])
    for i, vi in enumerate(v1):
        ax[0].text(i, vi + (0.05 if vi >= 0 else -0.05), f"{vi:+.2f}", ha="center", va="bottom" if vi >= 0 else "top", fontsize=9)
    ax[0].axhline(0, color=INK, lw=0.8)
    ax[0].set_ylim(-0.6, 1.6)
    ax[0].set_xticks(range(3))
    ax[0].set_xticklabels(lab, fontsize=8.5)
    ax[0].set_ylabel("開いた通数あたりのクリックの変化（ポイント）")
    ax[0].set_title("開いた人あたりのクリックが上がるのは1つだけ")
    a8 = [summ.loc[s, "inactive8_w8"] * 100 for s in SCN]
    a26 = [summ.loc[s, "inactive8_w26"] * 100 for s in SCN]
    ax[1].bar(np.arange(3) - 0.2, a8, 0.4, color=GRAY, label="8週目")
    ax[1].bar(np.arange(3) + 0.2, a26, 0.4, color=[cols[s] for s in SCN], label="26週目（色は場面）")
    for i in range(3):
        ax[1].text(i - 0.2, a8[i] + 0.5, f"{a8[i]:.2f}", ha="center", fontsize=8)
        ax[1].text(i + 0.2, a26[i] + 0.5, f"{a26[i]:.2f}", ha="center", fontsize=8)
    ax[1].set_ylim(0, 30)
    ax[1].set_xticks(range(3))
    ax[1].set_xticklabels(lab, fontsize=8.5)
    ax[1].set_ylabel("直前の8週に1回も開いていない人（%）")
    ax[1].set_title("開いていない人は、3つとも増える")
    ax[1].legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1204_cpo_inactive.png", SRC)
    print(json.dumps(headline, ensure_ascii=False))
    print(json.dumps(robust, ensure_ascii=False))
    print(base_info)
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
