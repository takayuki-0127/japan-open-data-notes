"""1150 置き場所の大きさを2倍にすると、当たり率はどれだけ上がるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ10万件への問い合わせの列。i番目に人気のデータが選ばれる確率は 1÷i^a に比例すると置いた
（a が大きいほど、よく使われるものへの偏りが大きい）。置き場所（キャッシュ）は件数で数え、いっぱいになったら
いちばん長く使われていないものから捨てる。
(1) 偏り a＝0.6・0.8・1.0・1.2 と、置き場所の大きさ（全体の0.25〜16%、2倍ずつ7段）ごとに、乱数の問い合わせ列で当たり率を数える
(2) 人気の上位を置き場所の大きさだけずっと置いたときの当たり率（式：上位の確率の合計）と比べる
(3) 2倍にするごとに当たり率が何ポイント上がるか、外れ率が何倍になるかを数える
(4) 確かめ：データの件数を2万件にして同じ割合の大きさで数える
"""
import json
import time
from collections import OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1150
SRC = "架空のアプリへの問い合わせ（作成者が置いた人気の偏りからの乱数、seed 1150）"
N_ITEMS = 100_000
ALPHAS = [0.6, 0.8, 1.0, 1.2]
SIZES_PCT = [0.25, 0.5, 1, 2, 4, 8, 16]
WARM, MEAS = 100_000, 300_000
BASE_A = 0.8


def r(x, d=4):
    return round(float(x), d)


def probs(n, a):
    p = 1.0 / np.arange(1, n + 1) ** a
    return p / p.sum()


def stream(rng, p, n):
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    return np.searchsorted(cdf, rng.random(n), side="right")


def recent_hit(seq, cap, warm):
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
    return hits / (len(seq) - warm)


def run(rng, n_items, alphas, label):
    rows = []
    for a in alphas:
        p = probs(n_items, a)
        seq = stream(rng, p, WARM + MEAS)
        cum = np.cumsum(p)
        for s in SIZES_PCT:
            cap = int(round(n_items * s / 100))
            h = recent_hit(seq, cap, WARM)
            rows.append({"items": n_items, "alpha": a, "size_pct": s, "size_items": cap,
                         "hit_recent_pct": r(h * 100, 2), "hit_top_formula_pct": r(cum[cap - 1] * 100, 2)})
        print(label, a, round(time.time() - T0, 1), flush=True)
    return pd.DataFrame(rows)


def add_steps(df):
    out = []
    for (n, a), g in df.groupby(["items", "alpha"]):
        g = g.sort_values("size_pct").reset_index(drop=True)
        for i in range(len(g) - 1):
            h0, h1 = g.hit_recent_pct[i], g.hit_recent_pct[i + 1]
            f0, f1 = g.hit_top_formula_pct[i], g.hit_top_formula_pct[i + 1]
            out.append({"items": n, "alpha": a, "from_pct": g.size_pct[i], "to_pct": g.size_pct[i + 1],
                        "hit_from_pct": h0, "hit_to_pct": h1, "gain_points": r(h1 - h0, 2),
                        "hit_ratio": r(h1 / h0, 3), "miss_ratio": r((100 - h1) / (100 - h0), 3),
                        "gain_points_top_formula": r(f1 - f0, 2)})
    return pd.DataFrame(out)


