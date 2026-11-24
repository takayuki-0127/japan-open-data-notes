"""1159 問い合わせの一部を抜き出して当たり率を見積もると、置き場所を小さくして試した値はどれだけずれるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ10万件への問い合わせ100万件（i番目に人気のデータが選ばれる確率は 1÷i^a に比例、基本 a=0.8）。
置き場所（キャッシュ）は件数で数え、いっぱいなら、いちばん長く使われていないものを捨てる。
本当の当たり率：100万件をそのまま流して数える（はじめの20%は置き場所を埋めるために使い、残り80%で数える）。
抜き出し方（割合 s＝10%・1%、それぞれ20回抜き出し直す）：
 ① 問い合わせを1件ずつ s の確率で抜き出し、置き場所も s 倍に小さくして試す
 ② データを s の確率で選び、選んだデータへの問い合わせをすべて残し、置き場所も s 倍に小さくして試す
 ③ 問い合わせを1件ずつ s の確率で抜き出し、置き場所の大きさはそのままで試す
確かめ：(a) 偏り a=0.6・1.0、(b) 同じデータが続けて来る傾き（3割の問い合わせが直前50件のどれかをもう一度取りに来る）を入れた列
"""
import json
import time
from collections import OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1159
SRC = "架空のアプリへの問い合わせ（作成者が置いた人気の偏りからの乱数、seed 1159）"
N_ITEMS = 100_000
N_REQ = 1_000_000
WARM_FRAC = 0.2
SIZES_PCT = [1, 4, 16]
RATES = [0.10, 0.01]
REPS = 20
BASE_A = 0.8
REPEAT_Q, REPEAT_WIN = 0.3, 50
METHODS = {"req_shrink": "① 1件ずつ抜き出し・置き場所も小さく",
           "item_shrink": "② データごとに抜き出し・置き場所も小さく",
           "req_same": "③ 1件ずつ抜き出し・置き場所はそのまま"}
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def probs(n, a):
    p = 1.0 / np.arange(1, n + 1) ** a
    return p / p.sum()


def stream(rng, p, n):
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    return np.searchsorted(cdf, rng.random(n), side="right") + 1


def stream_repeat(rng, p, n):
    """3割の問い合わせは、直前50件のどれかをもう一度取りに来る"""
    base = stream(rng, p, n)
    rep = rng.random(n) < REPEAT_Q
    back = rng.integers(1, REPEAT_WIN + 1, n)
    x = base.tolist()
    rl, bl = rep.tolist(), back.tolist()
    for i in range(REPEAT_WIN, n):
        if rl[i]:
            x[i] = x[i - bl[i]]
    return np.array(x)


def recent_hit(seq, cap, warm):
    cap = max(int(cap), 1)
    c = OrderedDict()
    hits = 0
    for i, x in enumerate(seq.tolist()):
        if x in c:
            c.move_to_end(x)
            if i >= warm:
                hits += 1
        else:
            c[x] = None
            if len(c) > cap:
                c.popitem(last=False)
    return hits / max(len(seq) - warm, 1)


def estimates(rng, seq, s, sizes, methods=("req_shrink", "item_shrink", "req_same")):
    """抜き出した列で当たり率を出す。時間の上ではじめの20%に当たる問い合わせは数えない"""
    n = len(seq)
    pos = np.arange(n)
    res = {}
    keep_req = rng.random(n) < s
    res["n_req_kept"] = int(keep_req.sum())
    res["n_req_measured"] = int((keep_req & (pos >= int(n * WARM_FRAC))).sum())
    chosen = rng.random(N_ITEMS + 1) < s
    keep_item = chosen[seq]
    for m in methods:
        keep = keep_item if m == "item_shrink" else keep_req
        sub = seq[keep]
        warm = int((pos[keep] < int(n * WARM_FRAC)).sum())
        for sz in sizes:
            cap = N_ITEMS * sz / 100
            cap = cap if m == "req_same" else cap * s
            res[(m, sz)] = recent_hit(sub, round(cap), warm)
    return res, keep_item.mean()


