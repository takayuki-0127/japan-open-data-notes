"""1153 古く使われたものから捨てる決まりと、使われた回数の少ないものから捨てる決まりは、人気が移り変わるときにどちらが当たるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ5,000件への問い合わせの列。r番目に人気のデータが選ばれる確率は 1÷r^0.9 に比例すると置いた。
人気の移り変わりは「D 件の問い合わせごとに、新しいデータが1件、人気の上位50位までのどこか（でたらめ）に入り、
それより下の順位が1つずつ下がる」と置いた（いちばん下は消える）。置き場所（キャッシュ）は100件。
捨てる決まり：
  ①古い順：最後に使われてからいちばん長くたったものを捨てる
  ②回数（ずっと数える）：これまでに使われた回数がいちばん少ないものを捨てる。回数は置き場所から出ても覚えておく（同じ回数なら最後に使われたのが古いほう）
  ③回数（置き場所にいる間だけ）：置き場所に入ってからの回数がいちばん少ないものを捨てる。出たら回数は忘れる
  ④回数（2万件ごとに半分）：②の回数を、2万件の問い合わせごとに全部半分にする
  参考：その時点の人気の上位100件をずっと置けたとき（式：上位100件の確率の合計）
(1) 移り変わりの速さ D＝なし・2万・5,000・2,000・1,000・500・200件で、当たり率を数える（どの決まりも同じ問い合わせの列）
(2) 新しく人気になったデータへの問い合わせの当たり率と、置き場所のうち、いまの人気の上位1,000位に入っていないデータの数
(3) 確かめ：偏り（0.7・1.1）×新しいデータの入る位置（上位10位まで・上位500位まで）×置き場所（50・200件）×D（なし・5,000・1,000・200）
"""
import json
import time
import heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1153
SRC = "架空のアプリへの問い合わせ（作成者が置いた人気の偏りと移り変わりからの乱数、seed 1153）"
N_ITEMS, ALPHA, CAP, INS_TOP = 5_000, 0.9, 100, 50
WARM, MEAS = 50_000, 250_000
DS = [None, 20_000, 5_000, 2_000, 1_000, 500, 200]
HALF_EVERY = 20_000
TOP_K = 1_000
SNAP = 5_000
POL = ["recent", "freq_all", "freq_in", "freq_half"]
PNAME = {"recent": "①古い順（使われてから最も長いものを捨てる）", "freq_all": "②回数（ずっと数える）",
         "freq_in": "③回数（置き場所にいる間だけ）", "freq_half": "④回数（2万件ごとに半分）"}
G_ALPHA = [0.7, 1.1]
G_INS = [10, 500]
G_CAP = [50, 200]
G_D = [None, 5_000, 1_000, 200]
G_MEAS = 120_000


def r(x, d=4):
    return round(float(x), d)


def probs(n, a):
    p = 1.0 / np.arange(1, n + 1) ** a
    return p / p.sum()


def make_stream(rng, n_items, a, d, ins_top, n_req):
    """問い合わせの列（データの番号）・新しいデータかどうか・ある時点の人気の上位 TOP_K の集合"""
    p = probs(n_items, a)
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    ranks = np.searchsorted(cdf, rng.random(n_items * 0 + n_req), side="right").tolist()
    n_ins = 0 if d is None else n_req // d + 1
    ins_pos = rng.integers(0, ins_top, size=max(n_ins, 1)).tolist()
    order = list(range(n_items))
    nxt = n_items
    items = []
    snaps = {}
    k = 0
    for i in range(n_req):
        if d is not None and i > 0 and i % d == 0:
            order.insert(ins_pos[k], nxt)
            order.pop()
            nxt += 1
            k += 1
        if i % SNAP == 0:
            snaps[i] = (set(order[:CAP]), set(order[:TOP_K]))
        items.append(order[ranks[i]])
    return items, snaps


