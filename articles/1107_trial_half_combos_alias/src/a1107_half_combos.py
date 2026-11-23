"""1107 組み合わせの半分だけを試すと、何と何の効き目が見分けられなくなるのか？（架空のデータ）

架空の塗装工房で、板に塗った仕上がりの「むらの少なさの点数」（高いほど良い）を、4つの条件
（A 塗料の薄め方・B 乾かす温度・C 吹き付けの距離・D 1回目と2回目の間の時間、それぞれ2段階）で試す。
16通りすべてを試す場合と、半分の8通りだけを試す場合（選び方2つ）で、効き目の見積もりがどう重なるかを数える。
本当の効き目は作成者が置き、1枚ごとの仕上がりには作成者が置いたばらつきを足す。
"""
import json
import itertools
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1107
SRC = "架空の塗装工房の試し塗り（作成者が置いた効き目とばらつきからの乱数、seed 1107）"
LET = "ABCD"
NAMES_JA = {"A": "A 薄め方", "B": "B 乾かす温度", "C": "C 吹き付けの距離", "D": "D 塗る間の時間"}
BASE_LEVEL = 60.0
NOISE = 2.0          # 1枚ごとのばらつき（標準偏差、点）
THRESH = 2.0         # 「効き目あり」とみなす大きさ（作成者が置いた目安、点）
REPS = 2000
WORLDS = 2000
BASE_RAND = {"main_sd": 3.0, "p_int": 0.3, "int_sd": 3.0}
GRID_P = [0.0, 0.15, 0.3, 0.6]
GRID_S = [1.5, 3.0, 6.0]

# 効き目の名前（空でない部分集合、次数の順）
TERMS = ["".join(c) for k in range(1, 5) for c in itertools.combinations(LET, k)]
COMBOS = np.array(list(itertools.product([-1, 1], repeat=4)))  # 16通り（A,B,C,D）


def r(x, d=4):
    return round(float(x), d)


def col(rows, term):
    return np.prod(rows[:, [LET.index(c) for c in term]], axis=1)


X16 = np.column_stack([col(COMBOS, t) for t in TERMS])  # 16×15
DESIGNS = {
    "full16": np.arange(16),
    "half_D_ABC": np.where(COMBOS[:, 3] == COMBOS[:, 0] * COMBOS[:, 1] * COMBOS[:, 2])[0],
    "half_D_AB": np.where(COMBOS[:, 3] == COMBOS[:, 0] * COMBOS[:, 1])[0],
}
DESIGN_JA = {"full16": "16通りすべて（16枚）", "half_D_ABC": "半分8通り：D＝A×B×C の列（8枚）",
             "half_D_AB": "半分8通り：D＝A×B の列（8枚）", "half_D_ABC_x2": "半分8通りを2枚ずつ（16枚）"}


def alias_groups(idx):
    """半分の組で、同じ列になる効き目どうしをまとめる"""
    rows = COMBOS[idx]
    groups = {}
    for t in TERMS:
        c = tuple(col(rows, t))
        neg = tuple(-v for v in c)
        if neg in groups:
            groups[neg].append("-" + t)
        else:
            groups.setdefault(c, []).append(t)
    out = []
    for c, ts in groups.items():
        if all(v == 1 for v in c):
            continue  # 平均と同じ列（すべて+1）は効き目の列から外す
        out.append(ts)
    # 平均（I）と同じ列になるもの
    const = [t for t in TERMS if np.all(col(rows, t) == 1)]
    return out, const


def model_terms(design):
    """見積もりに使う列と、その列の効き目をどの名前の効き目とみなすか（次数の低い順、同じ次数ならアルファベット順）"""
    if design == "full16":
        return [t for t in TERMS if len(t) <= 2]
    groups, _ = alias_groups(DESIGNS[design if design in DESIGNS else "half_D_ABC"])
    names = []
    for g in groups:
        g2 = sorted([t.lstrip("-") for t in g], key=lambda s: (len(s), s))
        if len(g2[0]) <= 2:
            names.append(g2[0])
    return sorted(names, key=lambda s: (len(s), s))


