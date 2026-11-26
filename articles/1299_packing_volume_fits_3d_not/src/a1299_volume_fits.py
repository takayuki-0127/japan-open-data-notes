"""1299 荷物の体積の合計は箱の容量に収まっていても、縦・横・高さで並べると入らない組み合わせはどれだけあるのか？（架空のデータ）

作成者が置いた架空の通販の発送。1つの注文の荷物（商品の箱）は2〜4個（同じ確率）。
荷物の縦・横・高さは、それぞれ中央値12cm・対数のばらつき0.45の右に長い乱数を1cm単位に丸め、2〜45cmに収めたもの。
発送の箱の内のりは 40×30×25cm（容量30,000cm3）。荷物の体積の合計が容量以下の注文だけを取り出し、
縦・横・高さで並べて入るかを判定した（判定のしかたは pack3d.py）。
確かめとして、荷物の大きさ（中央値9・12・15cm）×箱の形（40×30×25・31×31×31・50×40×15）
×向き（6通りの向きを使ってよい・上下はそのまま横に回すだけ）の18通り。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
import pack3d
from multiprocessing import Pool

SEED = 1299
SRC = "架空の通販の発送（作成者が置いた荷物の大きさの分布と箱の寸法からの乱数、seed 1299）"
PER_BIN = 300
NMAX = 4                # 1つの注文の荷物は2〜NMAX個
BOXES = {"40×30×25": (40, 30, 25), "31×31×31": (31, 31, 31), "50×40×15": (50, 40, 15)}
MEDIANS = [9, 12, 15]
ROTS = {"all": "6通りの向き", "flat": "上下そのまま"}
BINS = [0, 0.5, 0.7, 0.85, 1.0]
BIN_LABELS = ["50%以下", "50〜70%", "70〜85%", "85〜100%"]
CAT_NO = ["single", "pair", "nf_search", "unknown"]
LIMIT = 3000000
MAX_BATCH = 40          # 4,000件ずつ、最大40回（16万件）引いて区分を埋める
MIN_BIN = 50            # 区分の件数がこれより少なければ割合を出さない
MIN_OK1 = 30            # どの荷物も1つなら入る注文がこれより少なければ、組み合わせの割合を出さない


def make_orders(rng, per_bin, median, box):
    """体積の合計が容量以下の注文を、詰まり具合（体積の合計÷容量）の4つの区分から per_bin 件ずつ取る。
    あわせて、区分に分ける前の自然な割合（体積で入る注文のうち各区分が占める割合）も返す"""
    V = box[0] * box[1] * box[2]
    got = {b: [] for b in range(4)}
    natural = np.zeros(4)
    for _ in range(MAX_BATCH):
        if min(len(v) for v in got.values()) >= per_bin:
            break
        k = rng.integers(2, NMAX + 1, 4000)
        it = np.clip(np.round(rng.lognormal(np.log(median), 0.45, (4000, NMAX, 3))), 2, 45).astype(int)
        v = it.prod(2)
        v = np.where(np.arange(NMAX)[None, :] < k[:, None], v, 0).sum(1)
        fill = v / V
        for r in range(4000):
            if fill[r] > 1:
                continue
            b = int(np.searchsorted(BINS, fill[r], side="left") - 1)
            b = max(b, 0)
            natural[b] += 1
            if len(got[b]) < per_bin:
                got[b].append(([tuple(int(a) for a in x) for x in it[r, :k[r]]], float(fill[r])))
    orders = [o for b in range(4) for o in got[b]]
    return orders, natural / natural.sum()


def judge(items, box, rot):
    # pack3d.judge と同じ順で、置き場所を探す回数の上限だけ LIMIT にする
    if not all(pack3d.fits_one(i, box, rot) for i in items):
        return "single"
    n = len(items)
    for a in range(n):
        for b in range(a + 1, n):
            if not pack3d.pair_ok(items[a], items[b], box, rot):
                return "pair"
    kb = pack3d.key_box(box, rot)
    ki = tuple(sorted(pack3d.key_item(i, rot) for i in items))
    if pack3d.CUT[rot](kb, ki):
        return "fit"
    r = pack3d.corner_search(items, box, rot, limit=LIMIT)
    if r is True:
        return "fit_corner"
    return "nf_search" if r is False else "unknown"


def run(median, boxname, rot, seed):
    box = BOXES[boxname]
    rng = np.random.default_rng(seed)
    orders, nat = make_orders(rng, PER_BIN, median, box)
    rows = []
    for i, (items, fill) in enumerate(orders):
        rows.append({"order": i + 1, "n_items": len(items), "fill": fill,
                     "items": ";".join("x".join(map(str, t)) for t in items),
                     "result": judge(items, box, rot)})
    df = pd.DataFrame(rows)
    df["fill_bin"] = pd.cut(df.fill, BINS, labels=BIN_LABELS)
    return df, nat


def summarize(df):
    n = len(df)
    if n == 0:
        return {"orders": 0}
    c = df.result.value_counts()
    g = lambda k: int(c.get(k, 0))
    proven = g("single") + g("pair")
    notfound = g("nf_search") + g("unknown")
    n_ok1 = n - g("single")          # どの荷物も1つなら入る注文
    return {"orders": n, "fit_cut_pct": round(100 * g("fit") / n, 2),
            "fit_corner_pct": round(100 * g("fit_corner") / n, 2),
            "single_pct": round(100 * g("single") / n, 2), "pair_pct": round(100 * g("pair") / n, 2),
            "notfound_pct": round(100 * notfound / n, 2),
            "nf_search_pct": round(100 * g("nf_search") / n, 2), "unknown_pct": round(100 * g("unknown") / n, 2),
            "no_fit_low_pct": round(100 * proven / n, 2), "no_fit_high_pct": round(100 * (proven + notfound) / n, 2),
            "orders_each_fits": n_ok1,
            "combo_low_pct": round(100 * g("pair") / n_ok1, 2) if n_ok1 >= MIN_OK1 else np.nan,
            "combo_high_pct": round(100 * (g("pair") + notfound) / n_ok1, 2) if n_ok1 >= MIN_OK1 else np.nan,
            "mean_fill_pct": round(100 * df.fill.mean(), 2)}


def weighted(bf, nat):
    """区分ごとの割合を、区分に分ける前の自然な割合で重みづけした、体積で入る注文全体の割合（件数のない区分は自然な割合も0）"""
    w = np.asarray(nat)
    o = {}
    for col in ["single_pct", "no_fit_low_pct", "no_fit_high_pct"]:
        o[col] = round(float(np.nansum(bf[col].values * w)), 2)
    ok1 = (100 - bf.single_pct.values) / 100 * w
    for col in ["combo_low_pct", "combo_high_pct"]:
        v = bf[col].values.astype(float)
        m = ~np.isnan(v) & ~np.isnan(ok1)
        o[col] = round(float((v[m] * ok1[m]).sum() / ok1[m].sum()), 2)
    return o


def setting(args):
    med, bname, rot, seed = args
    df, nat = run(med, bname, rot, seed)
    rows = []
    for lab in BIN_LABELS:
        d = df[df.fill_bin == lab]
        s = summarize(d) if len(d) >= MIN_BIN else {"orders": len(d)}
        rows.append(dict(s, fill_bin=lab))
    bf = pd.DataFrame(rows)
    return df, nat, bf


def main():
    t0 = time.time()
    tasks = [(12, "40×30×25", "all", SEED)]
    for mi, med in enumerate(MEDIANS):
        for bi, bname in enumerate(BOXES):
            for ri, rot in enumerate(ROTS):
                if (med, bname, rot) != (12, "40×30×25", "all"):
                    tasks.append((med, bname, rot, SEED * 100 + mi * 10 + bi * 3 + ri))
    with Pool(2) as pool:
        res = pool.map(setting, tasks, chunksize=1)
    base, nat, bf = res[0]
    base.drop(columns="fill_bin").to_csv(DATA / "orders_base.csv", index=False, float_format="%.4f")
    bf["natural_share_pct"] = np.round(100 * nat, 2)
    bf.to_csv(RES / "base_by_fill.csv", index=False)
    bn = pd.DataFrame([dict(summarize(d), n_items=int(k)) for k, d in base.groupby("n_items", sort=True)])
    bn.to_csv(RES / "base_by_items_stratified.csv", index=False)
    sb = summarize(base)
    wb = weighted(bf, nat)

    ex = base[(base.result == "pair") & (base.fill <= 0.7)].head(1)
    example = [dict(r, fill=round(100 * r["fill"], 2)) for r in ex[["order", "n_items", "items", "fill"]].to_dict("records")]
    ex2 = base[(base.result == "fit_corner")].head(1)
    example_corner = [dict(r, fill=round(100 * r["fill"], 2)) for r in ex2[["order", "n_items", "items", "fill"]].to_dict("records")]

    grid = []
    for (med, bname, rot, _), (d, nt, b) in zip(tasks, res):
        w = weighted(b, nt)
        row = {"item_median_cm": med, "box": bname, "rotation": ROTS[rot]}
        for k, lab in zip(range(4), ["le50", "50_70", "70_85", "85_100"]):
            row[f"natural_{lab}_pct"] = round(100 * float(nt[k]), 2)
        row.update({"all_single_pct": w["single_pct"], "all_no_fit_low_pct": w["no_fit_low_pct"],
                    "all_no_fit_high_pct": w["no_fit_high_pct"], "all_combo_low_pct": w["combo_low_pct"],
                    "all_combo_high_pct": w["combo_high_pct"]})
        for lab, bl in [("70_85", "70〜85%"), ("85_100", "85〜100%")]:
            r = b[b.fill_bin == bl].iloc[0]
            row[f"fill{lab}_orders"] = int(r.orders)
            for c in ["single_pct", "combo_low_pct", "combo_high_pct"]:
                row[f"fill{lab}_{c}"] = r.get(c, np.nan)
        row["notfound_pct_max_bin"] = float(np.nanmax(b.notfound_pct.values.astype(float)))
        row["fit_corner_pct_max_bin"] = float(np.nanmax(b.fit_corner_pct.values.astype(float)))
        grid.append(row)
    order = {**{m: i for i, m in enumerate(MEDIANS)}, **{bb: i for i, bb in enumerate(BOXES)},
             **{v: i for i, v in enumerate(ROTS.values())}}
    grid = pd.DataFrame(grid).sort_values(["item_median_cm", "box", "rotation"],
                                          key=lambda c: c.map(order)).reset_index(drop=True)
    grid.to_csv(RES / "grid.csv", index=False)
    mm = lambda c: [float(grid[c].min()), float(grid[c].max())]
    rob = {"settings": len(grid), "settings_with_70_85": int(grid.fill70_85_combo_high_pct.notna().sum()),
           "settings_with_85_100": int(grid.fill85_100_combo_high_pct.notna().sum()),
           "all_no_fit_high_pct": mm("all_no_fit_high_pct"), "all_single_pct": mm("all_single_pct"),
           "all_combo_low_pct": mm("all_combo_low_pct"), "all_combo_high_pct": mm("all_combo_high_pct"),
           "fill70_85_combo_low_pct": mm("fill70_85_combo_low_pct"), "fill70_85_combo_high_pct": mm("fill70_85_combo_high_pct"),
           "fill85_100_combo_low_pct": mm("fill85_100_combo_low_pct"), "fill85_100_combo_high_pct": mm("fill85_100_combo_high_pct"),
           "notfound_pct_max_bin": float(grid.notfound_pct_max_bin.max()),
           "fit_corner_pct_max_bin": float(grid.fit_corner_pct_max_bin.max())}
    for col in ["fill85_100_combo_high_pct", "all_single_pct", "all_combo_high_pct"]:
        rob[col + "_by_rotation"] = {k: [float(v.min()), float(v.max())] for k, v in grid.groupby("rotation", sort=False)[col]}
        rob[col + "_by_box"] = {k: [float(v.min()), float(v.max())] for k, v in grid.groupby("box", sort=False)[col]}
        rob[col + "_by_median"] = {str(k): [float(v.min()), float(v.max())] for k, v in grid.groupby("item_median_cm")[col]}

    out = {"base": {"setting": "荷物の中央値12cm・箱40×30×25・6通りの向き", "orders": sb["orders"],
                    "per_bin": PER_BIN, "natural_share_pct": [round(100 * float(x), 2) for x in nat],
                    "weighted_all": wb, "stratified_all": sb},
           "base_by_fill": bf.to_dict("records"), "base_by_items_stratified": bn.to_dict("records"),
           "example_pair_fill_le70": example, "example_fit_only_corner": example_corner,
           "robust": rob, "corner_search_limit": LIMIT, "max_batches": MAX_BATCH, "min_orders_per_bin": MIN_BIN}
    json.dump(out, open(RES / "a1299_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)

    # 図1：詰まり具合ごとの、入らなかった割合（内訳）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(bf))
    a1 = bf.single_pct.values; a2 = bf.pair_pct.values; a3 = bf.notfound_pct.values
    ax.bar(x, a1, color=GRAY, label="1つでも入らない荷物がある（確か）")
    ax.bar(x, a2, bottom=a1, color=ORANGE, label="どれか2つの組が入らない（確か）")
    ax.bar(x, a3, bottom=a1 + a2, color=LIGHT, label="探した並べ方では見つからない")
    for i in range(len(bf)):
        tot = a1[i] + a2[i] + a3[i]
        ax.text(i, tot + 1, f"{bf.no_fit_high_pct.iloc[i]:.2f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(bf.fill_bin)
    ax.set_xlabel(f"荷物の体積の合計÷箱の容量（各区分{PER_BIN}件）"); ax.set_ylabel("並べると入らなかった注文の割合（%）")
    ax.set_ylim(0, 112); ax.set_yticks(range(0, 101, 20))
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("体積では箱に収まる注文でも、詰まり具合が高いほど並べると入らない", pad=12)
    save(fig, "a1299_by_fill.png", SRC)

    g = grid.copy()
    g["label"] = g.item_median_cm.astype(str) + "cm・" + g.box + "・" + g.rotation
    y = np.arange(len(g))[::-1]
    # 図2：70〜85%の区分で、どの荷物も1つなら入る注文のうち、組み合わせで入らない割合（件数の足りる置き方だけ）
    g2 = g[g.fill70_85_combo_high_pct.notna()].reset_index(drop=True)
    y2 = np.arange(len(g2))[::-1]
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    lo = g2.fill70_85_combo_low_pct.values.astype(float); hi = g2.fill70_85_combo_high_pct.values.astype(float)
    ax.barh(y2, lo, color=ORANGE, label="どれか2つの組が入らない（確か）")
    ax.barh(y2, hi - lo, left=lo, color=LIGHT, label="探した並べ方では見つからない")
    for yi, v in zip(y2, hi):
        ax.text(v + 1, yi, f"{v:.2f}%", va="center", fontsize=8)
    ax.set_yticks(y2); ax.set_yticklabels(g2.label, fontsize=8)
    ax.set_xlabel("体積の合計が容量の70〜85%で、どの荷物も1つなら入る注文のうち、入らなかった割合（%）", fontsize=9)
    ax.set_xlim(0, 110); ax.set_xticks(range(0, 101, 20))
    ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=2)
    ax.set_title(f"件数の足りる{len(g2)}通りで、組み合わせで入らない割合（18通りのうち）", fontsize=12)
    save(fig, "a1299_grid_combo.png", SRC, y=-0.16)

    # 図3：18通りの、体積で入る注文全体のうち入らなかった割合（自然な割合で重みづけ）
    fig, ax = plt.subplots(figsize=(7.4, 6.4))
    s1 = g.all_single_pct.values; s2 = g.all_no_fit_high_pct.values - s1
    ax.barh(y, s1, color=GRAY, label="1つでも入らない荷物がある")
    ax.barh(y, s2, left=s1, color=ORANGE, label="組み合わせで入らない（見つからないを含む）")
    for yi, v in zip(y, g.all_no_fit_high_pct.values):
        ax.text(v + 1, yi, f"{v:.2f}%", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(g.label, fontsize=8)
    ax.set_xlabel("体積の合計が容量以下の注文全体のうち、入らなかった割合（%）")
    ax.set_xlim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("体積で入る注文全体では、1つで入らない長い荷物の分が大きい")
    save(fig, "a1299_grid_all.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