def simulate(items, cap, policy, warm, snaps=None, n_items=N_ITEMS):
    cache = {}            # 古い順：並び順をそのまま使う／回数：中身の印
    cnt = {}
    last = {}
    heap = []
    hits = 0
    new_req = new_hit = 0
    slots_mid, slots_far = [], []
    for i, x in enumerate(items):
        if policy == "freq_half" and i > 0 and i % HALF_EVERY == 0:
            for key in cnt:
                cnt[key] = cnt[key] // 2
            heap = [(cnt[y], last[y], y) for y in cache]
            heapq.heapify(heap)
        hit = x in cache
        if policy == "recent":
            if hit:
                del cache[x]
                cache[x] = None
            else:
                cache[x] = None
                if len(cache) > cap:
                    del cache[next(iter(cache))]
        else:
            if hit:
                cnt[x] += 1
            else:
                if len(cache) >= cap:
                    while True:
                        c, t, y = heapq.heappop(heap)
                        if y in cache and cnt.get(y) == c and last[y] == t:
                            break
                    del cache[y]
                    if policy == "freq_in":
                        del cnt[y]
                cache[x] = None
                cnt[x] = cnt.get(x, 0) + 1
            last[x] = i
            heapq.heappush(heap, (cnt[x], i, x))
            if len(heap) > 20 * cap:
                heap = [(cnt[y], last[y], y) for y in cache]
                heapq.heapify(heap)
        if i >= warm:
            hits += hit
            if x >= n_items:
                new_req += 1
                new_hit += hit
            if snaps is not None and i % SNAP == 0:
                top_c, top_k = snaps[i]
                slots_far.append(sum(1 for y in cache if y not in top_k))
                slots_mid.append(sum(1 for y in cache if (y not in top_c) and (y in top_k)))
    return {"hit_rate": hits / (len(items) - warm),
            "new_req_share": new_req / (len(items) - warm),
            "new_hit_rate": (new_hit / new_req) if new_req else None,
            "slots_mid": float(np.mean(slots_mid)) if slots_mid else None,
            "slots_far": float(np.mean(slots_far)) if slots_far else None}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    ideal = float(probs(N_ITEMS, ALPHA)[:CAP].sum())
    out = {"setup": {"n_items": N_ITEMS, "alpha": ALPHA, "cap": CAP, "ins_top": INS_TOP, "warm": WARM, "meas": MEAS,
                     "half_every": HALF_EVERY, "top_k": TOP_K, "seed": SEED,
                     "n_requests": WARM + MEAS, "grid_requests": WARM + G_MEAS, "grid_meas": G_MEAS},
           "ideal_top100_formula": r(ideal)}
    rows = []
    first_items = None
    for d in DS:
        items, snaps = make_stream(rng, N_ITEMS, ALPHA, d, INS_TOP, WARM + MEAS)
        if d == 1_000:
            first_items = items[:20_000]
        for pol in POL:
            s = simulate(items, CAP, pol, WARM, snaps)
            rows.append({"d": "なし" if d is None else d, "d_num": 0 if d is None else d, "policy": pol,
                         "hit_rate": r(s["hit_rate"]), "new_req_share": r(s["new_req_share"]),
                         "new_hit_rate": None if s["new_hit_rate"] is None else r(s["new_hit_rate"]),
                         "slots_rank101_1000": r(s["slots_mid"], 2), "slots_outside_top1000": r(s["slots_far"], 2),
                         "slots_in_top100": r(CAP - s["slots_mid"] - s["slots_far"], 2), "ideal_formula": r(ideal)})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "by_speed.csv", index=False)
    out["by_speed"] = rows
    wide = df.pivot_table(index="d_num", columns="policy", values="hit_rate")
    # どの速さで①が②を上回るか
    cross = [int(k) for k, v in wide.iterrows() if k > 0 and v["recent"] > v["freq_all"]]
    out["recent_beats_freq_all_at_d"] = cross
    rc = df[df.policy == "recent"].hit_rate
    out["recent_hit_range_main"] = [r(rc.min()), r(rc.max())]
    out["best_policy_by_d"] = {("なし" if k == 0 else str(int(k))): v.idxmax() for k, v in wide.iterrows()}

    # 確かめ
    grows = []
    for a in G_ALPHA:
        for ins in G_INS:
            for cap in G_CAP:
                for d in G_D:
                    items, _ = make_stream(rng, N_ITEMS, a, d, ins, WARM + G_MEAS)
                    res = {pol: simulate(items, cap, pol, WARM)["hit_rate"] for pol in POL}
                    grows.append({"alpha": a, "ins_top": ins, "cap": cap, "d": "なし" if d is None else d,
                                  "recent": r(res["recent"]), "freq_all": r(res["freq_all"]), "freq_in": r(res["freq_in"]), "freq_half": r(res["freq_half"]),
                                  "ideal_formula": r(probs(N_ITEMS, a)[:cap].sum()),
                                  "best": max(res, key=res.get)})
    g = pd.DataFrame(grows)
    g.to_csv(RES / "grid.csv", index=False)
    gn = g[g.d == "なし"]
    gs = g[g.d != "なし"]
    out["grid_summary"] = {
        "n_cases": int(len(g)),
        "no_shift_freq_all_beats_recent": f"{int((gn.freq_all > gn.recent).sum())}/{len(gn)}",
        "no_shift_freq_all_minus_recent_pt": [r((gn.freq_all - gn.recent).min() * 100, 2), r((gn.freq_all - gn.recent).max() * 100, 2)],
        "d200_recent_beats_freq_all": f"{int((g[g.d == 200].recent > g[g.d == 200].freq_all).sum())}/{int((g.d == 200).sum())}",
        "d200_recent_minus_freq_all_pt": [r((g[g.d == 200].recent - g[g.d == 200].freq_all).min() * 100, 2),
                                          r((g[g.d == 200].recent - g[g.d == 200].freq_all).max() * 100, 2)],
        "d5000_recent_beats_freq_all": f"{int((g[g.d == 5000].recent > g[g.d == 5000].freq_all).sum())}/{int((g.d == 5000).sum())}",
        "d1000_recent_beats_freq_all": f"{int((g[g.d == 1000].recent > g[g.d == 1000].freq_all).sum())}/{int((g.d == 1000).sum())}",
        "shift_recent_beats_freq_all": f"{int((gs.recent > gs.freq_all).sum())}/{len(gs)}",
        "shift_best_counts": gs.best.value_counts().to_dict(),
        "shift_freq_half_minus_recent_pt": [r((gs.freq_half - gs.recent).min() * 100, 2), r((gs.freq_half - gs.recent).max() * 100, 2)],
        "shift_freq_half_beats_freq_all": f"{int((gs.freq_half > gs.freq_all).sum())}/{len(gs)}",
        "no_shift_freq_all_minus_freq_half_pt": [r((gn.freq_all - gn.freq_half).min() * 100, 2), r((gn.freq_all - gn.freq_half).max() * 100, 2)],
        "recent_range_over_d": [r(g.recent.min(), 4), r(g.recent.max(), 4)],
        "no_shift_best_counts": gn.best.value_counts().to_dict(),
    }

    # data
    pd.DataFrame({"i": np.arange(len(first_items)), "item": first_items,
                  "is_new": (np.array(first_items) >= N_ITEMS).astype(int)}).to_csv(DATA / "requests_d1000_first20000.csv", index=False)

    # 図1：速さごとの当たり率
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    xs = np.arange(len(DS))
    cols = {"recent": BLUE, "freq_all": ORANGE, "freq_in": GRAY, "freq_half": GREEN}
    for pol in POL:
        s = df[df.policy == pol]
        ax.plot(xs, s.hit_rate * 100, marker="o", color=cols[pol], label=PNAME[pol])
    ax.axhline(ideal * 100, color=INK, lw=0.8, ls="--")
    ax.text(len(DS) - 1, ideal * 100 + 1.2, f"その時点の上位100件を置けたとき {ideal*100:.2f}%（式）", fontsize=8, ha="right")
    ax.set_xticks(xs)
    ax.set_xticklabels(["なし" if d is None else f"{d:,}" for d in DS])
    ax.set_xlabel("新しいデータが上位に1件入る間隔（問い合わせの件数、右ほど速く移り変わる）")
    ax.set_ylabel("当たり率（%）")
    ax.set_ylim(0, 60)
    ax.set_title("人気が速く移り変わるほど、回数で捨てる決まりの当たり率が落ちる")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    save(fig, "a1153_by_speed.png", SRC)

    # 図2：置き場所100件の中身（D=1,000）
    s = df[df.d_num == 1000]
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    yy = np.arange(len(POL))[::-1]
    v1, v2, v3 = s.slots_in_top100.values, s.slots_rank101_1000.values, s.slots_outside_top1000.values
    ax.barh(yy, v1, color=BLUE, label="いまの上位100位")
    ax.barh(yy, v2, left=v1, color=ORANGE, label="101〜1,000位")
    ax.barh(yy, v3, left=v1 + v2, color=GRAY, label="1,000位より下")
    for yi, a1, a2, a3 in zip(yy, v1, v2, v3):
        ax.text(1, yi, f"{a1:.2f}", va="center", fontsize=8, color="white")
        ax.text(a1 + 1, yi, f"{a2:.2f}", va="center", fontsize=8, color=INK)
        ax.text(99, yi, f"{a3:.2f}", va="center", ha="right", fontsize=8, color=INK)
    ax.set_yticks(yy)
    ax.set_yticklabels([PNAME[p] for p in POL], fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("置き場所100件の中身（件、測った時点の平均）")
    ax.set_title("1,000件ごとに移り変わるとき、置き場所に何が入っているか")
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.18))
    save(fig, "a1153_slots.png", SRC, y=-0.12)

    # 図3：新しく人気になったデータへの問い合わせの当たり率
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    sub = df[df.d_num > 0]
    xs2 = np.arange(len(DS) - 1)
    w = 0.2
    for j, pol in enumerate(POL):
        v = sub[sub.policy == pol].new_hit_rate.values * 100
        ax.bar(xs2 + (j - 1.5) * w, v, width=w, color=cols[pol], label=PNAME[pol])
    ax.set_xticks(xs2)
    ax.set_xticklabels([f"{d:,}" for d in DS[1:]])
    ax.set_ylim(0, 100)
    ax.set_xlabel("新しいデータが上位に1件入る間隔（問い合わせの件数）")
    ax.set_ylabel("新しいデータへの問い合わせの当たり率（%）")
    ax.set_title("新しく人気になったデータに当たるか")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    save(fig, "a1153_new_items.png", SRC, y=-0.14)

    (RES / "a1153_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
