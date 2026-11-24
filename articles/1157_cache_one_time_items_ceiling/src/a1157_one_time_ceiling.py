"""1157 一度しか使われないものが多いと、置き場所を大きくしても当たり率はどこで止まるのか？（架空のデータ）

作成者が置いた架空のアプリへの問い合わせの列（20万件）。問い合わせのうち割合 u は、その場かぎりの新しいデータ（二度と来ない）。
残りは2万種類のくり返し使われるデータから引く。よく使われるものへの偏りは、順位 k の使われやすさが k の −0.8 乗に比例すると置いた。
置き場所（キャッシュ）は、いっぱいになったら「いちばん長く使われていないもの」を捨てる。
(1) u を 0・20・40・60% に変え、置ける数 100〜3万と無制限で当たり率を数える。無制限の当たり率は
    1 −（初めて来た種類の数）÷（問い合わせの数）で、数え方からの恒等式どおり（乱数の値と照らす）
(2) 「2回目に来たものから置く」決まり（一度見た種類の記録は無制限に持つと置いた）でも数える。無制限では2回目も外れになる
(3) 記録の中で「1回しか使われなかったもの」の割合を、種類の数と問い合わせの数の2つで数える
(4) 確かめ：u × 偏り × 数える長さ（5万・20万・80万件）の27通りで、止まる位置と、置ける数2,000での当たり率を数える
"""
import json
import time
from collections import OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1157
SRC = "架空のアプリの問い合わせ（作成者が置いた使われやすさとその場かぎりの割合からの乱数、seed 1157）"
M = 20_000
S = 0.8
N = 200_000
US = [0.0, 0.2, 0.4, 0.6]
U_BASE = 0.4
SIZES = [100, 300, 1000, 3000, 10000, 30000]
G_U = [0.2, 0.4, 0.6]
G_S = [0.6, 0.8, 1.0]
G_N = [50_000, 200_000, 800_000]
G_SIZE = 2000


def r(x, d=4):
    return round(float(x), d)


def make_stream(rng, u, s, n):
    k = np.arange(1, M + 1)
    p = k ** (-s)
    p /= p.sum()
    cat = rng.choice(M, n, p=p)
    one = rng.random(n) < u
    keys = cat.copy()
    keys[one] = M + np.arange(one.sum())       # その場かぎりの新しい番号
    return keys, one


def oldest_out(keys, size, admit_second=False):
    c = OrderedDict()
    seen = set()
    hits = 0
    for x in keys.tolist():
        if x in c:
            c.move_to_end(x)
            hits += 1
            continue
        if admit_second:
            if x not in seen:
                seen.add(x)
                continue
        c[x] = None
        if len(c) > size:
            c.popitem(last=False)
    return hits / len(keys)