def run_design(beta, design, rng, reps):
    """beta: (W,15) 係数（効き目の半分）。W 個の世界それぞれで1回ずつ試す。返り値：見積もった効き目 (W,15)、選んだ組"""
    base = design.replace("_x2", "")
    idx = DESIGNS[base]
    mult = 2 if design.endswith("_x2") else 1
    idx = np.tile(idx, mult)
    rows = COMBOS[idx]
    Xr = np.column_stack([col(rows, t) for t in TERMS])
    ytrue = BASE_LEVEL + beta @ Xr.T  # (W,n)
    y = ytrue + rng.normal(0, NOISE, ytrue.shape)
    est_eff = 2 * (y @ Xr) / len(idx)  # 各列の「高い−低い」（効き目の見積もり）
    terms = model_terms(base)
    ti = [TERMS.index(t) for t in terms]
    pred = BASE_LEVEL + (est_eff[:, ti] / 2) @ X16[:, ti].T  # 16通りの見込み
    choose = pred.argmax(1)
    return est_eff, choose


def random_world(rng, n, main_sd, p_int, int_sd):
    eff = np.zeros((n, 15))
    eff[:, :4] = rng.normal(0, main_sd, (n, 4))
    two = rng.normal(0, int_sd, (n, 6)) * (rng.random((n, 6)) < p_int)
    eff[:, 4:10] = two
    return eff / 2  # 係数＝効き目の半分