T0 = time.time()


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"items": N_ITEMS, "alphas": ALPHAS, "sizes_pct": SIZES_PCT, "warmup_requests": WARM,
                       "measured_requests": MEAS, "base_alpha": BASE_A}}
    df = run(rng, N_ITEMS, ALPHAS, "main")
    df.to_csv(RES / "hit_by_size.csv", index=False)
    st = add_steps(df)
    st.to_csv(RES / "double_steps.csv", index=False)

    # 確かめ：2万件
    df2 = run(rng, 20_000, ALPHAS, "small")
    df2.to_csv(RES / "check_20000_items.csv", index=False)
    st2 = add_steps(df2)
    st2.to_csv(RES / "check_20000_double_steps.csv", index=False)

    out["hit_by_size"] = df.to_dict("records")
    base = st[st.alpha == BASE_A]
    b1 = base[base.from_pct == 1].iloc[0]
    out["headline"] = {"base_alpha": BASE_A, "from_1_to_2": b1.to_dict(),
                       "base_gain_range_points": [float(base.gain_points.min()), float(base.gain_points.max())],
                       "all_gain_range_points": [float(st.gain_points.min()), float(st.gain_points.max())],
                       "all_hit_ratio_range": [float(st.hit_ratio.min()), float(st.hit_ratio.max())],
                       "all_miss_ratio_range": [float(st.miss_ratio.min()), float(st.miss_ratio.max())],
                       "n_steps": len(st)}
    by_a = {}
    for a in ALPHAS:
        s = st[st.alpha == a].sort_values("from_pct")
        g = s.gain_points.tolist()
        by_a[str(a)] = {"gains": g, "first": g[0], "last": g[-1],
                        "trend": "増える" if g[-1] > g[0] + 1 else ("減る" if g[-1] < g[0] - 1 else "ほぼ同じ"),
                        "recent_minus_top_points_range": [
                            r((df[df.alpha == a].hit_recent_pct - df[df.alpha == a].hit_top_formula_pct).min(), 2),
                            r((df[df.alpha == a].hit_recent_pct - df[df.alpha == a].hit_top_formula_pct).max(), 2)]}
    out["by_alpha"] = by_a
    # 2倍の大きさで当たり率が2倍以上になった段
    out["hit_doubled_steps"] = int((st.hit_ratio >= 2).sum())
    # 確かめ：2万件と10万件の同じ割合での差
    m = df.merge(df2, on=["alpha", "size_pct"], suffixes=("_100k", "_20k"))
    m["diff_points"] = (m.hit_recent_pct_20k - m.hit_recent_pct_100k).round(2)
    m[["alpha", "size_pct", "hit_recent_pct_100k", "hit_recent_pct_20k", "diff_points"]].to_csv(
        RES / "check_items_compare.csv", index=False)
    out["check_20000"] = {"diff_points_range": [float(m.diff_points.min()), float(m.diff_points.max())],
                          "gain_range_points": [float(st2.gain_points.min()), float(st2.gain_points.max())],
                          "trend_same": all(
                              (lambda g: ("増える" if g[-1] > g[0] + 1 else ("減る" if g[-1] < g[0] - 1 else "ほぼ同じ")))(
                                  st2[st2.alpha == a].sort_values("from_pct").gain_points.tolist()) == by_a[str(a)]["trend"]
                              for a in ALPHAS)}

    # データ：基本の偏りの問い合わせ列の先頭2万件
    p = probs(N_ITEMS, BASE_A)
    seq = stream(np.random.default_rng(SEED + 1), p, 20000)
    pd.DataFrame({"request_id": np.arange(1, 20001), "item_rank": seq + 1}).to_csv(DATA / "requests_alpha08.csv",
                                                                                   index=False)
    pd.DataFrame({"item_rank": np.arange(1, 1001), "prob_pct": np.round(p[:1000] * 100, 5)}).to_csv(
        DATA / "popularity_top1000_alpha08.csv", index=False)

    cols = dict(zip(ALPHAS, [GRAY, BLUE, ORANGE, INK]))
    # 図1：大きさと当たり率
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for a in ALPHAS:
        s = df[df.alpha == a]
        ax.plot(s.size_pct, s.hit_recent_pct, marker="o", ms=4, color=cols[a])
        ax.text(SIZES_PCT[-1] * 1.12, s.hit_recent_pct.iloc[-1], f"偏り a={a}", color=cols[a], fontsize=9, va="center")
    ax.set_xscale("log")
    ax.set_xticks(SIZES_PCT, [f"{x:g}" for x in SIZES_PCT])
    ax.set_xlim(0.2, 40)
    ax.set_ylim(0, 100)
    ax.set_xlabel("置き場所の大きさ（全体の件数の%、2倍ずつ）")
    ax.set_ylabel("当たり率（%）")
    ax.set_title("置き場所の大きさと当たり率（データ10万件）")
    save(fig, "a1150_hit_by_size.png", SRC)

    # 図2：2倍にするごとの上がり幅
    fig, ax = plt.subplots(figsize=(7, 4.2))
    labels = [f"{f:g}→{t:g}%" for f, t in zip(SIZES_PCT[:-1], SIZES_PCT[1:])]
    w = 0.2
    for j, a in enumerate(ALPHAS):
        s = st[st.alpha == a].sort_values("from_pct")
        ax.bar(np.arange(len(labels)) + (j - 1.5) * w, s.gain_points, w, color=cols[a], label=f"偏り a={a}")
    ax.set_xticks(np.arange(len(labels)), labels, fontsize=9)
    ax.set_ylim(0, None)
    ax.set_xlabel("置き場所の大きさ（全体の件数の%）")
    ax.set_ylabel("2倍にして上がった当たり率（ポイント）")
    ax.set_title("2倍にするごとの上がり幅")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left")
    save(fig, "a1150_gain_points.png", SRC)

    # 図3：古いものから捨てる場合と、人気の上位をずっと置いた場合（式）、偏り0.8
    fig, ax = plt.subplots(figsize=(7, 4.2))
    s = df[df.alpha == BASE_A]
    ax.plot(s.size_pct, s.hit_top_formula_pct, marker="s", ms=4, color=GREEN, label="人気の上位をずっと置く（式）")
    ax.plot(s.size_pct, s.hit_recent_pct, marker="o", ms=4, color=BLUE, label="いちばん長く使われていないものから捨てる")
    ax.set_xscale("log")
    ax.set_xticks(SIZES_PCT, [f"{x:g}" for x in SIZES_PCT])
    ax.set_ylim(0, 100)
    ax.set_xlabel("置き場所の大きさ（全体の件数の%）")
    ax.set_ylabel("当たり率（%）")
    ax.set_title(f"捨て方による違い（偏り a={BASE_A}）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1150_recent_vs_top.png", SRC)

    (RES / "a1150_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ["headline", "by_alpha", "hit_doubled_steps", "check_20000"]},
                     ensure_ascii=False, indent=1, default=float))
    print("sec", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
