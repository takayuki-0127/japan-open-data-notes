"""1026 キャンセル待ちの人は、何人いればよいのか？（架空のデータ）

架空の染め物教室（1回の定員10人、予約はいつも満席）。予約した人はそれぞれ作成者が置いた確率で取り消し、
取り消しの時期は「3日以上前」「前日（1〜2日前）」「当日」に分かれる。空いた席は、キャンセル待ちの列の
先頭から順に連絡して埋め直す。連絡を受けた人が席を受ける確率は時期ごとに置き、連絡できる人数は
前日なら3人、当日なら1人まで（3日以上前は列が尽きるまで）。断った人・受けた人は列から外れる。
キャンセル待ちの人数 W を変えて、「空いた席のうち埋め直せた割合」「待った人のうち席がもらえた割合」を数える。
何人にすべきかの助言ではなく、物差しを比べるためのもの。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1026
SRC = "架空の染め物教室の予約とキャンセル待ち（作成者が乱数で作成、seed 1026）"
CAP = 10
N_SIM = 100000
W_LIST = list(range(0, 21))
W_INF = 1000
BASE = {"cancel": 0.15, "timing": (0.5, 0.3, 0.2), "accept": (0.6, 0.4, 0.2), "limit": (None, 3, 1)}
TNAME = ["3日以上前", "前日", "当日"]


def ceiling(timing, accept, limit):
    """列が尽きないときに埋め直せる割合（式）：時期ごとに 1−(1−受ける確率)^(連絡できる人数)"""
    s = 0.0
    for t, a, l in zip(timing, accept, limit):
        s += t * (1.0 if l is None else 1 - (1 - a) ** l)
    return s


def simulate(rng, W, cancel, timing, accept, limit, n=N_SIM, keep=False):
    n_cancel = rng.binomial(CAP, cancel, n)
    # 時期ごとの取り消しの人数（多項分布を二項分布の積み重ねで引く）
    if True:
        c0 = rng.binomial(n_cancel, timing[0])
        c1 = rng.binomial(n_cancel - c0, timing[1] / (timing[1] + timing[2]) if timing[1] + timing[2] > 0 else 0)
        cnt = np.stack([c0, c1, n_cancel - c0 - c1], 1)
    R = np.full(n, W)
    filled = np.zeros((n, 3), dtype=int)
    contacts = np.zeros(n, dtype=int)
    for t in range(3):
        a, l = accept[t], limit[t]
        for j in range(int(cnt[:, t].max()) if n else 0):
            act = (cnt[:, t] > j) & (R > 0)
            if not act.any():
                continue
            K = rng.geometric(a, n)  # 何人目で受けてもらえるか
            cap_k = R if l is None else np.minimum(R, l)
            ok = act & (K <= cap_k)
            used = np.where(ok, K, np.where(act, cap_k, 0))
            filled[:, t] += ok
            R = R - used
            contacts += used
    out = {"cancelled": n_cancel, "filled": filled.sum(1), "cnt": cnt, "filled_t": filled, "contacts": contacts}
    if keep:
        df = pd.DataFrame({"session": np.arange(1, n + 1), "waitlist": W, "cancel_early": cnt[:, 0], "cancel_daybefore": cnt[:, 1],
                           "cancel_sameday": cnt[:, 2], "refilled": filled.sum(1), "contacted": contacts,
                           "empty_seats": n_cancel - filled.sum(1)})
        return out, df
    return out


def summarize(o, W):
    c, f = o["cancelled"], o["filled"]
    has = c > 0
    r = {"waitlist": W, "refill_share": round(float(f.sum() / c.sum()) * 100, 2),
         "all_refilled_sessions": round(float((f[has] == c[has]).mean()) * 100, 2),
         "seated_share_of_waitlist": round(float(f.mean() / W) * 100, 2) if W > 0 else None,
         "empty_mean": round(float((c - f).mean()), 3), "contacts_mean": round(float(o["contacts"].mean()), 3)}
    for t in range(3):
        r[f"refill_share_{['early', 'daybefore', 'sameday'][t]}"] = round(float(o["filled_t"][:, t].sum() / max(o["cnt"][:, t].sum(), 1)) * 100, 2)
    return r


def curve(seed, cancel, timing, accept, limit, n=N_SIM):
    rows = []
    for i, W in enumerate(W_LIST + [W_INF]):
        o = simulate(np.random.default_rng(seed + i), W, cancel, timing, accept, limit, n)
        rows.append(summarize(o, W))
    return pd.DataFrame(rows)


def need(df, target):
    """埋め直せた割合が target 以上になる最小の人数（20人までで届かなければ None）"""
    d = df[(df.waitlist <= 20) & (df.refill_share >= target)]
    return None if d.empty else int(d.waitlist.min())


def main():
    t0 = time.time()
    b = BASE
    ceil_f = ceiling(b["timing"], b["accept"], b["limit"])
    res = {"setting": {"capacity": CAP, **{k: (list(v) if isinstance(v, tuple) else v) for k, v in b.items()}, "n_sim": N_SIM},
           "mean_cancel_formula": round(CAP * b["cancel"], 3), "ceiling_formula": round(ceil_f * 100, 2),
           "ceiling_by_timing_formula": {n: round((1.0 if l is None else 1 - (1 - a) ** l) * 100, 2)
                                         for n, a, l in zip(TNAME, b["accept"], b["limit"])}}
    base = curve(SEED * 100, b["cancel"], b["timing"], b["accept"], b["limit"])
    base.to_csv(RES / "base_by_waitlist.csv", index=False)
    inf = base[base.waitlist == W_INF].iloc[0]
    res["ceiling_sim_W1000"] = float(inf.refill_share)
    ceil_pct = ceil_f * 100
    res["by_waitlist"] = base[base.waitlist.isin([1, 2, 3, 5, 8, 10, 15, 20, W_INF])].set_index("waitlist").to_dict(orient="index")
    t90 = round(ceil_pct * 0.9, 2)
    w90 = need(base, t90)
    res["target_90pct_of_ceiling"] = t90
    res["need_90pct_of_ceiling"] = w90
    res["seated_share_at_need90"] = float(base[base.waitlist == w90].seated_share_of_waitlist.iloc[0]) if w90 else None
    w_naive = int(np.ceil(CAP * b["cancel"] - 1e-9))
    res["naive_W_equal_mean_cancel"] = w_naive
    res["refill_at_naive"] = float(base[base.waitlist == w_naive].refill_share.iloc[0])
    res["refill_at_naive_over_ceiling"] = round(res["refill_at_naive"] / ceil_pct * 100, 2)
    res["mean_cancel_sim"] = round(float(base.empty_mean.iloc[0]), 3)

    # 1回分のデータ（基本、キャンセル待ち2人、1,000回）
    _, one = simulate(np.random.default_rng(SEED), 2, b["cancel"], b["timing"], b["accept"], b["limit"], n=1000, keep=True)
    one.to_csv(DATA / "sessions_w2.csv", index=False)
    res["one_run_w2_1000"] = {"sessions_with_cancel": int((one[["cancel_early", "cancel_daybefore", "cancel_sameday"]].sum(1) > 0).sum()),
                              "cancelled": int(one[["cancel_early", "cancel_daybefore", "cancel_sameday"]].values.sum()),
                              "refilled": int(one.refilled.sum()), "empty_seats": int(one.empty_seats.sum())}

    # 確かめ：取り消しの率×席を受ける確率×遅い取り消しの多さ（27通り、各3万回）
    grid = []
    j = 0
    timings = {"遅い取り消しが少ない": (0.7, 0.2, 0.1), "基本": (0.5, 0.3, 0.2), "遅い取り消しが多い": (0.3, 0.35, 0.35)}
    for c in [0.08, 0.15, 0.25]:
        for sc in [0.6, 1.0, 1.4]:
            acc = tuple(min(a * sc, 0.95) for a in b["accept"])
            for tn, tm in timings.items():
                df = curve(SEED * 10000 + j * 100, c, tm, acc, b["limit"], n=30000); j += 1
                cf = ceiling(tm, acc, b["limit"]) * 100
                wn = int(np.ceil(CAP * c - 1e-9))
                w9 = need(df, cf * 0.9)
                grid.append({"cancel": c, "accept_scale": sc, "accept_early": round(acc[0], 2), "timing": tn,
                             "mean_cancel": round(CAP * c, 2), "ceiling_formula": round(cf, 2),
                             "ceiling_sim_W1000": float(df[df.waitlist == W_INF].refill_share.iloc[0]),
                             "naive_W": wn, "refill_at_naive": float(df[df.waitlist == wn].refill_share.iloc[0]),
                             "refill_at_naive_over_ceiling": round(float(df[df.waitlist == wn].refill_share.iloc[0]) / cf * 100, 2),
                             "need_90pct_of_ceiling": w9,
                             "need_over_mean_cancel": round(w9 / (CAP * c), 2) if w9 else None,
                             "seated_share_at_need90": float(df[df.waitlist == w9].seated_share_of_waitlist.iloc[0]) if w9 else None})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    g9 = grid.dropna(subset=["need_90pct_of_ceiling"])
    res["grid_range"] = {
        "ceiling_formula": [float(grid.ceiling_formula.min()), float(grid.ceiling_formula.max())],
        "max_abs_sim_minus_formula_ceiling_pt": round(float((grid.ceiling_sim_W1000 - grid.ceiling_formula).abs().max()), 2),
        "refill_at_naive": [float(grid.refill_at_naive.min()), float(grid.refill_at_naive.max())],
        "refill_at_naive_over_ceiling": [float(grid.refill_at_naive_over_ceiling.min()), float(grid.refill_at_naive_over_ceiling.max())],
        "need_90pct_of_ceiling": [int(g9.need_90pct_of_ceiling.min()), int(g9.need_90pct_of_ceiling.max())],
        "need_not_reached_within_20": int(grid.need_90pct_of_ceiling.isna().sum()),
        "need_over_mean_cancel": [float(g9.need_over_mean_cancel.min()), float(g9.need_over_mean_cancel.max())],
        "seated_share_at_need90": [float(g9.seated_share_at_need90.min()), float(g9.seated_share_at_need90.max())],
        "need_gt_mean_cancel_all": bool((g9.need_90pct_of_ceiling > g9.mean_cancel).all()),
        "n_cases": int(len(grid)),
    }
    with open(RES / "a1026_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：キャンセル待ちの人数と、2つの物差し
    d = base[base.waitlist <= 20]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.plot(d.waitlist, d.refill_share, color=BLUE, marker="o", ms=4, label="空いた席のうち埋め直せた割合")
    ax.plot(d.waitlist[1:], d.seated_share_of_waitlist[1:], color=ORANGE, marker="s", ms=4, label="キャンセル待ちの人のうち席がもらえた割合")
    ax.axhline(ceil_pct, color=GRAY, ls="--", lw=1)
    ax.text(20, ceil_pct + 1.5, f"列が尽きないときの上限 {ceil_pct:.2f}%（式どおり）", ha="right", fontsize=9, color=INK)
    ax.axvline(w_naive, color=GRAY, ls=":", lw=1)
    ax.text(w_naive + 0.2, 3, f"平均の取り消し{CAP * b['cancel']:.1f}人を切り上げた{w_naive}人", fontsize=9, color=INK)
    ax.set_xlabel("キャンセル待ちの人数"); ax.set_ylabel("%"); ax.set_ylim(0, 105); ax.set_xticks(range(0, 21, 2))
    ax.legend(frameon=False, fontsize=9, loc="center right")
    ax.set_title("待つ人を増やすと埋め直しは上限に近づき、席をもらえる人の割合は下がる（定員10人）")
    save(fig, "a1026_curve.png", SRC)

    # 図2：取り消しの時期ごとの埋め直し（W=2・5・列が尽きない）
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    keys = ["refill_share_early", "refill_share_daybefore", "refill_share_sameday"]
    x = np.arange(3); w = 0.27
    for i, (W, c) in enumerate([(2, LIGHT), (5, BLUE), (W_INF, INK)]):
        v = base[base.waitlist == W][keys].values[0]
        lab = "列が尽きない（1,000人）" if W == W_INF else f"キャンセル待ち{W}人"
        ax.bar(x + (i - 1) * w, v, w, color=c, label=lab)
        for xi, vi in zip(x, v):
            ax.text(xi + (i - 1) * w, vi + 1.2, f"{vi:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"{n}の取り消し（{int(t * 100)}%）" for n, t in zip(TNAME, b["timing"])])
    ax.set_ylabel("埋め直せた割合（%）"); ax.set_ylim(0, 108)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.set_title("当日の取り消しは、待つ人が何人いてもほとんど埋まらない")
    save(fig, "a1026_timing.png", SRC, y=-0.08)

    # 図3：27通りで、上限の9割に届く人数と平均の取り消し
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    for tn, c, mk in [("遅い取り消しが少ない", GREEN, "s"), ("基本", BLUE, "o"), ("遅い取り消しが多い", ORANGE, "^")]:
        g = g9[g9.timing == tn]
        jit = {0.6: -0.08, 1.0: 0.0, 1.4: 0.08}
        ax.scatter(g.mean_cancel + g.accept_scale.map(jit), g.need_90pct_of_ceiling, color=c, marker=mk, s=36, label=tn)
    xx = np.array([0.5, 2.8]); ax.plot(xx, xx, color=GRAY, ls="--", lw=1)
    ax.text(2.8, 1.9, "平均の取り消しと同じ人数", fontsize=9, color=INK, ha="right", va="top")
    ax.set_xticks([0.8, 1.5, 2.5]); ax.set_xlabel("平均の取り消し（人、取り消しの率8・15・25%）\n各列の中は、左から席を受ける確率0.6倍・基本・1.4倍")
    ax.set_ylabel("上限の9割に届くキャンセル待ちの人数")
    ax.legend(frameon=False, fontsize=9, title="取り消しの時期", title_fontsize=9)
    ax.set_title("置き方を変えた27通り：上限の9割に届く人数は、平均の取り消しより多い")
    save(fig, "a1026_grid.png", SRC, y=-0.07)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