def summarize_world(beta, rng):
    true16 = BASE_LEVEL + beta @ X16.T
    best = true16.argmax(1)
    out = {}
    for d in ["full16", "half_D_ABC", "half_D_AB", "half_D_ABC_x2"]:
        est, ch = run_design(beta, d, rng, None)
        true_eff = 2 * beta
        mis_main = (np.abs(est[:, :4] - true_eff[:, :4]) >= THRESH).mean()
        gap = true16[np.arange(len(ch)), best] - true16[np.arange(len(ch)), ch]
        hit = (gap < 1e-9).mean()  # 選んだ組の本当の点数がいちばん良い点数と同じなら当たり（同点の組も当たり）
        short = gap.mean()
        out[d] = {"best_hit": r(hit), "shortfall_mean": r(short, 3), "main_off_2pt_share": r(mis_main)}
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setup": {"base_level": BASE_LEVEL, "noise_sd": NOISE, "threshold_points": THRESH, "reps": REPS,
                     "worlds": WORLDS, "random_world_base": BASE_RAND, "grid_p_int": GRID_P, "grid_int_sd": GRID_S}}

    # 1) 半分の組で重なる効き目（式どおり：列が同じになる組）
    rows_alias = []
    for d in ["half_D_ABC", "half_D_AB"]:
        groups, const = alias_groups(DESIGNS[d])
        for g in groups:
            rows_alias.append({"design": d, "same_column": " = ".join(g),
                               "has_main": any(len(t.lstrip("-")) == 1 for t in g),
                               "n_main": sum(len(t.lstrip("-")) == 1 for t in g),
                               "n_two": sum(len(t.lstrip("-")) == 2 for t in g)})
        out[f"alias_{d}"] = {"groups": [" = ".join(g) for g in groups], "same_as_mean": const,
                             "runs": [("".join("+" if v > 0 else "-" for v in COMBOS[i])) for i in DESIGNS[d]]}
    al = pd.DataFrame(rows_alias)
    al.to_csv(RES / "alias_groups.csv", index=False)
    out["alias_count"] = {d: {"main_with_two": int(((al.design == d) & (al.n_main >= 1) & (al.n_two >= 1)).sum()),
                              "two_with_two": int(((al.design == d) & (al.n_two >= 2)).sum())}
                          for d in ["half_D_ABC", "half_D_AB"]}

    # 2) 基本の置き方：A+4・B+3・C+2・D 0・A×B +3（ほかの組は0）。と、C×D が −3 で打ち消す置き方
    worlds = {"basic": {"A": 4, "B": 3, "C": 2, "D": 0, "AB": 3},
              "cancel": {"A": 4, "B": 3, "C": 2, "D": 0, "AB": 3, "CD": -3}}
    rows_basic = []
    show = ["A", "B", "C", "D", "AB", "CD", "AD", "BC"]
    for wname, w in worlds.items():
        eff = np.zeros(15)
        for k, v in w.items():
            eff[TERMS.index(k)] = v
        beta = np.tile(eff / 2, (REPS, 1))
        true16 = BASE_LEVEL + eff / 2 @ X16.T
        best = int(true16.argmax())
        for d in ["full16", "half_D_ABC", "half_D_AB", "half_D_ABC_x2"]:
            est, ch = run_design(beta, d, np.random.default_rng(SEED * 10 + len(rows_basic)), None)
            for t in show:
                j = TERMS.index(t)
                rows_basic.append({"world": wname, "design": d, "term": t, "true_effect": float(eff[j]),
                                   "est_mean": r(est[:, j].mean(), 3), "est_p10": r(np.quantile(est[:, j], 0.1), 3),
                                   "est_p90": r(np.quantile(est[:, j], 0.9), 3),
                                   "judged_effective_share": r((np.abs(est[:, j]) >= THRESH).mean()),
                                   "best_hit": r(((true16[best] - true16[ch]) < 1e-9).mean()),
                                   "shortfall_mean": r((true16[best] - true16[ch]).mean(), 3)})
    bs = pd.DataFrame(rows_basic)
    bs.to_csv(RES / "basic_estimates.csv", index=False)
    out["basic"] = {}
    for wname in worlds:
        out["basic"][wname] = {"true": worlds[wname], "best_combo_true_score": r((BASE_LEVEL + np.array([worlds[wname].get(t, 0) for t in TERMS]) / 2 @ X16.T).max(), 2)}
        for d in ["full16", "half_D_ABC", "half_D_AB", "half_D_ABC_x2"]:
            sub = bs[(bs.world == wname) & (bs.design == d)].set_index("term")
            out["basic"][wname][d] = {"est_mean": sub.est_mean.to_dict(), "judged_effective": sub.judged_effective_share.to_dict(),
                                      "best_hit": float(sub.best_hit.iloc[0]), "shortfall_mean": float(sub.shortfall_mean.iloc[0])}
    # ばらつきだけで、見積もりが本当の値から2点以上ずれる割合（式どおり：見積もりの標準偏差は 2×ばらつき÷√枚数）
    from math import erf, sqrt
    def p_off(n):
        se = 2 * NOISE / sqrt(n)
        return r(1 - erf(THRESH / se / sqrt(2)))
    out["formula_noise_only_off_2pt"] = {"16枚": p_off(16), "8枚": p_off(8)}

    # 3) でたらめに置いた世界（2,000個）：いちばん良い組を当てる割合・条件の効き目の見誤り
    rng_w = np.random.default_rng(SEED + 1)
    beta = random_world(rng_w, WORLDS, **BASE_RAND)
    out["random_base"] = summarize_world(beta, rng_w)

    # 4) 確かめ：2つの組の効き目の出やすさ・大きさを変えた12通り
    grid = []
    for p in GRID_P:
        for s in GRID_S:
            rg = np.random.default_rng(SEED * 100 + int(p * 100) + int(s * 10))
            b = random_world(rg, WORLDS, BASE_RAND["main_sd"], p, s)
            res = summarize_world(b, rg)
            for d, v in res.items():
                grid.append({"p_int": p, "int_sd": s, "design": d, **v})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    out["grid_ranges"] = {d: {"best_hit_min": r(g[g.design == d].best_hit.min()), "best_hit_max": r(g[g.design == d].best_hit.max()),
                              "main_off_min": r(g[g.design == d].main_off_2pt_share.min()),
                              "main_off_max": r(g[g.design == d].main_off_2pt_share.max()),
                              "shortfall_min": r(g[g.design == d].shortfall_mean.min(), 3),
                              "shortfall_max": r(g[g.design == d].shortfall_mean.max(), 3)}
                          for d in g.design.unique()}
    piv = g.pivot_table(index=["p_int", "int_sd"], columns="design", values="best_hit")
    out["grid_counts"] = {"ABC_beats_AB_best_hit": int((piv["half_D_ABC"] > piv["half_D_AB"]).sum()),
                          "settings": int(len(piv)),
                          "x2_beats_full16_best_hit": int((piv["half_D_ABC_x2"] > piv["full16"]).sum()),
                          "x2_minus_half_ABC_best_hit_max": r((piv["half_D_ABC_x2"] - piv["half_D_ABC"]).max()),
                          "full_minus_half_ABC_best_hit_min": r((piv["full16"] - piv["half_D_ABC"]).min()),
                          "full_minus_half_ABC_best_hit_max": r((piv["full16"] - piv["half_D_ABC"]).max())}

    # data：基本の置き方で1回試したときの板ごとの記録
    rng_d = np.random.default_rng(SEED + 7)
    eff = np.zeros(15)
    for k, v in worlds["basic"].items():
        eff[TERMS.index(k)] = v
    recs = []
    for d in ["full16", "half_D_ABC", "half_D_AB"]:
        for i in DESIGNS[d]:
            yt = BASE_LEVEL + eff / 2 @ X16[i]
            recs.append({"design": d, "A": COMBOS[i, 0], "B": COMBOS[i, 1], "C": COMBOS[i, 2], "D": COMBOS[i, 3],
                         "true_score": r(yt, 2), "observed_score": r(yt + rng_d.normal(0, NOISE), 2)})
    pd.DataFrame(recs).to_csv(DATA / "boards_basic.csv", index=False)
    pd.DataFrame(2 * beta[:200], columns=TERMS).round(3).to_csv(DATA / "random_worlds_first200.csv", index_label="world")

    json.dump(out, open(RES / "a1107_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：重なる効き目の地図
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.2))
    for ax, d, ttl in [(axes[0], "half_D_ABC", "D＝A×B×C の8通り"), (axes[1], "half_D_AB", "D＝A×B の8通り")]:
        groups, _ = alias_groups(DESIGNS[d])
        show_terms = [t for t in TERMS if len(t) <= 2]
        mat = np.zeros((len(show_terms), len(groups)))
        labels = []
        for j, gr in enumerate(groups):
            names = [t.lstrip("-") for t in gr]
            labels.append("／".join(sorted([n for n in names if len(n) <= 2], key=lambda s: (len(s), s))) or "（3つ以上の組）")
            for t in names:
                if t in show_terms:
                    mat[show_terms.index(t), j] = 1 if len(t) == 1 else 2
        ax.imshow(np.where(mat == 0, np.nan, mat), cmap=plt.matplotlib.colors.ListedColormap([BLUE, ORANGE]), vmin=1, vmax=2, aspect="auto")
        ax.set_yticks(range(len(show_terms)))
        ax.set_yticklabels([t if len(t) == 1 else t[0] + "×" + t[1] for t in show_terms])
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels(["\n＝".join(l.replace("A", "A").split("／")) for l in [
            "／".join((t if len(t) == 1 else t[0] + "×" + t[1]) for t in lab.split("／")) for lab in labels]], fontsize=8.5)
        ax.set_xticks(np.arange(-.5, len(groups)), minor=True)
        ax.set_yticks(np.arange(-.5, len(show_terms)), minor=True)
        ax.grid(which="minor", color="#dddddd")
        ax.tick_params(which="minor", length=0)
        ax.set_title(ttl)
        for j in range(len(groups)):
            k = np.where(mat[:, j] > 0)[0]
            if len(k) >= 2:
                ax.plot([j, j], [k.min(), k.max()], color=INK, lw=1.2, zorder=3)
    axes[0].set_ylabel("効き目（1つの条件・2つの組）")
    for ax in axes:
        ax.set_xlabel("見積もりの列（下の名前は、その列に入る効き目）")
    fig.suptitle("半分の8通りで、同じ列に入る効き目（青：1つの条件、橙：2つの組。線でつないだものが重なる）", y=1.0)
    fig.text(0.01, -0.06, "列に入る3つ以上の組の効き目は省いた。同じ列に入る効き目は、見積もりが足し合わさって分けられない", fontsize=8, color=GRAY)
    save(fig, "a1107_alias_map.png", SRC, y=-0.1)

    # 図2：基本の置き方での見積もり（2,000回の平均と10〜90%）
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    terms_plot = ["A", "B", "C", "D", "AB", "CD"]
    cols = {"full16": INK, "half_D_ABC": BLUE, "half_D_AB": ORANGE}
    for ax, wname, ttl in [(axes[0], "basic", "基本：A×B の組だけ +3"), (axes[1], "cancel", "A×B が +3、C×D が −3")]:
        for k, d in enumerate(["full16", "half_D_ABC", "half_D_AB"]):
            sub = bs[(bs.world == wname) & (bs.design == d)].set_index("term").loc[terms_plot]
            x = np.arange(len(terms_plot)) + (k - 1) * 0.22
            ax.errorbar(x, sub.est_mean, yerr=[sub.est_mean - sub.est_p10, sub.est_p90 - sub.est_mean], fmt="o", color=cols[d],
                        ms=5, capsize=2, label=DESIGN_JA[d])
        tr = bs[(bs.world == wname) & (bs.design == "full16")].set_index("term").loc[terms_plot].true_effect
        ax.scatter(np.arange(len(terms_plot)), tr, marker="_", s=500, color=GREEN, zorder=0, label="本当の効き目（置いた値）")
        ax.axhline(0, color=GRAY, lw=0.8)
        ax.set_xticks(range(len(terms_plot)))
        ax.set_xticklabels([t if len(t) == 1 else t[0] + "×" + t[1] for t in terms_plot])
        ax.set_title(ttl)
    axes[0].set_ylabel("見積もった効き目（点、2,000回の平均と10〜90%）")
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8.5, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.0))
    save(fig, "a1107_estimates.png", SRC, y=-0.07)

    # 図3：確かめ（12通り）：いちばん良い組を当てた割合
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
    for ax, s in zip(axes, GRID_S):
        for d, c in [("full16", INK), ("half_D_ABC_x2", GREEN), ("half_D_ABC", BLUE), ("half_D_AB", ORANGE)]:
            sub = g[(g.int_sd == s) & (g.design == d)]
            ax.plot(sub.p_int, sub.best_hit * 100, "o-", color=c, label=DESIGN_JA[d])
        ax.set_title(f"組の効き目の散らばり {s:g}点")
        ax.set_xlabel("2つの組に効き目がある確率")
        ax.set_ylim(0, 100)
        ax.set_xticks(GRID_P)
    axes[0].set_ylabel("いちばん良い組み合わせを当てた割合（%）")
    fig.suptitle("でたらめに置いた2,000個の世界で、いちばん良い組み合わせを当てた割合（12通り）", y=1.02)
    axes[0].legend(fontsize=8, loc="lower left", frameon=False)
    save(fig, "a1107_robust.png", SRC, y=-0.05)

    out_print = {k: out[k] for k in ["alias_count", "formula_noise_only_off_2pt", "random_base", "grid_ranges", "grid_counts"]}
    print(json.dumps(out_print, ensure_ascii=False, indent=1))
    print("basic", json.dumps(out["basic"], ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
