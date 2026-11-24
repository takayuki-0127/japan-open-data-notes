"""1241 分類の決まりを途中で書き直すと、前に付けた件とあとで付けた件で何がずれるのか？（架空のデータ）

架空の問い合わせ文に「返品」「交換」「その他」の分類を付ける。中身の種類（返品だけ・返品に似た件・境目の件・交換だけ・その他）と
その割合を作成者が置き、16週のあいだ中身は変えない。9週目から決まりを書き直し、境目の件（返品して別の品に替えたい）を
「返品」から「交換」に変える。付け手は新しい決まりに少しずつ慣れ、書き直しの範囲の外の「返品に似た件」にも交換を付けすぎる。
付いた分類で、週ごとの割合と、付いた分類から作った分類する仕組み（見た目の値に1本の境目を引く）の当たりを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1241
SRC = "架空の問い合わせ文（作成者が置いた中身の種類と付け手の慣れ方からの乱数、seed 1241）"
WEEKS, PER = 16, 800
KINDS = ["返品だけ", "返品に似た件", "境目の件", "交換だけ", "その他"]
LABELS = ["返品", "交換", "その他"]
MU = {0: -1.5, 1: -0.6, 2: 0.0, 3: 1.2}  # 見た目の値（返品寄り−、交換寄り＋）の中心。ばらつきは0.5
SD = 0.5
SPEED = {"fast": [0.98], "base": [0.5, 0.75, 0.9, 0.98], "slow": [0.2, 0.36, 0.52, 0.67, 0.82, 0.98]}
SPEED_NAME = {"fast": "すぐ慣れる", "base": "基本（4週で慣れる）", "slow": "ゆっくり（6週で慣れる）"}
SPILL = [0.15, 0.12, 0.08, 0.05]  # 書き直し後の週ごとに「返品に似た件」に交換を付ける確率（4週目以降0.05）
BASE = dict(m_share=0.06, speed="base", w_change=9)


def kind_shares(m_share):
    # 返品だけ＋返品に似た件＝18%（うち似た件3割）、交換だけ12%、境目 m_share、残りがその他
    a = 0.18
    return np.array([a * 0.7, a * 0.3, m_share, 0.12, 1 - a - 0.12 - m_share])


def adopt(week, w_change, speed):
    if week < w_change:
        return 0.0
    s = SPEED[speed]
    return s[min(week - w_change, len(s) - 1)]


def spill(week, w_change):
    if week < w_change:
        return 0.01
    return SPILL[min(week - w_change, len(SPILL) - 1)]


def make(rng, m_share=0.06, speed="base", w_change=9):
    p = kind_shares(m_share)
    n = WEEKS * PER
    week = np.repeat(np.arange(1, WEEKS + 1), PER)
    k = rng.choice(5, n, p=p)
    centers = np.array([MU[0], MU[1], MU[2], MU[3], 0.0])
    x = np.where(k < 4, centers[k] + SD * rng.standard_normal(n), np.nan)
    truth_new = np.where(k == 4, 2, np.where(np.isin(k, [0, 1]), 0, 1))
    lab = np.where(k == 4, 2, np.where(np.isin(k, [0, 1]), 0, 1))
    ad = np.array([adopt(w, w_change, speed) for w in range(1, WEEKS + 1)])[week - 1]
    new = rng.random(n) < ad
    lab = np.where(k == 2, np.where(new, 1, 0), lab)  # 境目の件：古い決まりは返品、新しい決まりは交換
    spv = np.array([spill(w, w_change) for w in range(1, WEEKS + 1)])[week - 1]
    sp = rng.random(n) < spv
    lab = np.where((k == 1) & sp, 1, lab)  # 返品に似た件に交換を付けすぎる
    err = rng.random(n) < 0.02  # 決まりと関係のないまちがい（残り2つへ均等）
    lab = np.where(err, (lab + rng.integers(1, 3, n)) % 3, lab)
    return pd.DataFrame({"week": week, "kind": k, "x": x, "label": lab, "truth_new": truth_new})


def fit_cut(x, y):
    """返品(0)・交換(1)の付いた件で、x がこの値を超えたら交換とする境目を、付いた分類と最もよく合うように決める。"""
    o = np.argsort(x, kind="stable")
    xs, ys = x[o], y[o]
    zeros_left = np.concatenate([[0], np.cumsum(ys == 0)])
    ones_right = (ys == 1).sum() - np.concatenate([[0], np.cumsum(ys == 1)])
    i = int(np.argmax(zeros_left + ones_right))
    if i == 0:
        return xs[0] - 1
    if i == len(xs):
        return xs[-1] + 1
    return (xs[i - 1] + xs[i]) / 2


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def true_acc(cut, m_share):
    """新しい決まりの正解に対する当たり（返品・交換の中身の件、式で出す）。"""
    p = kind_shares(m_share)[:4]
    acc_k = []
    for k in range(4):
        above = 1 - ncdf((cut - MU[k]) / SD)
        acc_k.append(1 - above if k in (0, 1) else above)
    acc_k = np.array(acc_k)
    return float((acc_k * p).sum() / p.sum()), acc_k


def train_sets(df, rng, w_change):
    """学習に使う件の作り方。返品・交換と付いた件だけを使う。"""
    hold = rng.random(len(df)) < 0.2
    d = df[~hold & (df.label < 2) & (df.kind < 4)]
    out = {}
    out["all16"] = (d.x.values, d.label.values)
    out["before"] = (d[d.week < w_change].x.values, d[d.week < w_change].label.values)
    out["after"] = (d[d.week >= w_change].x.values, d[d.week >= w_change].label.values)
    late = d.week >= w_change + 3
    out["after_skip3"] = (d[late].x.values, d[late].label.values)
    # 前の週の「返品」を見直して付け直す（境目の件を見つける確率0.9、返品に似た件を交換にしてしまう確率0.05）
    dd = d.copy()
    old = dd.week < w_change
    fx = old & (dd.label == 0) & (dd.kind == 2) & (rng.random(len(dd)) < 0.9)
    over = old & (dd.label == 0) & (dd.kind == 1) & (rng.random(len(dd)) < 0.05)
    lab = dd.label.values.copy()
    lab[(fx | over).values] = 1
    out["relabel"] = (dd.x.values, lab)
    # 比べる相手：16週すべてが新しい決まりで付いていたら（決まりと関係のないまちがい2%は残す）
    flip = rng.random(len(d)) < 0.02
    out["ideal_new"] = (d.x.values, np.where(flip, 1 - d.truth_new.values, d.truth_new.values))
    hd = df[hold & (df.label < 2) & (df.kind < 4)]
    return out, hd


def one(rng, m_share=0.06, speed="base", w_change=9, keep=False):
    df = make(rng, m_share, speed, w_change)
    share = (df.label.values == 1).reshape(WEEKS, PER).mean(1)
    sets, hd = train_sets(df, rng, w_change)
    res = {"share_week": share}
    for name, (x, y) in sets.items():
        c = fit_cut(x, y)
        acc, acc_k = true_acc(c, m_share)
        res[name] = {"cut": c, "acc": acc, "acc_border": acc_k[2], "acc_similar": acc_k[1]}
    # 16週から取った「混ざった」テストの件で数えた当たり（付いた分類と比べる）と、新しい決まりの正解と比べた当たり
    c = res["all16"]["cut"]
    pred = (hd.x.values > c).astype(int)
    res["all16"]["acc_mixed_test"] = float((pred == hd.label.values).mean())
    res["all16"]["acc_new_on_test"] = float((pred == hd.truth_new.values).mean())
    border = hd.kind.values == 2
    res["all16"]["border_mixed_test"] = float((pred[border] == hd.label.values[border]).mean())
    res["all16"]["border_new_on_test"] = float((pred[border] == hd.truth_new.values[border]).mean())
    # 似た件に交換が付いた割合（書き直しの前と、慣れたあと）
    sim = df[df.kind == 1]
    res["similar_exchange_before"] = float((sim[sim.week < w_change].label == 1).mean())
    res["similar_exchange_after"] = float((sim[sim.week >= w_change].label == 1).mean())
    if keep:
        return res, df
    return res


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res1, df1 = one(rng, **BASE, keep=True)
    out1 = df1.copy()
    out1["kind"] = [KINDS[i] for i in out1.kind]
    out1["label"] = [LABELS[i] for i in out1.label]
    out1["truth_new"] = [LABELS[i] for i in out1.truth_new]
    out1["x"] = out1.x.round(4)
    out1.insert(0, "item_id", np.arange(1, len(out1) + 1))
    out1.to_csv(DATA / "items_one_set.csv", index=False)

    # 1) 基本の置き方で200回
    reps = [one(np.random.default_rng([SEED, 1, i]), **BASE) for i in range(200)]
    share = np.array([x["share_week"] for x in reps])
    wk = pd.DataFrame({"week": np.arange(1, WEEKS + 1), "exchange_share_mean": share.mean(0).round(4),
                       "p10": np.percentile(share, 10, axis=0).round(4), "p90": np.percentile(share, 90, axis=0).round(4)})
    wk.to_csv(RES / "weekly_exchange_share.csv", index=False)
    w = BASE["w_change"]
    p = kind_shares(BASE["m_share"])
    # 週ごとの「交換」の割合の式：中身の割合×付ける確率（まちがい2%は残り2つへ均等）
    def share_formula(week):
        a = adopt(week, w, BASE["speed"])
        s = spill(week, w)
        to_ex = {0: 0.0, 1: s, 2: a, 3: 1.0, 4: 0.0}
        tot = 0.0
        for k in range(5):
            if k == 4:
                pe = 0.02 / 2
            else:
                pe = to_ex[k] * 0.98 + (1 - to_ex[k]) * 0.02 / 2
            tot += p[k] * pe
        return tot
    f_before, f_after_first, f_steady = share_formula(w - 1), share_formula(w), share_formula(WEEKS)
    jump_first = share[:, w - 1] - share[:, w - 2]
    jump_steady = share[:, w + 2:].mean(1) - share[:, :w - 1].mean(1)
    variants = ["before", "all16", "after", "after_skip3", "relabel", "ideal_new"]
    vt = []
    for v in variants:
        a = np.array([x[v]["acc"] for x in reps])
        b = np.array([x[v]["acc_border"] for x in reps])
        s_ = np.array([x[v]["acc_similar"] for x in reps])
        c = np.array([x[v]["cut"] for x in reps])
        vt.append({"train": v, "cut_mean": r(c.mean()), "acc_mean": r(a.mean()), "acc_p10": r(np.percentile(a, 10)),
                   "acc_p90": r(np.percentile(a, 90)), "acc_border_mean": r(b.mean()),
                   "acc_border_p10": r(np.percentile(b, 10)), "acc_border_p90": r(np.percentile(b, 90)),
                   "acc_similar_mean": r(s_.mean())})
    vt = pd.DataFrame(vt)
    vt.to_csv(RES / "train_variants.csv", index=False)
    mixed = {k: r(np.mean([x["all16"][k] for x in reps])) for k in
             ["acc_mixed_test", "acc_new_on_test", "border_mixed_test", "border_new_on_test"]}
    mixed["all_gap_points"] = r((mixed["acc_mixed_test"] - mixed["acc_new_on_test"]) * 100, 2)
    mixed["border_gap_points"] = r((mixed["border_mixed_test"] - mixed["border_new_on_test"]) * 100, 2)
    headline = {
        "weeks": WEEKS, "per_week": PER, "reps": 200, "kind_shares": {KINDS[i]: r(p[i]) for i in range(5)},
        "exchange_share_formula": {"week_before": r(f_before), "first_week_after": r(f_after_first), "steady": r(f_steady),
                                   "jump_first": r(f_after_first - f_before), "jump_steady": r(f_steady - f_before)},
        "exchange_share_sim": {"weeks_1_8_mean": r(share[:, :w - 1].mean()), "week_8": r(share[:, w - 2].mean()),
                               "week_9": r(share[:, w - 1].mean()), "weeks_12_16_mean": r(share[:, w + 2:].mean()),
                               "jump_first_mean": r(jump_first.mean()), "jump_steady_mean": r(jump_steady.mean()),
                               "first_over_steady": r(jump_first.mean() / jump_steady.mean())},
        "similar_exchange_before": r(np.mean([x["similar_exchange_before"] for x in reps])),
        "similar_exchange_after": r(np.mean([x["similar_exchange_after"] for x in reps])),
        "train_variants": {row["train"]: row for row in vt.to_dict("records")},
        "mixed_test": mixed,
    }

    # 2) 確かめ：境目の件の割合×慣れ方×書き直す週＝27通り（各100回）
    grid = []
    for ms in [0.03, 0.06, 0.12]:
        for sp in ["fast", "base", "slow"]:
            for wc in [5, 9, 13]:
                rr = [one(np.random.default_rng([SEED, 2, int(ms * 100), list(SPEED).index(sp), wc, i]),
                          m_share=ms, speed=sp, w_change=wc) for i in range(100)]
                sh = np.array([x["share_week"] for x in rr])
                jf = sh[:, wc - 1] - sh[:, wc - 2]
                after_cut = min(wc + 2, WEEKS - 1)
                js = sh[:, after_cut:].mean(1) - sh[:, :wc - 1].mean(1)
                grid.append({"m_share": ms, "speed": sp, "w_change": wc,
                             "new_rule_weeks_share": r((WEEKS - wc + 1) / WEEKS),
                             "jump_first": r(jf.mean()), "jump_steady": r(js.mean()), "first_over_steady": r(jf.mean() / js.mean()),
                             "acc_all16": r(np.mean([x["all16"]["acc"] for x in rr])),
                             "acc_border_all16": r(np.mean([x["all16"]["acc_border"] for x in rr])),
                             "acc_ideal": r(np.mean([x["ideal_new"]["acc"] for x in rr])),
                             "acc_relabel": r(np.mean([x["relabel"]["acc"] for x in rr])),
                             "acc_border_relabel": r(np.mean([x["relabel"]["acc_border"] for x in rr])),
                             "acc_mixed_test": r(np.mean([x["all16"]["acc_mixed_test"] for x in rr])),
                             "acc_new_on_test": r(np.mean([x["all16"]["acc_new_on_test"] for x in rr]))})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    grid["gap_ideal"] = grid.acc_ideal - grid.acc_all16
    grid["gap_test"] = grid.acc_mixed_test - grid.acc_new_on_test
    robust = {"combos": 27, "reps_each": 100,
              "first_over_steady": [r(grid.first_over_steady.min()), r(grid.first_over_steady.max())],
              "first_over_steady_by_speed": {s: [r(grid[grid.speed == s].first_over_steady.min()),
                                                 r(grid[grid.speed == s].first_over_steady.max())] for s in SPEED},
              "acc_border_all16_by_week": {str(wc): [r(grid[grid.w_change == wc].acc_border_all16.min()),
                                                     r(grid[grid.w_change == wc].acc_border_all16.max())] for wc in [5, 9, 13]},
              "acc_border_all16": [r(grid.acc_border_all16.min()), r(grid.acc_border_all16.max())],
              "acc_border_relabel": [r(grid.acc_border_relabel.min()), r(grid.acc_border_relabel.max())],
              "gap_ideal_points": [r(grid.gap_ideal.min() * 100, 3), r(grid.gap_ideal.max() * 100, 3)],
              "gap_test_points": [r(grid.gap_test.min() * 100, 3), r(grid.gap_test.max() * 100, 3)],
              "combos_mixed_test_higher": int((grid.gap_test > 0).sum())}
    out = {"headline": headline, "robust": robust,
           "setting": {**BASE, "x_center": {KINDS[k]: MU[k] for k in MU}, "x_sd": SD, "speed": SPEED, "spill": SPILL,
                       "random_error": 0.02, "relabel_find": 0.9, "relabel_over": 0.05, "holdout": 0.2}}
    with open(RES / "a1241_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：週ごとの「交換」の割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(1, WEEKS + 1)
    ax.fill_between(x, wk.p10 * 100, wk.p90 * 100, color=LIGHT, alpha=0.6)
    ax.plot(x, wk.exchange_share_mean * 100, "o-", color=BLUE, label="付いた分類で数えた「交換」の割合")
    ax.axvline(w - 0.5, color=GRAY, lw=1, ls="--")
    ax.text(w - 0.4, 3, "9週目から決まりを書き直す", fontsize=9, color=INK)
    ax.set_ylim(0, 25)
    ax.set_xticks(x)
    ax.set_xlabel("週")
    ax.set_ylabel("割合（%）")
    ax.set_title("中身は16週同じでも、「交換」の割合は段になって上がった（200回の平均、帯は10〜90%）", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1241_weekly_share.png", SRC)

    # 図2：学習に使った件の作り方と、境目の件の当たり
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    names = {"before": "書き直し前\nの8週だけ", "all16": "16週\nすべて", "after": "書き直し後\nの8週だけ",
             "after_skip3": "書き直し後の\n最初3週を除く", "relabel": "前の「返品」を\n見直して16週",
             "ideal_new": "（比べる相手）\n16週とも新しい\n決まりなら"}
    vals = vt.set_index("train").loc[variants]
    cols = [GRAY, ORANGE, BLUE, BLUE, GREEN, LIGHT]
    ax.bar(range(len(variants)), vals.acc_border_mean * 100, color=cols, width=0.6)
    for i, v in enumerate(vals.acc_border_mean * 100):
        ax.text(i, v + 1.5, f"{v:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(range(len(variants)), [names[v] for v in variants], fontsize=8.5)
    ax.set_ylim(0, 110)
    ax.set_ylabel("境目の件を「交換」と当てた割合（%）")
    ax.set_title("付いた分類から作った仕組みの、境目の件の当たり（新しい決まりで、200回の平均）", fontsize=11)
    save(fig, "a1241_border_accuracy.png", SRC)

    # 図3：27通り、16週すべてで作った仕組みの境目の件の当たり
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    cmap = {"fast": GREEN, "base": BLUE, "slow": ORANGE}
    for sp in SPEED:
        g = grid[grid.speed == sp]
        ax.scatter(g.new_rule_weeks_share * 100 + {"fast": -1, "base": 0, "slow": 1}[sp], g.acc_border_all16 * 100,
                   color=cmap[sp], s=28, label=f"付け手が{SPEED_NAME[sp]}")
    ax.set_xticks([r((WEEKS - wc + 1) / WEEKS) * 100 for wc in [5, 9, 13]],
                  [f"{(WEEKS - wc + 1) / WEEKS * 100:.0f}%\n（{wc}週目から）" for wc in [5, 9, 13]])
    ax.set_ylim(0, 105)
    ax.set_xlabel("16週のうち、書き直したあとの週の割合")
    ax.set_ylabel("境目の件を「交換」と当てた割合（%）")
    ax.set_title("16週すべての件で作った仕組みの、境目の件の当たり（27通り、各100回）", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.text(0.99, 0.97, "同じ色の3点は、境目の件の割合3・6・12%", transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, color=GRAY)
    save(fig, "a1241_grid.png", SRC, y=-0.06)
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
