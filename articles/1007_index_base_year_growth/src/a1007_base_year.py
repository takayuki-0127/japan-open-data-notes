"""1007 基準の年を変えると、指数の伸びはどう見えるのか？（架空のデータ）

架空の雑貨店チェーンの20店。店ごとの年の来客数を10年分作る（1年目〜10年目）。
店ごとに「本当の伸び」（年あたりの伸び率）を作成者が置き、年ごとの振れを足す。
指数＝その年の来客数÷基準の年の来客数×100。基準の年を変えて、伸びの見え方がどう変わるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1007
SRC = "架空の雑貨店チェーンの来客数（作成者が乱数で作成、seed 1007）"
N_STORE, N_YEAR = 20, 10
BASE = {"noise": 0.06, "g_sd": 0.03, "size_sd": 0.5}
N_CHAIN = 1000
N_SENS = 400
BASES_EARLY = [1, 2, 3, 4, 5]


def make_chain(rng, noise=0.06, g_sd=0.03, size_sd=0.5, **_):
    size = 50000 * np.exp(rng.normal(0, size_sd, N_STORE))
    g = rng.normal(0.03, g_sd, N_STORE)
    t = np.arange(N_YEAR)
    logv = np.log(size)[:, None] + g[:, None] * t[None, :] + rng.normal(0, noise, (N_STORE, N_YEAR))
    return np.round(np.exp(logv)), g


def index(v, b):
    """基準の年 b（1始まり）を100にした指数。b が (a, c) なら a〜c年目の平均を100にする"""
    if isinstance(b, tuple):
        base = v[:, b[0] - 1:b[1]].mean(1)
    else:
        base = v[:, b - 1]
    return v / base[:, None] * 100


def slope(v):
    t = np.arange(N_YEAR); tc = t - t.mean()
    return (np.log(v) * tc).sum(1) / (tc ** 2).sum()


def pair_stats(v, g):
    i, j = np.triu_indices(N_STORE, 1)
    truth = g[i] > g[j]
    ans = {}
    for b in BASES_EARLY:
        I = index(v, b)[:, -1]
        ans[f"base{b}"] = I[i] > I[j]
    I3 = index(v, (1, 3))[:, -1]
    ans["base1_3avg"] = I3[i] > I3[j]
    s = slope(v)
    ans["slope"] = s[i] > s[j]
    early = np.stack([ans[f"base{b}"] for b in BASES_EARLY])
    flip = early.any(0) & (~early).any(0)
    out = {"flip_share": float(flip.mean())}
    for k, a in ans.items():
        out[f"acc_{k}"] = float((a == truth).mean())
    out["acc_base_single_mean"] = float(np.mean([out[f"acc_base{b}"] for b in BASES_EARLY]))
    # 本当の伸びの差の大きさ別（基準の年でどちらが伸びたかが入れかわる割合）
    d = np.abs(g[i] - g[j])
    return out, flip, d


def composite_stats(v):
    """店の指数の平均と、合計の指数。5年目→10年目の伸び（%）を基準の年ごとに"""
    tot = v.sum(0)
    tot_growth = (tot[-1] / tot[4] - 1) * 100
    comp = {}
    for b in range(1, N_YEAR + 1):
        c = index(v, b).mean(0)
        comp[b] = (c[-1] / c[4] - 1) * 100
    vals = np.array(list(comp.values()))
    return tot_growth, comp, float(vals.max() - vals.min())


def main():
    # 例のチェーン
    v, g = make_chain(np.random.default_rng(SEED), **BASE)
    dv = pd.DataFrame(v.astype(int), columns=[f"{t}年目" for t in range(1, N_YEAR + 1)])
    dv.insert(0, "store_id", np.arange(1, N_STORE + 1)); dv.insert(1, "本当の伸び", np.round(g, 4))
    dv.to_csv(DATA / "chain_example.csv", index=False)

    # (1) 1つの店：基準の年で、前年比は変わらず、ポイント差は変わる
    st = int(np.argmax(v[:, 0]))  # いちばん大きい店を例に
    one = []
    for b in range(1, N_YEAR):
        I = index(v[st:st + 1], b)[0]
        one.append({"base_year": b, "index_9": round(float(I[8]), 2), "index_10": round(float(I[9]), 2),
                    "points_9_to_10": round(float(I[9] - I[8]), 2), "pct_9_to_10": round(float((I[9] / I[8] - 1) * 100), 4)})
    one = pd.DataFrame(one); one.to_csv(RES / "example_store_by_base.csv", index=False)

    # (2) 例のチェーンの2店の比べ：基準の年で答えが入れかわる組
    ps, flip, d = pair_stats(v, g)
    i, j = np.triu_indices(N_STORE, 1)
    # 図に使う組：入れかわる組のうち、本当の伸びの差がいちばん大きい組
    k = int(np.argmax(np.where(flip, d, -1)))
    pa, pb = int(i[k]), int(j[k])

    # (3) 1,000チェーンで
    rng = np.random.default_rng(SEED * 10)
    rows, flips, ds, comps = [], [], [], []
    for r in range(N_CHAIN):
        vv, gg = make_chain(rng, **BASE)
        o, f, dd = pair_stats(vv, gg)
        tg, comp, rngw = composite_stats(vv)
        o.update({"total_growth_5_10": tg, "comp_range_5_10": rngw,
                  **{f"comp_growth_5_10_base{b}": comp[b] for b in range(1, N_YEAR + 1)}})
        rows.append(o); flips.append(f); ds.append(dd)
    sims = pd.DataFrame(rows); sims.to_csv(RES / "chains_1000.csv", index=False, float_format="%.4f")
    m = sims.mean()
    flips = np.concatenate(flips); ds = np.concatenate(ds)
    bins = [0, 0.01, 0.02, 0.04, 0.06, 1]
    names = ["1ポイント未満", "1〜2ポイント", "2〜4ポイント", "4〜6ポイント", "6ポイント以上"]
    cut = pd.cut(ds, bins, right=False, labels=names)
    by_d = pd.DataFrame({"diff": cut, "flip": flips}).groupby("diff", observed=True).agg(
        pairs=("flip", "size"), flip_share=("flip", "mean")).reset_index().round(4)
    by_d.to_csv(RES / "flip_by_true_diff.csv", index=False)
    acc = {k: round(float(m[f"acc_{k}"]), 4) for k in [f"base{b}" for b in BASES_EARLY] + ["base1_3avg", "slope"]}
    acc["base_single_mean"] = round(float(m.acc_base_single_mean), 4)
    comp_mean = {b: round(float(m[f"comp_growth_5_10_base{b}"]), 3) for b in range(1, N_YEAR + 1)}

    # 確かめ（各400チェーン）
    sens = []
    grid = [("年ごとの振れ", "noise", [0.03, 0.06, 0.12]), ("店ごとの本当の伸びの差", "g_sd", [0.01, 0.03, 0.05]),
            ("店の大きさの差", "size_sd", [0.2, 0.5, 1.0])]
    kk = 0
    for label, key, vals in grid:
        for val in vals:
            kw = dict(BASE); kw[key] = val; kk += 1
            rr = np.random.default_rng(SEED * 100 + kk)
            rs = []
            for _ in range(N_SENS):
                vv, gg = make_chain(rr, **kw)
                o, _, _ = pair_stats(vv, gg)
                tg, comp, rngw = composite_stats(vv)
                o.update({"comp_range_5_10": rngw, "comp_minus_total_base1": comp[1] - tg})
                rs.append(o)
            q = pd.DataFrame(rs).mean()
            sens.append({"changed": label, "value": val, "flip_share": round(float(q.flip_share), 4),
                         "acc_base1": round(float(q.acc_base1), 4), "acc_base1_3avg": round(float(q.acc_base1_3avg), 4),
                         "acc_slope": round(float(q.acc_slope), 4), "comp_range_5_10": round(float(q.comp_range_5_10), 3),
                         "comp_minus_total_base1": round(float(q.comp_minus_total_base1), 3)})
    sens = pd.DataFrame(sens); sens.to_csv(RES / "robustness.csv", index=False)

    ex_tg, ex_comp, ex_rng = composite_stats(v)
    out = {"example_store": {"store_id": st + 1, "pct_9_to_10_all_bases": sorted(set(one.pct_9_to_10.tolist())),
                             "points_9_to_10_min": float(one.points_9_to_10.min()), "points_9_to_10_max": float(one.points_9_to_10.max()),
                             "index_10_min": float(one.index_10.min()), "index_10_max": float(one.index_10.max())},
           "example_chain": {"flip_share": round(ps["flip_share"], 4), "n_pairs": int(len(i)), "n_flip": int(flip.sum()),
                             "pair_for_figure": [pa + 1, pb + 1], "pair_true_growth": [round(float(g[pa]), 4), round(float(g[pb]), 4)],
                             "pair_index10_by_base": {b: [round(float(index(v, b)[pa, -1]), 2), round(float(index(v, b)[pb, -1]), 2)] for b in BASES_EARLY},
                             "total_growth_5_10": round(float(ex_tg), 3),
                             "comp_growth_5_10_by_base": {b: round(float(c), 3) for b, c in ex_comp.items()},
                             "comp_range_5_10": round(ex_rng, 3),
                             "total_index_growth_5_10_by_base_distinct": sorted({round(float((t[-1] / t[4] - 1) * 100), 6) for t in
                                                                                 [v.sum(0) / v.sum(0)[b - 1] * 100 for b in range(1, N_YEAR + 1)]})},
           "chains_1000": {"flip_share": round(float(m.flip_share), 4), "accuracy": acc,
                           "total_growth_5_10_mean": round(float(m.total_growth_5_10), 3),
                           "comp_growth_5_10_mean_by_base": comp_mean,
                           "comp_range_5_10_mean": round(float(m.comp_range_5_10), 3)},
           "flip_by_true_diff": by_d.to_dict("records"),
           "robustness_ranges": {c: [float(sens[c].min()), float(sens[c].max())] for c in
                                 ["flip_share", "acc_base1", "acc_base1_3avg", "comp_range_5_10"]},
           "settings": {**BASE, "n_store": N_STORE, "n_year": N_YEAR, "true_growth_mean": 0.03}}
    json.dump(out, open(RES / "a1007_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の2店、基準の年を変えた指数
    yrs = np.arange(1, N_YEAR + 1)
    b_hi = max(BASES_EARLY, key=lambda b: index(v, b)[pa, -1] - index(v, b)[pb, -1])
    b_lo = min(BASES_EARLY, key=lambda b: index(v, b)[pa, -1] - index(v, b)[pb, -1])
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9), sharey=True)
    for ax, b in zip(axes, [b_hi, b_lo]):
        I = index(v, b)
        ax.plot(yrs, I[pa], "-o", color=BLUE, ms=3.5, label=f"店{pa + 1}（本当の伸び 年{g[pa] * 100:.1f}%）")
        ax.plot(yrs, I[pb], "-o", color=ORANGE, ms=3.5, label=f"店{pb + 1}（本当の伸び 年{g[pb] * 100:.1f}%）")
        ax.axvline(b, color=GRAY, lw=0.8, ls=":"); ax.axhline(100, color=GRAY, lw=0.6)
        ax.set_title(f"{b}年目を100にすると", fontsize=11)
        ax.set_xlabel("年目"); ax.set_xticks(yrs)
        off = 0 if abs(I[pa, -1] - I[pb, -1]) >= 5 else 2.5
        sa = 1 if I[pa, -1] >= I[pb, -1] else -1
        ax.text(N_YEAR + 0.25, I[pa, -1] + sa * off, f"{I[pa, -1]:.0f}", color=BLUE, fontsize=8.5, va="center")
        ax.text(N_YEAR + 0.25, I[pb, -1] - sa * off, f"{I[pb, -1]:.0f}", color=ORANGE, fontsize=8.5, va="center")
    axes[0].set_ylabel("来客数の指数")
    h, l = axes[0].get_legend_handles_labels()
    fig.suptitle("同じ2店の来客数でも、基準の年しだいで「よく伸びた店」が入れかわる（例）", fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.legend(h, l, frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 0.93))
    save(fig, "a1007_two_stores.png", SRC)

    # 図2：どちらが伸びたかの当たり（1,000チェーンの平均）
    labs = [f"{b}年目を100" for b in BASES_EARLY] + ["1〜3年目の平均を100", "10年分の傾き"]
    vals = [acc[f"base{b}"] for b in BASES_EARLY] + [acc["base1_3avg"], acc["slope"]]
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    yy = np.arange(len(labs))[::-1]
    ax.barh(yy, np.array(vals) * 100, color=[LIGHT] * 5 + [BLUE, GREEN], height=0.65)
    for y, val in zip(yy, vals):
        ax.text(val * 100 + 0.5, y, f"{val * 100:.1f}%", va="center", fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels(labs)
    ax.set_xlim(0, 100); ax.set_xlabel("10年目の指数で比べた答えが、本当の伸びの大小と合った2店の組（%）")
    ax.set_title("基準の年が後ろほど当たりが下がり、10年分の傾きがいちばん当たる（1,000チェーン）")
    save(fig, "a1007_accuracy.png", SRC)

    # 図3：店の指数の平均と合計の指数（5年目→10年目の伸び）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    bb = np.arange(1, N_YEAR + 1)
    ax.plot(bb, [comp_mean[b] for b in bb], "-o", color=ORANGE, label="店の指数の平均（1,000チェーンの平均）")
    ax.axhline(float(m.total_growth_5_10), color=BLUE, lw=1.5, label="合計の指数（基準の年によらない）")
    ax.plot(bb, [ex_comp[b] for b in bb], "--o", color=ORANGE, alpha=.5, ms=3, label="店の指数の平均（例のチェーン）")
    ax.axhline(ex_tg, color=BLUE, lw=1, ls="--", alpha=.5, label="合計の指数（例のチェーン）")
    ax.set_xticks(bb); ax.set_xlabel("基準の年（その年を100にする）")
    ax.set_ylabel("5年目→10年目の伸び（%）")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    ax.set_title("店の指数を平均すると、基準の年で伸びが変わる", pad=40)
    save(fig, "a1007_composite.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
