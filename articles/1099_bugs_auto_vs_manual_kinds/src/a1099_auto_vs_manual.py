"""1099 自動テストで見つかるバグと、人が触って見つかるバグは、同じ種類なのか？（架空のデータ）

架空のアプリのリリース前のバグ（種類ごとの件数）を乱数で作り、種類ごとに
自動テストで見つかる確率と、人が触って見つかる確率を作成者が置く。
自動テストを先に流し、そのあと人が触る。記録では、両方で見つかったバグは先に見つけた自動テストに数える。
自動テストの分と人が新しく見つけた分の種類の割合がどれだけずれるか、
同じ種類を同じ割合で見つけると置いても、先に見つけた側に数えるだけでどれだけずれるか、
2つの見つけ方の重なりから全体のバグの数を見積もるとどれだけ外れるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1099
SRC = "架空のアプリのリリース前のバグ（作成者が置いた確率からの乱数、seed 1099）"
KINDS = ["計算のまちがい", "境目の値", "操作の順番", "画面の崩れ", "文言のまちがい", "動きの遅さ"]
MEAN_N = np.array([50, 40, 40, 30, 20, 20], float)          # 種類ごとのバグの数（平均、合計200）
P_AUTO = np.array([0.70, 0.50, 0.25, 0.10, 0.05, 0.15])     # 自動テストで見つかる確率
P_MAN = np.array([0.30, 0.20, 0.40, 0.60, 0.50, 0.35])      # 人が触って見つかる確率
REPS = 2000
GRID_REPS = 500


def r(x, d=4):
    return round(float(x), d)


def mix_gap(a, b):
    """2つの種類の割合の、差の絶対値の合計の半分（0〜1）"""
    a = a / a.sum(-1, keepdims=True)
    b = b / b.sum(-1, keepdims=True)
    return 0.5 * np.abs(a - b).sum(-1)


def man_profile(w):
    """人の見つけ方を、自動テストと同じ形（全体の件数はそろえる）に w だけ寄せる"""
    s = (MEAN_N * P_MAN).sum() / (MEAN_N * P_AUTO).sum()
    return np.clip((1 - w) * P_MAN + w * s * P_AUTO, 0, 1)


def sim(rng, reps, p_auto, p_man, scale=1.0, auto_first=True):
    n = rng.poisson(MEAN_N * scale, (reps, len(KINDS)))
    both = rng.binomial(n, p_auto * p_man)                       # 両方で見つかる
    only_a = rng.binomial(n - both, p_auto * (1 - p_man) / (1 - p_auto * p_man))
    only_m = rng.binomial(n - both - only_a, (1 - p_auto) * p_man / (1 - p_auto * p_man - p_auto * (1 - p_man)))
    a_all, m_all = both + only_a, both + only_m
    if auto_first:
        a_rec, m_rec = a_all, only_m          # 両方の分は先の自動テストに数える
    else:
        a_rec, m_rec = only_a, m_all          # 人が先なら、両方の分は人に数える
    return {"n": n, "both": both, "a_all": a_all, "m_all": m_all, "a_rec": a_rec, "m_rec": m_rec}


def estimates(d):
    na, nm, nb, n = d["a_all"].sum(1), d["m_all"].sum(1), d["both"].sum(1), d["n"].sum(1)
    pooled = (na + 1) * (nm + 1) / (nb + 1) - 1           # 重なりから全体を見積もる（1を足して0割りを避ける形）
    strat = ((d["a_all"] + 1) * (d["m_all"] + 1) / (d["both"] + 1) - 1).sum(1)  # 種類ごとに見積もって足す
    found = (d["a_all"] + d["m_all"] - d["both"]).sum(1)
    return {"pooled_ratio": pooled / n, "strat_ratio": strat / n, "found_share": found / n}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 主な結果：基本の置き方
    d = sim(rng, REPS, P_AUTO, P_MAN)
    tot = {k: d[k].sum(0) for k in ["n", "both", "a_all", "m_all", "a_rec", "m_rec"]}
    mix = pd.DataFrame({"kind": KINDS, "p_auto": P_AUTO, "p_man": P_MAN, "mean_n": MEAN_N,
                        "share_true": tot["n"] / tot["n"].sum(), "share_auto": tot["a_rec"] / tot["a_rec"].sum(),
                        "share_man_new": tot["m_rec"] / tot["m_rec"].sum(), "share_man_all": tot["m_all"] / tot["m_all"].sum(),
                        "share_found_any": (tot["a_all"] + tot["m_all"] - tot["both"]) / (tot["a_all"] + tot["m_all"] - tot["both"]).sum(),
                        "left_share_of_kind": 1 - (tot["a_all"] + tot["m_all"] - tot["both"]) / tot["n"],
                        "formula_left": (1 - P_AUTO) * (1 - P_MAN)})
    for c in mix.columns[1:]:
        mix[c] = mix[c].round(4)
    mix.to_csv(RES / "kind_mix.csv", index=False)

    gap_new = mix_gap(d["a_rec"].astype(float), d["m_rec"].astype(float))
    gap_all = mix_gap(d["a_rec"].astype(float), d["m_all"].astype(float))
    est = estimates(d)
    base = {"auto_per_release": r(d["a_rec"].sum(1).mean(), 2), "man_new_per_release": r(d["m_rec"].sum(1).mean(), 2),
            "man_all_per_release": r(d["m_all"].sum(1).mean(), 2), "both_per_release": r(d["both"].sum(1).mean(), 2),
            "bugs_per_release": r(d["n"].sum(1).mean(), 2),
            "gap_auto_vs_man_new": r(np.median(gap_new)), "gap_auto_vs_man_all": r(np.median(gap_all)),
            "gap_auto_vs_man_new_p10_p90": [r(np.percentile(gap_new, 10)), r(np.percentile(gap_new, 90))],
            "pooled_ratio_median": r(np.median(est["pooled_ratio"])), "pooled_ratio_p10_p90": [r(np.percentile(est["pooled_ratio"], 10)), r(np.percentile(est["pooled_ratio"], 90))],
            "strat_ratio_median": r(np.median(est["strat_ratio"])), "strat_ratio_p10_p90": [r(np.percentile(est["strat_ratio"], 10)), r(np.percentile(est["strat_ratio"], 90))],
            "found_share_mean": r(est["found_share"].mean()),
            "formula_found_share": r(1 - (MEAN_N * (1 - P_AUTO) * (1 - P_MAN)).sum() / MEAN_N.sum()),
            "formula_pooled_ratio": r((MEAN_N * P_AUTO).sum() * (MEAN_N * P_MAN).sum() / (MEAN_N * P_AUTO * P_MAN).sum() / MEAN_N.sum()),
            "formula_gap_new": r(mix_gap(MEAN_N * P_AUTO, MEAN_N * (1 - P_AUTO) * P_MAN)),
            "formula_gap_all": r(mix_gap(MEAN_N * P_AUTO, MEAN_N * P_MAN)),
            "corr_p_auto_p_man": r(np.corrcoef(P_AUTO, P_MAN)[0, 1])}

    # 同じ形の見つけ方（w=1）：先に見つけた側に数えるだけで、どれだけずれるか
    p1 = man_profile(1.0)
    d1 = sim(rng, REPS, P_AUTO, p1)
    e1 = estimates(d1)
    same = {"p_man_same": [r(x) for x in p1],
            "gap_auto_vs_man_new": r(np.median(mix_gap(d1["a_rec"].astype(float), d1["m_rec"].astype(float)))),
            "gap_auto_vs_man_all": r(np.median(mix_gap(d1["a_rec"].astype(float), d1["m_all"].astype(float)))),
            "formula_gap_new": r(mix_gap(MEAN_N * P_AUTO, MEAN_N * (1 - P_AUTO) * p1)),
            "pooled_ratio_median": r(np.median(e1["pooled_ratio"])), "strat_ratio_median": r(np.median(e1["strat_ratio"])),
            "formula_pooled_ratio": r((MEAN_N * P_AUTO).sum() * (MEAN_N * p1).sum() / (MEAN_N * P_AUTO * p1).sum() / MEAN_N.sum()),
            "share_man_new": [r(x) for x in d1["m_rec"].sum(0) / d1["m_rec"].sum()],
            "share_man_all": [r(x) for x in d1["m_all"].sum(0) / d1["m_all"].sum()],
            "share_auto": [r(x) for x in d1["a_rec"].sum(0) / d1["a_rec"].sum()]}

    # 確かめ：人の見つけ方を自動テストの形に寄せる度合い w × バグの数 × どちらが先か（30通り、各500回）
    grid_rows = []
    for w in [0.0, 0.25, 0.5, 0.75, 1.0]:
        pm = man_profile(w)
        for scale in [0.5, 1.0, 2.0]:
            for af in [True, False]:
                g = sim(rng, GRID_REPS, P_AUTO, pm, scale, af)
                e = estimates(g)
                first = g["a_rec"] if af else g["m_rec"]
                second = g["m_rec"] if af else g["a_rec"]
                grid_rows.append({"w": w, "bugs_mean": int(MEAN_N.sum() * scale), "first": "auto" if af else "manual",
                                  "corr_profiles": r(np.corrcoef(P_AUTO, pm)[0, 1]),
                                  "gap_first_vs_second_new": r(np.median(mix_gap(first.astype(float), second.astype(float)))),
                                  "gap_auto_all_vs_man_all": r(np.median(mix_gap(g["a_all"].astype(float), g["m_all"].astype(float)))),
                                  "pooled_ratio": r(np.median(e["pooled_ratio"])), "strat_ratio": r(np.median(e["strat_ratio"])),
                                  "found_share": r(e["found_share"].mean())})
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # data：1回目のリリースの、種類ごとの件数
    one = pd.DataFrame({"kind": KINDS, "bugs": d["n"][0], "found_auto": d["a_all"][0], "found_manual": d["m_all"][0],
                        "found_both": d["both"][0], "recorded_auto": d["a_rec"][0], "recorded_manual_new": d["m_rec"][0]})
    one["left"] = one.bugs - one.found_auto - one.found_manual + one.found_both
    one.to_csv(DATA / "bugs_one_release.csv", index=False)
    chk = {"one_gap_new": r(mix_gap(one.recorded_auto.values.astype(float), one.recorded_manual_new.values.astype(float))), "sim_rep0": r(gap_new[0])}

    gw = grid.groupby("w")
    out = {"settings": {"kinds": KINDS, "mean_n": MEAN_N.tolist(), "p_auto": P_AUTO.tolist(), "p_man": P_MAN.tolist(), "reps": REPS, "grid_reps": GRID_REPS},
           "base": base, "kind_mix": mix.to_dict(orient="records"), "same_profile": same,
           "grid": grid.to_dict(orient="records"),
           "grid_gap_new_by_w": {str(k): [r(v.gap_first_vs_second_new.min()), r(v.gap_first_vs_second_new.max())] for k, v in gw},
           "grid_gap_all_by_w": {str(k): [r(v.gap_auto_all_vs_man_all.min()), r(v.gap_auto_all_vs_man_all.max())] for k, v in gw},
           "grid_pooled_by_w": {str(k): [r(v.pooled_ratio.min()), r(v.pooled_ratio.max())] for k, v in gw},
           "grid_strat_by_w": {str(k): [r(v.strat_ratio.min()), r(v.strat_ratio.max())] for k, v in gw},
           "grid_strat_closer_than_pooled": int((abs(grid.strat_ratio - 1) < abs(grid.pooled_ratio - 1)).sum()),
           "grid_gap_new_gt_gap_all": int((grid.gap_first_vs_second_new > grid.gap_auto_all_vs_man_all).sum()),
           "data_check": chk}
    json.dump(out, open(RES / "a1099_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：種類の割合
    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    x = np.arange(len(KINDS)); wd = 0.2
    sets = [("share_true", INK, "作成者が置いたバグ全体"), ("share_auto", BLUE, "自動テストの記録"),
            ("share_man_new", ORANGE, "人が新しく見つけた記録"), ("share_man_all", LIGHT, "人が触って見つけた全部（重なりも）")]
    for j, (c, col, lab) in enumerate(sets):
        v = mix[c].values * 100
        ax.bar(x + (j - 1.5) * wd, v, wd, color=col, label=lab)
    ax.set_xticks(x); ax.set_xticklabels(KINDS, fontsize=9.5)
    ax.set_ylim(0, 60); ax.set_ylabel("種類の割合（%、2,000回を合わせた）")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper right")
    ax.set_title(f"自動テストの記録と人が新しく見つけた記録では、種類の割合がずれる（ずれの中央値 {base['gap_auto_vs_man_new'] * 100:.2f}%）", fontsize=11)
    save(fig, "a1099_mix.png", SRC, y=-0.03)

    # 図2：人の見つけ方を自動テストの形に寄せたときの、種類の割合のずれ（自動が先、バグ200件）
    sub = grid[(grid["bugs_mean"] == 200) & (grid["first"] == "auto")]
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    x = np.arange(len(sub)); wd = 0.36
    ax.bar(x - wd / 2, sub.gap_first_vs_second_new * 100, wd, color=ORANGE, label="記録どうし（重なりは自動テストに数える）")
    ax.bar(x + wd / 2, sub.gap_auto_all_vs_man_all * 100, wd, color=LIGHT, label="見つけた全部どうし（重なりも両方に数える）")
    for xx, a, b in zip(x, sub.gap_first_vs_second_new * 100, sub.gap_auto_all_vs_man_all * 100):
        ax.text(xx - wd / 2, a + 0.8, f"{a:.2f}", ha="center", fontsize=8.5)
        ax.text(xx + wd / 2, b + 0.8, f"{b:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"w={w}" + ("\n（基本）" if w == 0 else "\n（同じ形）" if w == 1 else "") for w in sub.w], fontsize=9)
    ax.set_xlabel("人の見つけ方を自動テストと同じ形に寄せた度合い")
    ax.set_ylim(0, 72); ax.set_ylabel("種類の割合のずれ（%、500回の中央値）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("同じ形で見つけると置いても、重なりを先の側に数えると、記録の種類はずれる", fontsize=11.5)
    save(fig, "a1099_same.png", SRC, y=-0.08)

    # 図3：重なりから見積もった全体の数÷置いた数
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    ax.bar(x - wd / 2, sub.pooled_ratio, wd, color=BLUE, label="まとめて見積もる")
    ax.bar(x + wd / 2, sub.strat_ratio, wd, color=GREEN, label="種類ごとに見積もって足す")
    for xx, a, b in zip(x, sub.pooled_ratio, sub.strat_ratio):
        ax.text(xx - wd / 2, a + 0.02, f"{a:g}", ha="center", fontsize=8.5)
        ax.text(xx + wd / 2, b + 0.02, f"{b:g}", ha="center", fontsize=8.5)
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([f"w={w}" + ("\n（基本）" if w == 0 else "\n（同じ形）" if w == 1 else "") for w in sub.w], fontsize=9)
    ax.set_xlabel("人の見つけ方を自動テストと同じ形に寄せた度合い")
    ax.set_ylim(0, 1.5); ax.set_ylabel("見積もり÷置いたバグの数（500回の中央値）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=2)
    ax.set_title("2つの見つけ方の重なりから全体を見積もると、見つけ方の形しだいで上にも下にも外れる", fontsize=11)
    save(fig, "a1099_estimate.png", SRC, y=-0.08)

    print(mix.to_string()); print(json.dumps({"base": base, "same": same}, ensure_ascii=False, indent=1)); print(grid.to_string())
    print(json.dumps({k: out[k] for k in out if k.startswith("grid_") or k == "data_check"}, ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
