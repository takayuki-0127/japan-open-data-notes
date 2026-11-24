"""1151 当たり率を件数で数えるかデータの量で数えるかで、良し悪しはどう入れかわるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ2万件（大きさはKBで、中央値50KB・対数の標準偏差1.2の対数で正規の形）への問い合わせの列。
i番目に人気のデータが選ばれる確率は 1÷i^0.8 に比例。置き場所（キャッシュ）は量（KB）で数え、全データの合計の3%と置いた。
3つの捨て方・置き方を比べる。
  ①いちばん長く使われていないものから捨てる（なんでも置く）
  ②①と同じだが、大きさが上位10%に入る大きいデータは置かない
  ③いちばん大きいものから捨てる
当たり率は2通りで数える：件数の当たり率＝当たった件数÷問い合わせの件数、量の当たり率＝当たった量÷問い合わせた量。
確かめ：大きさと人気の関係（人気ほど小さい・関係なし・人気ほど大きい）×置き場所の大きさ（1・3・10%）×大きさの散らばり（0.8・1.6）の18通り。
"""
import json
import time
import heapq
from statistics import NormalDist
from collections import OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1151
SRC = "架空のアプリへの問い合わせ（作成者が置いた人気の偏りとデータの大きさからの乱数、seed 1151）"
N_ITEMS = 20_000
ALPHA = 0.8
MED_KB = 50.0
BASE = {"rho": 0.0, "cap_pct": 3, "sig": 1.2}
RHOS = [-0.5, 0.0, 0.5]
CAPS = [1, 3, 10]
SIGS = [0.8, 1.6]
WARM, MEAS = 40_000, 160_000
BIG_Q = 0.90
POL = ["①古いものから捨てる", "②大きいものは置かない", "③大きいものから捨てる"]
RHO_NAME = {-0.5: "人気ほど小さい", 0.0: "関係なし", 0.5: "人気ほど大きい"}


def r(x, d=4):
    return round(float(x), d)


def make_items(rng, rho, sig):
    p = 1.0 / np.arange(1, N_ITEMS + 1) ** ALPHA
    p /= p.sum()
    nd = NormalDist()
    z = np.array([nd.inv_cdf(1 - (k - 0.5) / N_ITEMS) for k in range(1, N_ITEMS + 1)])  # 人気の順位を正規の目盛りに（人気ほど大きい）
    e = rng.standard_normal(N_ITEMS)
    size = MED_KB * np.exp(sig * (rho * z + np.sqrt(1 - rho ** 2) * e))
    return p, size


def stream(rng, p, n):
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    return np.searchsorted(cdf, rng.random(n), side="right")


def sim_recent(seq, size, cap, warm, limit=np.inf):
    c, used = OrderedDict(), 0.0
    hn = hb = rb = 0.0
    for i, x in enumerate(seq.tolist()):
        s = size[x]
        if i >= warm:
            rb += s
        if x in c:
            c.move_to_end(x)
            if i >= warm:
                hn += 1
                hb += s
        elif s <= limit and s <= cap:
            while used + s > cap:
                _, v = c.popitem(last=False)
                used -= v
            c[x] = s
            used += s
    n = len(seq) - warm
    return hn / n, hb / rb


def sim_big_first(seq, size, cap, warm):
    inside, heap, used = set(), [], 0.0
    hn = hb = rb = 0.0
    for i, x in enumerate(seq.tolist()):
        s = size[x]
        if i >= warm:
            rb += s
        if x in inside:
            if i >= warm:
                hn += 1
                hb += s
        elif s <= cap:
            while used + s > cap:
                _, y = heapq.heappop(heap)
                inside.discard(y)
                used -= size[y]
            inside.add(x)
            heapq.heappush(heap, (-s, x))
            used += s
    n = len(seq) - warm
    return hn / n, hb / rb