def ceiling(keys):
    return 1 - len(np.unique(keys)) / len(keys)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setting": {"catalog_items": M, "popularity_power": S, "requests": N, "one_time_shares": US,
                       "base_one_time_share": U_BASE, "sizes": SIZES}}

    rows, once_rows = [], []
    for u in US:
        keys, one = make_stream(rng, u, S, N)
        ceil = ceiling(keys)
        uniq, cnt = np.unique(keys, return_counts=True)
        cat_distinct = int((uniq < M).sum())
        once_items = int((cnt == 1).sum())
        once_rows.append({"one_time_share_pct": r(u * 100, 1), "distinct_items": int(len(uniq)),
                          "distinct_catalog": cat_distinct, "one_time_requests": int(one.sum()),
                          "used_once_items": once_items,
                          "used_once_share_of_items_pct": r(once_items / len(uniq) * 100, 2),
                          "used_once_share_of_requests_pct": r(once_items / N * 100, 2),
                          "used_once_from_catalog": int(((cnt == 1) & (uniq < M)).sum()),
                          "one_time_share_actual_pct": r(one.sum() / N * 100, 3),
                          "first_catalog_share_pct": r(cat_distinct / N * 100, 3),
                          "ceiling_pct": r(ceil * 100, 3),
                          "ceiling_formula_pct": r((1 - one.sum() / N - cat_distinct / N) * 100, 3),
                          "catalog_seen_2plus": int(((cnt >= 2) & (uniq < M)).sum()),
                          "ceiling_admit_second_pct": r(oldest_out(keys, 10 ** 9, True) * 100, 3),
                          "ceiling_admit_second_formula_pct": r((1 - (one.sum() + cat_distinct + ((cnt >= 2) & (uniq < M)).sum()) / N) * 100, 3)})
        for sz in SIZES:
            for pol, adm in (("oldest_out", False), ("admit_second", True)):
                h = oldest_out(keys, sz, adm)
                rows.append({"one_time_share_pct": r(u * 100, 1), "size": sz, "rule": pol,
                             "hit_rate_pct": r(h * 100, 3), "ceiling_pct": r(ceil * 100, 3),
                             "share_of_ceiling_pct": r(h / ceil * 100, 2) if ceil > 0 else None})
        if u == U_BASE:
            pd.DataFrame({"request_id": np.arange(1, 20001), "item_key": keys[:20000],
                          "one_time": one[:20000].astype(int)}).to_csv(DATA / "requests_u40.csv", index=False)
    tb = pd.DataFrame(rows)
    tb.to_csv(RES / "by_size.csv", index=False)
    oc = pd.DataFrame(once_rows)
    oc.to_csv(RES / "used_once.csv", index=False)
    out["used_once"] = oc.to_dict("records")
    out["by_size"] = tb.to_dict("records")

    # 置き場所を10倍にしたときの伸び・止まる位置との差（基本 u=40%）
    b = tb[(tb.one_time_share_pct == U_BASE * 100)]
    bo = b[b.rule == "oldest_out"].set_index("size").hit_rate_pct
    ba = b[b.rule == "admit_second"].set_index("size").hit_rate_pct
    ob = oc[oc.one_time_share_pct == U_BASE * 100].iloc[0]
    out["base"] = {"ceiling_pct": float(b.ceiling_pct.iloc[0]),
                   "ceiling_admit_second_pct": float(ob.ceiling_admit_second_pct),
                   "oldest_out": {str(k): float(v) for k, v in bo.items()},
                   "admit_second": {str(k): float(v) for k, v in ba.items()},
                   "gain_3000_to_30000_pt": r(bo[30000] - bo[3000], 3),
                   "gap_30000_to_ceiling_pt": r(float(b.ceiling_pct.iloc[0]) - bo[30000], 3)}
    # u=0 と比べて、同じ置き場所で当たり率がどれだけ下がるか（(1−u)倍で済むか）
    z = tb[(tb.rule == "oldest_out")].pivot(index="size", columns="one_time_share_pct", values="hit_rate_pct")
    comp = []
    for sz in SIZES:
        for u in US[1:]:
            comp.append({"size": sz, "one_time_share_pct": r(u * 100, 1), "hit_pct": float(z.loc[sz, u * 100]),
                         "no_one_time_times_1_minus_u_pct": r(z.loc[sz, 0.0] * (1 - u), 3),
                         "extra_drop_pt": r(z.loc[sz, 0.0] * (1 - u) - z.loc[sz, u * 100], 3)})
    comp = pd.DataFrame(comp)
    comp.to_csv(RES / "crowding.csv", index=False)
    out["crowding"] = comp.to_dict("records")
    out["crowding_extra_drop_range_pt"] = [float(comp.extra_drop_pt.min()), float(comp.extra_drop_pt.max())]

    # (4) 確かめ
    gr = []
    for u in G_U:
        for s in G_S:
            for n in G_N:
                keys, one = make_stream(rng, u, s, n)
                ceil = ceiling(keys)
                h1 = oldest_out(keys, G_SIZE, False)
                h2 = oldest_out(keys, G_SIZE, True)
                gr.append({"one_time_share_pct": r(u * 100, 1), "popularity_power": s, "requests": n,
                           "one_time_share_actual_pct": r(one.sum() / N * 100, 3),
                          "first_catalog_share_pct": r(cat_distinct / N * 100, 3),
                          "ceiling_pct": r(ceil * 100, 3), "ceiling_upper_1_minus_u_pct": r((1 - u) * 100, 1),
                           "gap_to_1_minus_u_pt": r((1 - u - ceil) * 100, 3),
                           "hit_oldest_out_2000_pct": r(h1 * 100, 3), "hit_admit_second_2000_pct": r(h2 * 100, 3)})
    gr = pd.DataFrame(gr)
    gr.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"n": len(gr),
                   "ceiling_range_by_u": {str(k): [float(v.min()), float(v.max())]
                                          for k, v in gr.groupby("one_time_share_pct").ceiling_pct},
                   "gap_to_1_minus_u_by_n": {str(k): [float(v.min()), float(v.max())]
                                             for k, v in gr.groupby("requests").gap_to_1_minus_u_pt},
                   "admit_second_better": int((gr.hit_admit_second_2000_pct > gr.hit_oldest_out_2000_pct).sum()),
                   "admit_minus_oldest_range_pt": [r((gr.hit_admit_second_2000_pct - gr.hit_oldest_out_2000_pct).min(), 3),
                                                   r((gr.hit_admit_second_2000_pct - gr.hit_oldest_out_2000_pct).max(), 3)]}

    # 図1：置ける数と当たり率（古いものから捨てる）
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    cols = {0.0: INK, 0.2: BLUE, 0.4: ORANGE, 0.6: GREEN}
    for u in US:
        s_ = tb[(tb.one_time_share_pct == u * 100) & (tb.rule == "oldest_out")]
        ax.plot(s_["size"], s_.hit_rate_pct, marker="o", ms=4, color=cols[u], label=f"その場かぎり {u * 100:g}%")
        cv = s_.ceiling_pct.iloc[0]
        ax.hlines(cv, 20000, 200000, color=cols[u], lw=0.9, ls="--")
        ax.text(36000, cv + 0.8, f"無制限 {cv:.3f}%", fontsize=8.5, color=cols[u], va="bottom")
    ax.set_xscale("log")
    ax.set_xticks(SIZES, [f"{x:,}" for x in SIZES])
    ax.set_xlim(80, 200000)
    ax.set_ylim(0, 100)
    ax.set_xlabel("置ける数（種類、くり返し使われるデータは2万種類）")
    ax.set_ylabel("当たり率（%）")
    ax.set_title("置き場所を大きくしても、点線（無制限）より上には行かない（20万件）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1157_ceiling.png", SRC)

    # 図2：1回しか使われなかったものの割合
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(US))
    w = 0.38
    a1 = oc.used_once_share_of_items_pct.values
    a2 = oc.used_once_share_of_requests_pct.values
    ax.bar(x - w / 2, a1, w, color=ORANGE, label="種類の数で数えた割合")
    ax.bar(x + w / 2, a2, w, color=BLUE, label="問い合わせの数で数えた割合")
    for i in range(len(US)):
        ax.text(x[i] - w / 2, a1[i] + 1.2, f"{a1[i]:.2f}%", ha="center", fontsize=8.5)
        ax.text(x[i] + w / 2, a2[i] + 1.2, f"{a2[i]:.2f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x, [f"その場かぎり\n{u * 100:g}%" for u in US])
    ax.set_ylim(0, 105)
    ax.set_ylabel("記録の中で1回しか使われなかったもの（%）")
    ax.set_title("同じ記録でも、種類で数えるか件数で数えるかで大きく違う")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1157_used_once.png", SRC)

    # 図3：2回目から置く決まり（u=40%）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(SIZES, bo.values, marker="o", ms=4, color=ORANGE, label="来たらすぐ置く")
    ax.plot(SIZES, ba.values, marker="s", ms=4, color=BLUE, label="2回目に来たものから置く")
    ax.axhline(out["base"]["ceiling_pct"], color=GRAY, lw=0.8, ls="--")
    ax.text(110, out["base"]["ceiling_pct"] + 1.2, f"来たらすぐ置く・無制限 {out['base']['ceiling_pct']:.3f}%",
            fontsize=8.5, color=GRAY)
    ca = out["base"]["ceiling_admit_second_pct"]
    ax.axhline(ca, color=BLUE, lw=0.8, ls=":")
    ax.text(110, ca - 1.2, f"2回目から置く・無制限 {ca:.3f}%", fontsize=8.5, color=BLUE, va="top")
    ax.set_xscale("log")
    ax.set_xticks(SIZES, [f"{x:,}" for x in SIZES])
    ax.set_ylim(0, 70)
    ax.set_xlabel("置ける数（種類）")
    ax.set_ylabel("当たり率（%）")
    ax.set_title("その場かぎり40%：2回目から置くと、小さい置き場所では高く、止まる位置は低い")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    save(fig, "a1157_admit.png", SRC)

    (RES / "a1157_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("by_size", "crowding")}, ensure_ascii=False, indent=1))
    print(comp.to_string())
    print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
