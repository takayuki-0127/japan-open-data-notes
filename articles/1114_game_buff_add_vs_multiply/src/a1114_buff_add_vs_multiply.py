"""1114 強化の倍率を足し合わせる決まりと掛け合わせる決まりでは、重ねたときの強さはどれだけ違うのか？（架空のデータ）

作成者が置いた架空のゲームの強化（「攻撃力+20%」のような倍率）。
決まりは3つ：
  足す決まり：強さ＝1＋（倍率の合計）
  掛ける決まり：強さ＝（1＋倍率）の積
  種類ごとに足して種類どうしは掛ける決まり：強化を3つの種類に分け、種類の中で足し、種類どうしを掛ける
(1) +20%を1〜8個重ねたときの強さ（式どおり）と、次の1個の伸び
(2) +20%を6個、種類への分け方を変えたときの強さ（式どおり）
(3) 架空の遊ぶ人1万人（強化の数0〜8個、1個の倍率5〜40%）で、上位1割・真ん中・下位1割の強さの開き
(4) 確かめ：倍率の幅×強化の数の上限の9通り
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1114
SRC = "架空のゲームの強化（作成者が置いた倍率と個数からの乱数、seed 1114）"
B = 0.20
N_PLAYERS = 10000
KINDS = 3
BASE = {"size_lo": 0.05, "size_hi": 0.40, "max_count": 8}
GRID_SIZE = [(0.05, 0.20), (0.05, 0.40), (0.10, 0.60)]
GRID_MAX = [4, 8, 12]


def r(x, d=4):
    return round(float(x), d)


def players(rng, n, lo, hi, kmax):
    k = rng.integers(0, kmax + 1, n)
    size = np.round(rng.uniform(lo, hi, (n, kmax)), 2)
    mask = np.arange(kmax)[None, :] < k[:, None]
    size = np.where(mask, size, 0.0)
    kind = rng.integers(0, KINDS, (n, kmax))
    add = 1 + size.sum(1)
    mul = np.prod(1 + size, 1)
    mix = np.ones(n)
    for g in range(KINDS):
        mix *= 1 + np.where(kind == g, size, 0.0).sum(1)
    return k, size, kind, {"足す": add, "種類ごとに足して掛ける": mix, "掛ける": mul}


def spread(p):
    q10, q50, q90 = np.quantile(p, [0.1, 0.5, 0.9])
    return {"p10": r(q10), "median": r(q50), "p90": r(q90), "max": r(p.max()),
            "p90_over_median": r(q90 / q50), "p90_over_p10": r(q90 / q10), "max_over_median": r(p.max() / q50)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setting": {"buff": B, "players": N_PLAYERS, "kinds": KINDS, **BASE}}

    # (1) 同じ+20%を重ねる（式）
    st = []
    for n in range(0, 9):
        a, m = 1 + B * n, (1 + B) ** n
        st.append({"count": n, "add": r(a), "multiply": r(m), "multiply_over_add": r(m / a),
                   "next_gain_add_pct": round((1 + B * (n + 1)) / a * 100 - 100, 2), "next_gain_multiply_pct": round(B * 100, 2)})
    st = pd.DataFrame(st)
    st.to_csv(RES / "stack_same.csv", index=False)
    out["stack_same"] = st.to_dict("records")

    # (2) +20%を6個、種類への分け方（式）
    splits = [(6,), (3, 3), (4, 2), (5, 1), (2, 2, 2), (4, 1, 1), (1, 1, 1, 1, 1, 1)]
    sp = []
    for s in splits:
        v = float(np.prod([1 + B * x for x in s]))
        sp.append({"split": "・".join(str(x) for x in s), "kinds_used": len(s), "power": r(v)})
    sp = pd.DataFrame(sp)
    sp.to_csv(RES / "split_six.csv", index=False)
    out["split_six"] = sp.to_dict("records")
    # 種類の中に3個ある所へ足すか、空の種類へ足すか（7個目）
    out["seventh_buff"] = {"into_kind_with_3_pct": round((1 + B * 4) / (1 + B * 3) * 100 - 100, 2),
                           "into_empty_kind_pct": round(B * 100, 2)}

    # (3) 1万人
    k, size, kind, pw = players(rng, N_PLAYERS, BASE["size_lo"], BASE["size_hi"], BASE["max_count"])
    pl = []
    for name, p in pw.items():
        pl.append({"rule": name, **spread(p),
                   "mean_full_count": r(p[k == BASE["max_count"]].mean()), "mean_one": r(p[k == 1].mean())})
    pl = pd.DataFrame(pl)
    pl.to_csv(RES / "players.csv", index=False)
    out["players"] = pl.to_dict("records")
    full = k == BASE["max_count"]
    out["players_extra"] = {
        "full_count_share_pct": round(full.mean() * 100, 2),
        "multiply_over_add_full_mean": r((pw["掛ける"][full] / pw["足す"][full]).mean()),
        "multiply_over_add_full_max": r((pw["掛ける"][full] / pw["足す"][full]).max()),
        "top100_overlap_count": int(len(set(np.argsort(-pw["足す"], kind="stable")[:100]) &
                                          set(np.argsort(-pw["掛ける"], kind="stable")[:100]))),
    }
    df = pd.DataFrame({"player": np.arange(1, N_PLAYERS + 1), "count": k})
    for j in range(BASE["max_count"]):
        df[f"buff{j + 1}"] = size[:, j]
        df[f"kind{j + 1}"] = np.where(size[:, j] > 0, kind[:, j] + 1, 0)
    for name, key in [("足す", "power_add"), ("種類ごとに足して掛ける", "power_mix"), ("掛ける", "power_multiply")]:
        df[key] = np.round(pw[name], 4)
    df.head(2000).to_csv(DATA / "players_first2000.csv", index=False)

    # 個数ごとの平均の強さ
    bc = []
    for c in range(BASE["max_count"] + 1):
        sel = k == c
        bc.append({"count": c, "players": int(sel.sum()),
                   **{key: r(pw[name][sel].mean()) for name, key in
                      [("足す", "add_mean"), ("種類ごとに足して掛ける", "mix_mean"), ("掛ける", "multiply_mean")]}})
    bc = pd.DataFrame(bc)
    bc.to_csv(RES / "by_count.csv", index=False)

    # (4) 9通り
    gr = []
    for lo, hi in GRID_SIZE:
        for km in GRID_MAX:
            g_rng = np.random.default_rng([SEED, int(lo * 100), int(hi * 100), km])
            _, _, _, p2 = players(g_rng, N_PLAYERS, lo, hi, km)
            row = {"size_lo_pct": round(lo * 100), "size_hi_pct": round(hi * 100), "max_count": km}
            for name, key in [("足す", "add"), ("種類ごとに足して掛ける", "mix"), ("掛ける", "multiply")]:
                s = spread(p2[name])
                row[f"{key}_p90_over_median"] = s["p90_over_median"]
                row[f"{key}_max"] = s["max"]
            row["multiply_over_add_p90_over_median"] = r(row["multiply_p90_over_median"] / row["add_p90_over_median"])
            gr.append(row)
    gr = pd.DataFrame(gr)
    gr.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {
        "n": len(gr),
        "multiply_wider_count": int((gr.multiply_p90_over_median > gr.add_p90_over_median).sum()),
        "add_p90_over_median_range": [float(gr.add_p90_over_median.min()), float(gr.add_p90_over_median.max())],
        "mix_p90_over_median_range": [float(gr.mix_p90_over_median.min()), float(gr.mix_p90_over_median.max())],
        "multiply_p90_over_median_range": [float(gr.multiply_p90_over_median.min()), float(gr.multiply_p90_over_median.max())],
        "multiply_max_range": [float(gr.multiply_max.min()), float(gr.multiply_max.max())],
        "add_max_range": [float(gr.add_max.min()), float(gr.add_max.max())],
    }

    # 図1：同じ+20%を重ねる
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(st["count"], st["add"], marker="o", color=BLUE, label="足す（1＋0.2×個数）")
    ax.plot(st["count"], st["multiply"], marker="o", color=ORANGE, label="掛ける（1.2の個数乗）")
    for n in [5, 8]:
        a, m = st.loc[n, "add"], st.loc[n, "multiply"]
        ax.text(n, a - 0.35, f"{a}", ha="center", color=BLUE, fontsize=9)
        ax.text(n, m + 0.15, f"{m}", ha="center", color=ORANGE, fontsize=9)
    ax.set_ylim(0, 5)
    ax.set_xlabel("重ねた+20%の強化の個数")
    ax.set_ylabel("強さ（強化なし＝1）")
    ax.set_title("+20%を重ねたときの強さ（式どおり）")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1114_stack.png", SRC)

    # 図2：1万人の強さの分布（上位1割/真ん中）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    names = list(pw.keys())
    cols = [BLUE, GREEN, ORANGE]
    vals = [pl.loc[pl.rule == nm, "p90_over_median"].iloc[0] for nm in names]
    xs = np.arange(3)
    ax.bar(xs, vals, color=cols, width=0.55)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.03, f"{v}倍", ha="center", fontsize=9)
    ax.set_xticks(xs, names)
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_ylabel("上位1割の位置÷真ん中の強さ（倍）")
    ax.set_title("架空の1万人（強化0〜8個・1個5〜40%）の強さの開き")
    save(fig, "a1114_players.png", SRC)

    # 図3：9通り
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    lab = [f"{a}〜{b}%\n上限{c}個" for a, b, c in zip(gr.size_lo_pct, gr.size_hi_pct, gr.max_count)]
    xs = np.arange(len(gr))
    w = 0.27
    for i, (key, nm, col) in enumerate([("add", "足す", BLUE), ("mix", "種類ごとに足して掛ける", GREEN), ("multiply", "掛ける", ORANGE)]):
        ax.bar(xs + (i - 1) * w, gr[f"{key}_p90_over_median"], w, color=col, label=nm)
    ax.set_xticks(xs, lab, fontsize=8)
    ax.set_ylim(0, gr.multiply_p90_over_median.max() * 1.15)
    ax.set_ylabel("上位1割の位置÷真ん中の強さ（倍）")
    ax.set_title("倍率の幅と個数の上限を変えた9通り")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1114_grid.png", SRC)

    (RES / "a1114_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(bc)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