def one_setting(rng, rho, cap_pct, sig, keep=False):
    p, size = make_items(rng, rho, sig)
    seq = stream(rng, p, WARM + MEAS)
    cap = size.sum() * cap_pct / 100
    lim = np.quantile(size, BIG_Q)
    res = [sim_recent(seq, size, cap, WARM), sim_recent(seq, size, cap, WARM, lim), sim_big_first(seq, size, cap, WARM)]
    rows = []
    for name, (hn, hb) in zip(POL, res):
        rows.append({"size_popularity": RHO_NAME[rho], "rho": rho, "cap_pct": cap_pct, "size_logsd": sig,
                     "policy": name, "hit_count_pct": r(hn * 100, 2), "hit_bytes_pct": r(hb * 100, 2)})
    extra = None
    if keep:
        extra = {"p": p, "size": size, "seq": seq, "limit_kb": lim, "cap_kb": cap,
                 "mean_req_kb": float((p * size).sum()), "mean_item_kb": float(size.mean())}
    return rows, extra


def rank_str(df, col):
    return ">".join(df.sort_values(col, ascending=False).policy.str[0].tolist())


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setting": {"items": N_ITEMS, "alpha": ALPHA, "median_kb": MED_KB, "base": BASE, "warmup": WARM,
                       "measured": MEAS, "big_quantile": BIG_Q}}

    # 基本
    rows, ex = one_setting(rng, BASE["rho"], BASE["cap_pct"], BASE["sig"], keep=True)
    b = pd.DataFrame(rows)
    b.to_csv(RES / "base_policies.csv", index=False)
    out["base"] = b.to_dict("records")
    out["base_rank_count"] = rank_str(b, "hit_count_pct")
    out["base_rank_bytes"] = rank_str(b, "hit_bytes_pct")
    out["base_detail"] = {"cap_kb": r(ex["cap_kb"], 1), "big_limit_kb": r(ex["limit_kb"], 2),
                          "mean_requested_kb": r(ex["mean_req_kb"], 2), "mean_item_kb": r(ex["mean_item_kb"], 2)}
    # 大きいデータ（上位10%）が問い合わせの件数と量に占める割合
    size, seq = ex["size"], ex["seq"][WARM:]
    big = size[seq] > ex["limit_kb"]
    out["base_detail"]["big_share_of_requests_pct"] = r(big.mean() * 100, 2)
    out["base_detail"]["big_share_of_bytes_pct"] = r(size[seq][big].sum() / size[seq].sum() * 100, 2)
    pd.DataFrame({"item_rank": np.arange(1, N_ITEMS + 1), "prob_pct": np.round(ex["p"] * 100, 6),
                  "size_kb": np.round(size, 3)}).to_csv(DATA / "items_base.csv", index=False)
    pd.DataFrame({"request_id": np.arange(1, 20001), "item_rank": ex["seq"][:20000] + 1}).to_csv(
        DATA / "requests_base_first20000.csv", index=False)

    # 確かめ 18通り
    g = []
    for rho in RHOS:
        for cap in CAPS:
            for sig in SIGS:
                rr, _ = one_setting(rng, rho, cap, sig)
                g += rr
        print("rho", rho, round(time.time() - t0, 1), flush=True)
    g = pd.DataFrame(g)
    g.to_csv(RES / "grid_policies.csv", index=False)
    summ = []
    for (rho, cap, sig), s in g.groupby(["rho", "cap_pct", "size_logsd"], sort=False):
        bc = s.loc[s.hit_count_pct.idxmax()].policy
        bb = s.loc[s.hit_bytes_pct.idxmax()].policy
        summ.append({"size_popularity": RHO_NAME[rho], "cap_pct": cap, "size_logsd": sig,
                     "rank_count": rank_str(s, "hit_count_pct"), "rank_bytes": rank_str(s, "hit_bytes_pct"),
                     "best_count": bc, "best_bytes": bb, "best_differs": bc != bb})
    sm = pd.DataFrame(summ)
    sm.to_csv(RES / "grid_summary.csv", index=False)
    out["grid"] = {"n": len(sm), "best_differs": int(sm.best_differs.sum()),
                   "best_differs_by_relation": {RHO_NAME[k]: int(sm[sm.size_popularity == RHO_NAME[k]].best_differs.sum())
                                                for k in RHOS},
                   "best_count_counts": sm.best_count.value_counts().to_dict(),
                   "best_bytes_counts": sm.best_bytes.value_counts().to_dict(),
                   "fully_reversed": int((sm.rank_count == sm.rank_bytes.str[::-1]).sum())}
    # 件数と量の差（①と③）
    piv = g.pivot_table(index=["rho", "cap_pct", "size_logsd"], columns="policy", values=["hit_count_pct", "hit_bytes_pct"])
    d_cnt = piv[("hit_count_pct", POL[2])] - piv[("hit_count_pct", POL[0])]
    d_byt = piv[("hit_bytes_pct", POL[2])] - piv[("hit_bytes_pct", POL[0])]
    out["grid"]["p3_minus_p1_count_pts_range"] = [r(d_cnt.min(), 2), r(d_cnt.max(), 2)]
    out["grid"]["p3_minus_p1_bytes_pts_range"] = [r(d_byt.min(), 2), r(d_byt.max(), 2)]
    out["grid"]["p3_count_higher_n"] = int((d_cnt > 0).sum())
    out["grid"]["p3_bytes_lower_n"] = int((d_byt < 0).sum())

    # 図1：基本の3つの置き方、件数と量
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(3)
    ax.bar(x - 0.18, b.hit_count_pct, 0.36, color=BLUE, label="件数の当たり率")
    ax.bar(x + 0.18, b.hit_bytes_pct, 0.36, color=ORANGE, label="量の当たり率")
    for i in range(3):
        ax.text(i - 0.18, b.hit_count_pct[i] + 1, f"{b.hit_count_pct[i]}%", ha="center", fontsize=9)
        ax.text(i + 0.18, b.hit_bytes_pct[i] + 1, f"{b.hit_bytes_pct[i]}%", ha="center", fontsize=9)
    ax.set_xticks(x, POL, fontsize=9.5)
    ax.set_ylim(0, max(b.hit_count_pct.max(), b.hit_bytes_pct.max()) * 1.2)
    ax.set_ylabel("当たり率（%）")
    ax.set_title("同じ置き場所（全データの量の3%）で、3つの置き方")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1151_base.png", SRC)

    # 図2：18通りの、③−①の差（件数・量）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    fig.set_size_inches(7.5, 7.5)
    labs = [f"{RHO_NAME[k[0]]}・置き場所{k[1]}%・散らばり{k[2]}" for k in d_cnt.index]
    yy = np.arange(len(labs))[::-1]
    ax.barh(yy + 0.2, d_cnt.values, 0.4, color=BLUE, label="件数の当たり率の差")
    ax.barh(yy - 0.2, d_byt.values, 0.4, color=ORANGE, label="量の当たり率の差")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(yy, labs, fontsize=8.5)
    ax.set_xlabel("③大きいものから捨てる − ①古いものから捨てる（ポイント）")
    ax.set_title("置き方を変えた18通りでの差")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1151_grid_diff.png", SRC)

    # 図3：大きさと人気の関係ごと、件数と量の当たり率（置き場所3%・散らばり1.6）
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.8), sharey=True)
    for ax, rho in zip(axes, RHOS):
        s = g[(g.rho == rho) & (g.cap_pct == 3) & (g.size_logsd == 1.6)].reset_index(drop=True)
        ax.bar(x - 0.18, s.hit_count_pct, 0.36, color=BLUE, label="件数")
        ax.bar(x + 0.18, s.hit_bytes_pct, 0.36, color=ORANGE, label="量")
        ax.set_xticks(x, ["①", "②", "③"])
        ax.set_title(RHO_NAME[rho], fontsize=11)
    axes[1].set_xlabel("①古いものから捨てる　②大きいものは置かない　③大きいものから捨てる", fontsize=9.5)
    axes[0].set_ylim(0, 100)
    axes[0].set_ylabel("当たり率（%）")
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("大きさと人気の関係で（置き場所3%・大きさの散らばり1.6）", fontsize=12, y=1.04)
    save(fig, "a1151_relation.png", SRC)

    (RES / "a1151_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ["base", "base_rank_count", "base_rank_bytes", "base_detail", "grid"]},
                     ensure_ascii=False, indent=1, default=float))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