def summarize(est_rows, truth):
    df = pd.DataFrame(est_rows)
    out = []
    for (m, s, sz), g in df.groupby(["method", "rate", "size_pct"], sort=False):
        t = truth[sz]
        e = g.est_pct.values
        out.append({"method": m, "method_name": METHODS[m], "rate_pct": r(s * 100, 1), "size_pct": sz,
                    "true_hit_pct": t, "est_mean_pct": r(e.mean(), 2), "bias_pt": r(e.mean() - t, 2),
                    "est_p10_pct": r(np.percentile(e, 10), 2), "est_p90_pct": r(np.percentile(e, 90), 2),
                    "est_min_pct": r(e.min(), 2), "est_max_pct": r(e.max(), 2),
                    "within_2pt_share_pct": r(np.mean(np.abs(e - t) <= 2) * 100, 1)})
    return pd.DataFrame(out)


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"items": N_ITEMS, "requests": N_REQ, "warm_frac": WARM_FRAC, "sizes_pct": SIZES_PCT,
                       "rates": RATES, "reps": REPS, "alpha": BASE_A, "repeat_q": REPEAT_Q, "repeat_window": REPEAT_WIN}}
    warm_full = int(N_REQ * WARM_FRAC)

    # 基本
    p = probs(N_ITEMS, BASE_A)
    seq = stream(rng, p, N_REQ)
    truth = {sz: r(recent_hit(seq, N_ITEMS * sz // 100, warm_full) * 100, 2) for sz in SIZES_PCT}
    print("truth", truth, round(time.time() - T0, 1), flush=True)
    rows, cover = [], []
    for s in RATES:
        for k in range(REPS):
            res, cov = estimates(rng, seq, s, SIZES_PCT)
            cover.append({"rate_pct": r(s * 100, 1), "rep": k + 1, "kept_request_share_pct": r(cov * 100, 3),
                          "req_sample_kept": res.pop("n_req_kept"), "req_sample_measured": res.pop("n_req_measured")})
            for (m, sz), h in res.items():
                rows.append({"method": m, "rate": s, "size_pct": sz, "rep": k + 1, "est_pct": r(h * 100, 2)})
        print("rate", s, round(time.time() - T0, 1), flush=True)
    est = pd.DataFrame(rows)
    cov = pd.DataFrame(cover)
    est = est.merge(cov.assign(rate=cov.rate_pct / 100)[["rate", "rep", "kept_request_share_pct"]], on=["rate", "rep"])
    est["rate_pct"] = (est.rate * 100).round(1)
    est.drop(columns="rate").to_csv(RES / "estimates_base.csv", index=False)
    sm = summarize(rows, truth)
    sm.to_csv(RES / "summary_base.csv", index=False)
    out["truth_pct"] = {str(k): v for k, v in truth.items()}
    # 小さい置き場所の本当の当たり率（①が実際に見ているもの）
    small_truth = {}
    for s in RATES:
        for sz in SIZES_PCT:
            small_truth[f"{sz}%x{s*100:g}%"] = r(recent_hit(seq, max(round(N_ITEMS * sz / 100 * s), 1), warm_full) * 100, 2)
    out["truth_small_cache_full_stream_pct"] = small_truth
    out["summary_base"] = sm.drop(columns="method_name").to_dict("records")

    # ②の振れ：抜き出したデータに入った問い合わせの割合と見積もり
    it = est[(est.method == "item_shrink")]
    cc = []
    for (s, sz), g in it.groupby(["rate_pct", "size_pct"]):
        cc.append({"rate_pct": s, "size_pct": sz,
                   "corr_kept_share_vs_est": r(np.corrcoef(g.kept_request_share_pct, g.est_pct)[0, 1], 3),
                   "kept_share_min_pct": r(g.kept_request_share_pct.min(), 2), "kept_share_max_pct": r(g.kept_request_share_pct.max(), 2)})
    out["item_shrink_kept_share"] = cc
    top10 = probs(N_ITEMS, BASE_A)[:10].sum()
    out["req_sample_size_mean"] = {f"{s*100:g}%": {"kept": r(cov[cov.rate_pct == r(s * 100, 1)].req_sample_kept.mean(), 1),
                                                  "measured": r(cov[cov.rate_pct == r(s * 100, 1)].req_sample_measured.mean(), 1)} for s in RATES}
    out["top10_items_request_share_pct"] = r(top10 * 100, 2)
    out["top1_item_request_share_pct"] = r(probs(N_ITEMS, BASE_A)[0] * 100, 2)

    # 確かめ：偏り・続けて来る傾き（抜き出し10%と1%、置き場所4%、10回）
    chk = []
    for label, a, rep_on in [("a=0.6", 0.6, False), ("a=1.0", 1.0, False), ("続けて来る傾きあり（a=0.8）", 0.8, True)]:
        pp = probs(N_ITEMS, a)
        sq = stream_repeat(rng, pp, N_REQ) if rep_on else stream(rng, pp, N_REQ)
        t = r(recent_hit(sq, N_ITEMS * 4 // 100, warm_full) * 100, 2)
        rr = []
        for s in RATES:
            for k in range(10):
                res, _ = estimates(rng, sq, s, [4])
                res.pop("n_req_kept"); res.pop("n_req_measured")
                for (m, sz), h in res.items():
                    rr.append({"method": m, "rate": s, "size_pct": sz, "rep": k + 1, "est_pct": r(h * 100, 2)})
        smc = summarize(rr, {4: t})
        smc.insert(0, "case", label)
        chk.append(smc)
        print(label, round(time.time() - T0, 1), flush=True)
    chk = pd.concat(chk)
    chk.to_csv(RES / "check_cases.csv", index=False)
    out["check_cases"] = chk.drop(columns="method_name").to_dict("records")
    allb = pd.concat([sm.assign(case="基本（a=0.8）"), chk])
    out["bias_range_by_method_pt"] = {m: [float(allb[allb.method == m].bias_pt.min()), float(allb[allb.method == m].bias_pt.max())]
                                      for m in METHODS}
    out["bias_range_n_by_method"] = {m: int((allb.method == m).sum()) for m in METHODS}

    # データ：基本の列の先頭2万件と、1回目の抜き出しで残ったか
    pd.DataFrame({"request_id": np.arange(1, 20001), "item_rank": seq[:20000]}).to_csv(DATA / "requests_head.csv", index=False)
    cov.to_csv(DATA / "item_sample_kept_share.csv", index=False)

    # 図1：置き場所4%の見積もり（10〜90%の範囲）
    fig, axs = plt.subplots(1, 2, figsize=(9.4, 4.2), sharey=True)
    for ax, s in zip(axs, [10.0, 1.0]):
        g = sm[(sm.size_pct == 4) & (sm.rate_pct == s)].set_index("method").loc[list(METHODS)]
        x = np.arange(3)
        cols = [ORANGE, BLUE, GRAY]
        ax.bar(x, g.est_mean_pct, color=cols)
        ax.errorbar(x, g.est_mean_pct, yerr=[g.est_mean_pct - g.est_p10_pct, g.est_p90_pct - g.est_mean_pct],
                    fmt="none", ecolor=INK, capsize=4, lw=1)
        for i, v in enumerate(g.est_mean_pct):
            ax.text(i + 0.08, v / 2, f"{v:.2f}%", ha="left", fontsize=8.5, color="white" if i < 2 else INK)
        ax.axhline(truth[4], color=INK, lw=1, ls="--")
        ax.text(2.45, truth[4] + 1, f"本当 {truth[4]:.2f}%", ha="right", fontsize=8.5)
        ax.set_xticks(x, ["①1件ずつ\n＋小さく", "②データごと\n＋小さく", "③1件ずつ\n＋そのまま"], fontsize=8.5)
        ax.set_title(f"抜き出し {s:g}%", fontsize=11)
    axs[0].set_ylim(0, truth[4] * 1.5)
    axs[0].set_ylabel("見積もった当たり率（20回の平均、%）")
    fig.suptitle("置き場所を全体の4%と見込んだときの見積もり（線は20回の10〜90%）", fontsize=11)
    fig.tight_layout()
    save(fig, "a1159_methods.png", SRC)

    # 図2：②の振れと、抜き出したデータに入った問い合わせの割合
    fig, ax = plt.subplots(figsize=(7, 4.2))
    g = it[(it.rate_pct == 1.0) & (it.size_pct == 4)]
    ax.scatter(g.kept_request_share_pct, g.est_pct, color=BLUE, s=22)
    ax.axhline(truth[4], color=INK, lw=1, ls="--")
    ax.text(g.kept_request_share_pct.max(), truth[4] + 0.6, f"本当 {truth[4]:.2f}%", ha="right", fontsize=8.5)
    ax.axvline(1.0, color=GRAY, lw=0.8, ls=":")
    ax.set_xlabel("選んだデータへの問い合わせが全体に占めた割合（%）")
    ax.set_ylabel("②の見積もり（%）")
    ax.set_ylim(0, max(g.est_pct.max(), truth[4]) * 1.15)
    ax.set_xlim(0, None)
    ax.set_title("②データごと1%・置き場所4%の20回")
    save(fig, "a1159_item_spread.png", SRC)

    # 図3：確かめ（ずれの平均、抜き出し10%・置き場所4%）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    cases = ["基本（a=0.8）", "a=0.6", "a=1.0", "続けて来る傾きあり（a=0.8）"]
    b10 = allb[(allb.rate_pct == 10.0) & (allb.size_pct == 4)]
    w = 0.26
    for j, (m, col) in enumerate(zip(METHODS, [ORANGE, BLUE, GRAY])):
        v = [b10[(b10.case == c) & (b10.method == m)].bias_pt.iloc[0] for c in cases]
        ax.bar(np.arange(4) + (j - 1) * w, v, w, color=col, label=METHODS[m])
        for i, vv in enumerate(v):
            ax.text(i + (j - 1) * w, vv + (0.5 if vv >= 0 else -0.5), f"{vv:.2f}", ha="center",
                    va="bottom" if vv >= 0 else "top", fontsize=7)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(np.arange(4), ["基本\n（a=0.8）", "偏り\na=0.6", "偏り\na=1.0", "続けて来る\n傾きあり"], fontsize=9)
    lo = b10.bias_pt.min()
    ax.set_ylim(lo * 1.25, max(b10.bias_pt.max(), 0) + 6)
    ax.set_ylabel("見積もり − 本当（ポイント）")
    ax.set_title("抜き出し10%・置き場所4%のずれ（平均）")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    save(fig, "a1159_check.png", SRC)

    (RES / "a1159_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.item()))
    print(sm.to_string())
    print(chk.drop(columns="method_name").to_string())
    print(json.dumps({k: out[k] for k in ["truth_pct", "truth_small_cache_full_stream_pct", "item_shrink_kept_share", "bias_range_by_method_pt", "top10_items_request_share_pct", "top1_item_request_share_pct"]}, ensure_ascii=False, default=lambda o: o.item()))
    print("sec", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
