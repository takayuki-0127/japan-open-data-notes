"""950 店の商圏を半径で決めると、重なりはどれだけ数え落とすのか？（架空のデータ）

架空の町（10km四方）に世帯4万を置き、架空のチェーンの店12軒を置く。
店ごとの商圏を「半径1kmの円の中の世帯」と決めて数えた値と、
作成者が置いた店の選び方（いちばん近い店へ。ただし2kmより遠ければどこにも行かない）での
本当の客の世帯数を比べる。距離はまっすぐの距離。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 950
SRC = "架空の町の世帯と店（作成者が乱数で作成、seed 950）"
SIZE = 10.0
N_HH = 40000
N_STORE = 12
R = 1.0
REACH = 2.0
REPS = 100


def make_town(rng):
    n_cl = int(N_HH * 0.6)
    centers = rng.uniform(2, 8, (4, 2))
    which = rng.integers(0, 4, n_cl)
    pts = centers[which] + rng.normal(0, 1.2, (n_cl, 2))
    pts = np.vstack([pts, rng.uniform(0, SIZE, (N_HH - n_cl, 2))])
    pts = pts[(pts >= 0).all(1) & (pts <= SIZE).all(1)]
    return pts


def place_stores(rng, hh, s):
    return hh[rng.choice(len(hh), s, replace=False)]


def customers(dist, rule):
    """世帯×店の距離から、店ごとの客の世帯数（分けるときは小数）"""
    s = dist.shape[1]
    if rule == "nearest":
        near = dist.argmin(1)
        ok = dist.min(1) <= REACH
        return np.bincount(near[ok], minlength=s).astype(float), ok
    w = np.where(dist <= REACH, np.exp(-dist / 0.5), 0.0)
    tot = w.sum(1)
    ok = tot > 0
    share = np.zeros_like(w)
    share[ok] = w[ok] / tot[ok, None]
    return share.sum(0), ok


def analyse(hh, st, r=R, rule="nearest"):
    dist = np.hypot(hh[:, None, 0] - st[None, :, 0], hh[:, None, 1] - st[None, :, 1])
    inside = dist <= r
    circ = inside.sum(0).astype(float)
    n_in = inside.sum(1)
    union = float((n_in > 0).sum())
    cust, served = customers(dist, rule)
    # 円の中の世帯のうち、ほかの店の円にも入っている割合（店ごと）
    shared = (inside & (n_in > 1)[:, None]).sum(0) / np.maximum(circ, 1)
    # 本当の客のうち、使う店の円の外に住む割合（いちばん近い店のとき）
    if rule == "nearest":
        near = dist.argmin(1)
        d_use = dist[np.arange(len(hh)), near]
        out_circle = float((d_use[served] > r).mean())
    else:
        w = np.where(dist <= REACH, np.exp(-dist / 0.5), 0.0)
        sh = w / np.maximum(w.sum(1, keepdims=True), 1e-300)
        out_circle = float((sh * (dist > r)).sum() / sh.sum())
    ratio = circ / np.maximum(cust, 1e-9)
    return {"circle_sum": circ.sum(), "union": union, "double_count_share": (circ.sum() - union) / circ.sum(),
            "overcount_ratio": circ.sum() / union, "served": float(served.sum()),
            "circle_sum_over_served": circ.sum() / served.sum(),
            "store_ratio_median": float(np.median(ratio)), "store_ratio_min": float(ratio.min()),
            "store_ratio_max": float(ratio.max()), "store_shared_median": float(np.median(shared)),
            "customers_outside_own_circle": out_circle,
            "households_outside_all_circles_served": float(((n_in == 0) & served).sum() / served.sum())}, \
        (dist, inside, circ, cust, served)


def new_store(hh, st, rng, r=R, rule="nearest"):
    """13軒目を置いたとき：新しい店の円の世帯・本当の客・そのうち前は行く店のなかった世帯"""
    new = hh[rng.integers(len(hh))][None, :]
    st2 = np.vstack([st, new])
    d_old = np.hypot(hh[:, None, 0] - st[None, :, 0], hh[:, None, 1] - st[None, :, 1])
    d_new = np.hypot(hh[:, 0] - new[0, 0], hh[:, 1] - new[0, 1])
    circ_new = float((d_new <= r).sum())
    circ_new_overlap = float(((d_new <= r) & (d_old <= r).any(1)).sum())
    cust2, served2 = customers(np.column_stack([d_old, d_new]), rule)
    _, served1 = customers(d_old, rule)
    gain = float(served2.sum() - served1.sum())
    c_new = float(cust2[-1])
    return {"new_circle": circ_new, "new_circle_overlap_share": circ_new_overlap / max(circ_new, 1),
            "new_customers": c_new, "net_new_served": gain,
            "net_new_over_circle": gain / max(circ_new, 1),
            "from_other_stores_share": (c_new - gain) / max(c_new, 1e-9)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    hh = make_town(rng)
    st = place_stores(rng, hh, N_STORE)
    one, (dist, inside, circ, cust, served) = analyse(hh, st)
    pd.DataFrame({"store": np.arange(1, N_STORE + 1), "x_km": st[:, 0], "y_km": st[:, 1],
                  "households_in_1km": circ.astype(int), "customers_nearest_rule": cust.astype(int)}) \
        .to_csv(DATA / "stores_example.csv", index=False, float_format="%.3f")
    one_town = {k: round(float(v), 4) for k, v in one.items()}
    one_town["households"] = int(len(hh))
    store_tab = pd.DataFrame({"store": np.arange(1, N_STORE + 1), "circle": circ.astype(int),
                              "customers": cust.astype(int), "ratio": np.round(circ / cust, 3)})

    rows, nrows = [], []
    for k in range(REPS):
        rr = np.random.default_rng(SEED * 1000 + k)
        h = make_town(rr)
        s_ = place_stores(rr, h, N_STORE)
        for rule in ["nearest", "split"]:
            o, _ = analyse(h, s_, R, rule)
            o.update({"rep": k, "rule": rule})
            rows.append(o)
            nn = new_store(h, s_, np.random.default_rng(SEED * 2000 + k), R, rule)
            nn.update({"rep": k, "rule": rule})
            nrows.append(nn)
    sim = pd.DataFrame(rows)
    summ = sim.drop(columns="rep").groupby("rule").mean().round(4)
    summ.to_csv(RES / "main_100towns.csv")
    nsim = pd.DataFrame(nrows)
    nsumm = nsim.drop(columns="rep").groupby("rule").agg(["mean", "median"]).round(4)
    nsumm.columns = [f"{a}_{b}" for a, b in nsumm.columns]
    nsumm.to_csv(RES / "new_store_100towns.csv")

    # 確かめ：店の数 × 半径 × 店の選び方（18通り、各20回）
    sens = []
    for ns in [6, 12, 24]:
        for r in [0.5, 1.0, 1.5]:
            for rule in ["nearest", "split"]:
                acc, acc2 = [], []
                for k in range(20):
                    rr = np.random.default_rng(SEED * 7000 + ns * 100 + int(r * 10) * 10000 + k)
                    h = make_town(rr)
                    s_ = place_stores(rr, h, ns)
                    acc.append(analyse(h, s_, r, rule)[0])
                    acc2.append(new_store(h, s_, rr, r, rule))
                a = pd.DataFrame(acc).mean()
                b = pd.DataFrame(acc2).mean()
                sens.append({"stores": ns, "radius_km": r, "rule": rule,
                             "double_count_share": round(a.double_count_share, 4),
                             "overcount_ratio": round(a.overcount_ratio, 4),
                             "circle_sum_over_served": round(a.circle_sum_over_served, 4),
                             "store_ratio_median": round(a.store_ratio_median, 4),
                             "customers_outside_own_circle": round(a.customers_outside_own_circle, 4),
                             "net_new_over_circle": round(b.net_new_over_circle, 4),
                             "from_other_stores_share": round(b.from_other_stores_share, 4)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_grid.csv", index=False)

    def rg(col, sub=sens):
        return [round(float(sub[col].min()), 4), round(float(sub[col].max()), 4)]

    out = {"setup": {"town_km": SIZE, "households_target": N_HH, "stores": N_STORE, "radius_km": R, "reach_km": REACH,
                     "reps": REPS, "split_rule": "2km以内の店に exp(-距離/0.5km) の重みで分かれる"},
           "one_town": one_town, "one_town_stores": store_tab.to_dict("records"),
           "mean_over_100": summ.reset_index().to_dict("records"),
           "new_store_over_100": nsumm.reset_index().to_dict("records"),
           "sensitivity_ranges": {c: rg(c) for c in ["double_count_share", "overcount_ratio", "circle_sum_over_served",
                                                     "store_ratio_median", "customers_outside_own_circle",
                                                     "net_new_over_circle", "from_other_stores_share"]}}
    json.dump(out, open(RES / "a950_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の町と、店の半径1kmの円
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    sub = hh[np.random.default_rng(SEED + 1).choice(len(hh), 6000, replace=False)]
    ax.scatter(sub[:, 0], sub[:, 1], s=1.2, color=GRAY, alpha=.5, lw=0)
    for x, y in st:
        ax.add_patch(Circle((x, y), R, fill=True, fc=BLUE, alpha=.12, ec=BLUE, lw=1))
    ax.scatter(st[:, 0], st[:, 1], s=28, color=ORANGE, zorder=3, marker="s")
    ax.set_xlim(0, SIZE); ax.set_ylim(0, SIZE); ax.set_aspect("equal")
    ax.set_xlabel("km"); ax.set_ylabel("km")
    ax.set_title(f"店{N_STORE}軒の半径1kmの円の合計は{one_town['circle_sum']:,.0f}世帯、\n"
                 f"重ならずに数えると{one_town['union']:,.0f}世帯（1回分の町。灰色の点は世帯の一部）", fontsize=11.5)
    save(fig, "a950_town.png", SRC)

    # 図2：店ごとの、円の中の世帯と本当の客（1回分の町）
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(cust, circ, s=36, color=BLUE)
    m = max(circ.max(), cust.max()) * 1.08
    ax.plot([0, m], [0, m], color=GRAY, ls="--", lw=1)
    ax.text(m * .97, m * .9, "円の中＝本当の客", color=GRAY, fontsize=9, ha="right")
    for j in range(N_STORE):
        dx, dy, ha = (m * .012, m * .012, "left") if j % 2 == 0 else (-m * .012, -m * .035, "right")
        ax.text(cust[j] + dx, circ[j] + dy, f"{j + 1}", fontsize=8, color=INK, ha=ha)
    ax.set_xlim(0, m); ax.set_ylim(0, m)
    ax.set_xlabel("本当の客の世帯数（いちばん近い店へ、2km以内）"); ax.set_ylabel("半径1kmの円の中の世帯数")
    ax.set_title(f"円の中の世帯÷本当の客は、店ごとに{store_tab.ratio.min():.2f}〜{store_tab.ratio.max():.2f}倍（1回分の町、数字は店の番号）",
                 fontsize=11.5)
    save(fig, "a950_store_ratio.png", SRC)

    # 図3：確かめ。店の数と半径で、二重に数えた割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    sn = sens[sens.rule == "nearest"]
    for r, c in [(0.5, LIGHT), (1.0, BLUE), (1.5, INK)]:
        t = sn[sn.radius_km == r]
        ax.plot(t.stores, t.double_count_share * 100, marker="o", color=c, label=f"半径{r}km")
        for x, v in zip(t.stores, t.double_count_share * 100):
            ax.text(x, v + 2, f"{v:.0f}%", ha="center", fontsize=8.5, color=c)
    ax.set_xticks([6, 12, 24]); ax.set_xticklabels(["6軒", "12軒", "24軒"]); ax.set_ylim(0, 100)
    ax.set_xlabel("店の数"); ax.set_ylabel("円の合計のうち、二重に数えた世帯（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("店が多く半径が大きいほど、円を足した数は重なりを多く含む（各20回の平均）")
    save(fig, "a950_overlap_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
