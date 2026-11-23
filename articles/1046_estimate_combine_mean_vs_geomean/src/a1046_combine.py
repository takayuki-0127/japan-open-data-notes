"""1046 何人かの概算をまとめるとき、普通の平均と掛け算の平均（幾何平均）のどちらが当たりに近いのか？（架空のデータ）

架空の問い（「A町で1年に売れる傘の本数」のような件数）に、5人がそれぞれ概算を出す。正しい件数は作成者が置く。
1人の概算＝正しい件数 ×（みんなに共通の思い込みのずれ）×（その人だけのずれ）。
ずれの形を3通り（対数で上下に同じだけ／足し算で上下に同じだけ／対数＋ときどき桁を間違える）に置き、
普通の平均・幾何平均・中央値でまとめた値が正しい件数にどれだけ近いかを比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1046
SRC = "架空の概算（作成者が乱数で作成、seed 1046）"
BASE = {"model": "対数", "sigma": 0.7, "k": 5, "tau": 0.3}
N_GROUP = 40_000
N_GROUP_GRID = 20_000
P_DIGIT = 0.08
MODELS = ["対数", "足し算", "対数＋桁違い"]
METHODS = ["普通の平均", "幾何平均", "中央値"]


def r(x, k=4):
    return round(float(x), k)


def estimates(rng, n, k, model, sigma, tau):
    """正しい件数を1としたときの、n組×k人の概算"""
    if model == "足し算":
        b = rng.normal(0, tau, (n, 1))
        e = rng.normal(0, sigma, (n, k))
        return np.maximum(1 + b + e, 0.05)
    b = rng.normal(0, tau, (n, 1))
    e = rng.normal(0, sigma, (n, k))
    x = np.exp(b + e)
    if model == "対数＋桁違い":
        hit = rng.random((n, k)) < P_DIGIT
        x = np.where(hit, x * np.where(rng.random((n, k)) < 0.5, 10.0, 0.1), x)
    return x


def combine(x):
    return {"普通の平均": x.mean(1), "幾何平均": np.exp(np.log(x).mean(1)), "中央値": np.median(x, 1)}


def score(v):
    lv = np.abs(np.log(v))
    return {"within15": float((lv <= np.log(1.5)).mean()), "within2": float((lv <= np.log(2)).mean()),
            "median_times_off": float(np.exp(np.median(lv))), "median_value": float(np.median(v)),
            "mean_value": float(v.mean()), "median_abs_diff": float(np.median(np.abs(v - 1))),
            "mean_abs_diff": float(np.abs(v - 1).mean())}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    x = estimates(rng, N_GROUP, BASE["k"], BASE["model"], BASE["sigma"], BASE["tau"])
    true_n = np.round(np.exp(rng.uniform(np.log(1_000), np.log(1_000_000), N_GROUP)))
    dfx = pd.DataFrame(np.round(x[:2000] * true_n[:2000, None]), columns=[f"person{i+1}" for i in range(BASE["k"])])
    dfx.insert(0, "true_count", true_n[:2000].astype(int)); dfx.insert(0, "group", np.arange(1, 2001))
    dfx.to_csv(DATA / "groups_base.csv", index=False, float_format="%.0f")
    c = combine(x)
    base = {m: score(c[m]) for m in METHODS}
    base["1人"] = score(x[:, 0])
    pd.DataFrame(base).T.round(4).to_csv(RES / "base_methods.csv", index_label="method")

    # ずれの形ごと（ほかは基本）
    by_model = {}
    for i, md in enumerate(MODELS):
        if md == BASE["model"]:
            cc = c
        else:
            xx = estimates(np.random.default_rng(SEED * 10 + i), N_GROUP, BASE["k"], md, 0.5 if md == "足し算" else BASE["sigma"], BASE["tau"])
            cc = combine(xx)
        by_model[md] = {m: {kk: r(vv) for kk, vv in score(cc[m]).items()} for m in METHODS}

    # 人数を変えると（基本のずれの形）
    by_k = []
    for k in [1, 2, 3, 5, 10, 30, 100]:
        if k == BASE["k"]:
            cc = c
        elif k == 1:
            cc = combine(x[:, :1])
        else:
            cc = combine(estimates(np.random.default_rng(SEED * 20 + k), N_GROUP, k, BASE["model"], BASE["sigma"], BASE["tau"]))
        row = {"k": k}
        for m in ["普通の平均", "幾何平均"]:
            s = score(cc[m])
            row[f"{m}_within15_pct"] = r(s["within15"] * 100, 2)
            row[f"{m}_median_value"] = r(s["median_value"], 3)
        by_k.append(row)
    by_k = pd.DataFrame(by_k)
    by_k.to_csv(RES / "by_people.csv", index=False)
    # 共通の思い込みのずれだけのときの上限（人数が無限）
    ceiling_tau = float((np.abs(np.random.default_rng(SEED * 30).normal(0, BASE["tau"], 1_000_000)) <= np.log(1.5)).mean())

    # 27通り：sigma の大きさ（足し算は 0.2・0.4・0.6）× 人数 × ずれの形
    rows = []
    gi = 0
    for md in MODELS:
        for lvl, sg in enumerate([0.3, 0.7, 1.2]):
            sgu = [0.2, 0.4, 0.6][lvl] if md == "足し算" else sg
            for k in [3, 5, 10]:
                xx = estimates(np.random.default_rng(SEED * 100 + gi), N_GROUP_GRID, k, md, sgu, BASE["tau"])
                cc = combine(xx)
                sc = {m: score(cc[m]) for m in METHODS}
                rows.append({"model": md, "spread_level": lvl + 1, "sigma": sgu, "k": k,
                             **{f"{m}_within15_pct": r(sc[m]["within15"] * 100, 2) for m in METHODS},
                             **{f"{m}_median_abs_diff": r(sc[m]["median_abs_diff"], 4) for m in METHODS},
                             **{f"{m}_median_value": r(sc[m]["median_value"], 3) for m in METHODS},
                             "best_by_ratio": max(METHODS, key=lambda m: sc[m]["within15"]),
                             "best_by_diff": min(METHODS, key=lambda m: sc[m]["median_abs_diff"]),
                             "gm_minus_am_pt": r((sc["幾何平均"]["within15"] - sc["普通の平均"]["within15"]) * 100, 2)})
                gi += 1
    g = pd.DataFrame(rows)
    g.to_csv(RES / "grid.csv", index=False)

    b = {m: base[m] for m in METHODS}
    pct = lambda v: r(v * 100, 2)
    gm_am = g.gm_minus_am_pt
    out = {
        "headline": {
            "am_within15_pct": pct(b["普通の平均"]["within15"]), "gm_within15_pct": pct(b["幾何平均"]["within15"]),
            "md_within15_pct": pct(b["中央値"]["within15"]), "one_within15_pct": pct(base["1人"]["within15"]),
            "am_within2_pct": pct(b["普通の平均"]["within2"]), "gm_within2_pct": pct(b["幾何平均"]["within2"]),
            "md_within2_pct": pct(b["中央値"]["within2"]), "one_within2_pct": pct(base["1人"]["within2"]),
            "am_median_value": r(b["普通の平均"]["median_value"], 2), "gm_median_value": r(b["幾何平均"]["median_value"], 2),
            "md_median_value": r(b["中央値"]["median_value"], 2),
            "am_times_off": r(b["普通の平均"]["median_times_off"], 2), "gm_times_off": r(b["幾何平均"]["median_times_off"], 2),
            "md_times_off": r(b["中央値"]["median_times_off"], 2), "one_times_off": r(base["1人"]["median_times_off"], 2),
            "one_median_abs_diff": r(base["1人"]["median_abs_diff"], 3),
            "gm_minus_am_base_pt": r((b["幾何平均"]["within15"] - b["普通の平均"]["within15"]) * 100, 2),
            "am_median_abs_diff": r(b["普通の平均"]["median_abs_diff"], 3), "gm_median_abs_diff": r(b["幾何平均"]["median_abs_diff"], 3),
            "am_mean_abs_diff": r(b["普通の平均"]["mean_abs_diff"], 3), "gm_mean_abs_diff": r(b["幾何平均"]["mean_abs_diff"], 3),
            "am_mean_value": r(b["普通の平均"]["mean_value"], 3), "gm_mean_value": r(b["幾何平均"]["mean_value"], 3),
            "add_am_within15_pct": r(by_model["足し算"]["普通の平均"]["within15"] * 100, 2),
            "add_gm_within15_pct": r(by_model["足し算"]["幾何平均"]["within15"] * 100, 2),
            "add_md_within15_pct": r(by_model["足し算"]["中央値"]["within15"] * 100, 2),
            "add_am_median_value": r(by_model["足し算"]["普通の平均"]["median_value"], 2),
            "add_gm_median_value": r(by_model["足し算"]["幾何平均"]["median_value"], 2),
            "digit_am_within15_pct": r(by_model["対数＋桁違い"]["普通の平均"]["within15"] * 100, 2),
            "digit_gm_within15_pct": r(by_model["対数＋桁違い"]["幾何平均"]["within15"] * 100, 2),
            "digit_md_within15_pct": r(by_model["対数＋桁違い"]["中央値"]["within15"] * 100, 2),
            "digit_am_median_value": r(by_model["対数＋桁違い"]["普通の平均"]["median_value"], 2),
            "ceiling_common_bias_within15_pct": pct(ceiling_tau),
            "grid_gm_beats_am_n": int((gm_am > 0).sum()),
            "grid_log_gm_beats_am_n": int((g[g.model == "対数"].gm_minus_am_pt > 0).sum()),
            "grid_add_gm_beats_am_n": int((g[g.model == "足し算"].gm_minus_am_pt > 0).sum()),
            "grid_digit_gm_beats_am_n": int((g[g.model == "対数＋桁違い"].gm_minus_am_pt > 0).sum()),
            "grid_log_gap_min_pt": r(g[g.model == "対数"].gm_minus_am_pt.min(), 2),
            "grid_log_gap_max_pt": r(g[g.model == "対数"].gm_minus_am_pt.max(), 2),
            "grid_add_gap_min_pt": r(g[g.model == "足し算"].gm_minus_am_pt.min(), 2),
            "grid_add_gap_max_pt": r(g[g.model == "足し算"].gm_minus_am_pt.max(), 2),
            "grid_digit_gap_min_pt": r(g[g.model == "対数＋桁違い"].gm_minus_am_pt.min(), 2),
            "grid_digit_gap_max_pt": r(g[g.model == "対数＋桁違い"].gm_minus_am_pt.max(), 2),
            "grid_best_ratio_counts": g.best_by_ratio.value_counts().to_dict(),
            "grid_best_diff_counts": g.best_by_diff.value_counts().to_dict(),
            "grid_digit_md_best_n": int((g[g.model == "対数＋桁違い"].best_by_ratio == "中央値").sum()),
            "grid_digit_md_beats_gm_n": int((g[g.model == "対数＋桁違い"]["中央値_within15_pct"] > g[g.model == "対数＋桁違い"]["幾何平均_within15_pct"]).sum()),
            "grid_best_ratio_differs_from_diff_n": int((g.best_by_ratio != g.best_by_diff).sum()),
        },
        "formula": {"lognormal_am_bias": r(np.exp(BASE["sigma"] ** 2 / 2), 3),
                    "lognormal_am_bias_k5_median_approx_note": "人数が多いと普通の平均は exp(σ²/2) 倍に近づく",
                    "am_median_value_k100": r(by_k[by_k.k == 100]["普通の平均_median_value"].iloc[0], 3),
                    "within15_log": r(np.log(1.5), 4)},
        "by_model": by_model,
        "by_people": by_k.to_dict("records"),
        "base_methods": {m: {kk: r(vv) for kk, vv in s.items()} for m, s in base.items()},
        "constants": {**BASE, "within_ratio": 1.5, "within_lower": r(1 / 1.5, 2), "true_count_min": 1_000, "true_count_max": 1_000_000,
                      "data_rows": 2000, "sigma_additive_base": 0.5, "p_digit_error": P_DIGIT, "digit_factor": 10, "n_group": N_GROUP, "n_group_grid": N_GROUP_GRID},
        "grid_n": int(len(g)),
    }
    json.dump(out, open(RES / "a1046_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：まとめた値の分布（基本）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.exp(np.linspace(np.log(0.2), np.log(6), 70))
    ax.hist(c["普通の平均"], bins=bins, color=ORANGE, alpha=.55, label="普通の平均")
    ax.hist(c["幾何平均"], bins=bins, color=BLUE, alpha=.55, label="幾何平均")
    ax.set_xscale("log"); ax.set_xticks([0.25, 0.5, 1, 2, 4]); ax.set_xticklabels(["0.25倍", "0.5倍", "1倍", "2倍", "4倍"])
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.axvline(1, color=INK, lw=1)
    ax.axvspan(1 / 1.5, 1.5, color=GRAY, alpha=.12, lw=0)
    ax.text(1.52, ax.get_ylim()[1] * 0.97, "1.5倍以内", color=GRAY, fontsize=8.5)
    ax.set_xlabel("5人の概算をまとめた値 ÷ 正しい件数（対数の目盛り）"); ax.set_ylabel("組の数（40,000組のうち）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"誤差を対数で置くと、普通の平均は上にずれる（中央値{b['普通の平均']['median_value']:.2f}倍）")
    save(fig, "a1046_distribution.png", SRC)

    # 図2：ずれの形ごとの1.5倍以内の割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    w = 0.26
    cols = {"普通の平均": ORANGE, "幾何平均": BLUE, "中央値": GRAY}
    for j, m in enumerate(METHODS):
        vals = [by_model[md][m]["within15"] * 100 for md in MODELS]
        ax.bar(np.arange(3) + (j - 1) * w, vals, width=w, color=cols[m], label=m)
        for i, v in enumerate(vals):
            ax.text(i + (j - 1) * w, v + 1, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_xticks(range(3)); ax.set_xticklabels(["対数で上下に同じ", "足し算で上下に同じ", "対数＋8%が桁違い"])
    ax.set_ylim(0, 100); ax.set_ylabel("正しい件数の1.5倍以内に入った組（%）")
    ax.set_xlabel("1人のずれの形（5人、基本の置き方）")
    ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=3)
    ax.set_title("どちらが当たるかは、ずれの形で入れかわる")
    save(fig, "a1046_by_model.png", SRC)

    # 図3：人数と当たり（基本）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(by_k.k, by_k["普通の平均_within15_pct"], marker="o", color=ORANGE, label="普通の平均")
    ax.plot(by_k.k, by_k["幾何平均_within15_pct"], marker="o", color=BLUE, label="幾何平均")
    ax.axhline(ceiling_tau * 100, color=GRAY, ls="--", lw=1)
    ax.text(1.05, ceiling_tau * 100 + 1.5, f"みんなに共通のずれだけが残ったときの上限 {ceiling_tau*100:.1f}%", color=GRAY, fontsize=8.5)
    ax.set_xscale("log"); ax.set_xticks([1, 2, 3, 5, 10, 30, 100]); ax.set_xticklabels(["1", "2", "3", "5", "10", "30", "100"])
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.set_ylim(0, 100); ax.set_xlabel("概算を出す人数"); ax.set_ylabel("1.5倍以内に入った組（%）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("人数を増やしても、共通の思い込みのずれは消えない")
    save(fig, "a1046_people.png", SRC)
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1)); print(json.dumps(out["formula"], ensure_ascii=False))
    print(by_k); print(pd.DataFrame(base).T.round(3))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
