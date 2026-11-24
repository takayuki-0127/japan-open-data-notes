"""1234 付け手ごとの甘さ・辛さのくせは、見本の件でどこまで直せるのか？（架空のデータ）

架空の製品の写真に見立てた件。件ごとに「傷の目立ち具合」s を置き、s が境目 C を超える件を本当の「傷あり」とする。
写真は10のロットに分かれ、ロットごとに1人の付け手が300件に「傷あり／傷なし」を付ける。
付け手は s に見誤り e を足した値を見て、境目 C に自分のくせ t を足した線を超えたら「傷あり」と付ける
（t が正なら甘い＝傷ありと付けにくい、負なら辛い＝付けやすい）。
答えの分かっている見本の件を付け手ごとに判定させ、見逃しと付けすぎの割合を見積もって、ロットの「傷あり」の割合を直す。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1234
SRC = "架空の製品の写真に見立てた件と付け手（作成者が置いたくせと見誤りからの乱数、seed 1234）"
C = 0.841621          # 標準の山形の分布で上側20%になる境目（件全体の傷ありが20%）
N_BATCH, N_ITEM = 10, 300
LOT_SD = 0.3          # ロットごとの傷の目立ち具合の平均の散らばり
CLEAR = 0.75          # 「はっきりした件」は境目から0.75以上離れた件
GOLD_TYPES = ["でたらめに選ぶ", "傷あり・なし半分ずつ", "はっきりした件だけ（半分ずつ）"]


def draw_gold(rng, kind, g):
    """見本の件の傷の目立ち具合を g 件引く"""
    if kind == GOLD_TYPES[0]:
        return rng.normal(0, 1, g)
    lo_cut, hi_cut = (C, C) if kind == GOLD_TYPES[1] else (C - CLEAR, C + CLEAR)
    pool = rng.normal(0, 1, max(4000, 60 * g))
    pos, neg = pool[pool > hi_cut], pool[pool < lo_cut]
    return np.concatenate([pos[: g // 2], neg[: g - g // 2]])


def one_world(rng, lean_sd, noise, g, kind, with_true=True):
    """10ロット分。返り値：ロットごとの本当の割合・そのままの割合・直した割合・見積もった見逃し/付けすぎ"""
    mu = rng.normal(0, LOT_SD, N_BATCH)
    t = rng.normal(0, lean_sd, N_BATCH)
    s = rng.normal(mu[:, None], 1, (N_BATCH, N_ITEM))
    truth = s > C
    lab = s + rng.normal(0, noise, s.shape) > C + t[:, None]
    true_share, raw = truth.mean(1), lab.mean(1)
    fixed, se_hat, sp_hat, used = raw.copy(), np.full(N_BATCH, np.nan), np.full(N_BATCH, np.nan), np.zeros(N_BATCH, bool)
    for b in range(N_BATCH):
        gs = draw_gold(rng, kind, g)
        gt = gs > C
        gl = gs + rng.normal(0, noise, g) > C + t[b]
        if gt.sum() == 0 or (~gt).sum() == 0:
            continue                       # 傷ありか傷なしが見本に1件もないと直せない（そのまま）
        se, sp = gl[gt].mean(), (~gl[~gt]).mean()
        se_hat[b], sp_hat[b] = se, sp
        fixed[b] = np.clip((raw[b] + sp - 1) / max(se + sp - 1, 0.1), 0, 1)
        used[b] = True
    # 件全体（ロットの平均0）での本当の見逃し・付けすぎ（大きな件数で数える）
    se_true = sp_true = np.full(N_BATCH, np.nan)
    if with_true:
        big = rng.normal(0, 1, 10000)
        bt = big > C
        se_true = np.array([(big[bt] + rng.normal(0, noise, bt.sum()) > C + tb).mean() for tb in t])
        sp_true = np.array([(big[~bt] + rng.normal(0, noise, (~bt).sum()) <= C + tb).mean() for tb in t])
    return dict(true=true_share, raw=raw, fixed=fixed, se_hat=se_hat, sp_hat=sp_hat, used=used,
                se_true=se_true, sp_true=sp_true, t=t, s=s, truth=truth, lab=lab, mu=mu)


def summarize(ws):
    tr = np.concatenate([w["true"] for w in ws]); raw = np.concatenate([w["raw"] for w in ws])
    fx = np.concatenate([w["fixed"] for w in ws]); used = np.concatenate([w["used"] for w in ws])
    rc = lambda a, b: np.mean([pd.Series(x).rank().corr(pd.Series(y).rank()) for x, y in a]) if b else None
    return {"mae_raw": round(float(np.abs(raw - tr).mean()) * 100, 2),
            "mae_fixed": round(float(np.abs(fx - tr).mean()) * 100, 2),
            "bias_raw": round(float((raw - tr).mean()) * 100, 2),
            "bias_fixed": round(float((fx - tr).mean()) * 100, 2),
            "share_fixed_worse": round(float((np.abs(fx - tr) > np.abs(raw - tr)).mean()) * 100, 1),
            "share_fixed_off_10pt": round(float((np.abs(fx - tr) > 0.10).mean()) * 100, 1),
            "share_not_fixable": round(float((~used).mean()) * 100, 1),
            "rankcorr_raw": round(float(rc([(w["raw"], w["true"]) for w in ws], True)), 3),
            "rankcorr_fixed": round(float(rc([(w["fixed"], w["true"]) for w in ws], True)), 3)}


def main():
    t0 = time.time()
    # 1回分のデータ（基本の置き方、見本はでたらめに20件）
    w1 = one_world(np.random.default_rng(SEED), 0.4, 0.4, 20, GOLD_TYPES[0])
    b_idx = np.repeat(np.arange(1, N_BATCH + 1), N_ITEM)
    pd.DataFrame({"lot": b_idx, "item_id": np.arange(1, N_BATCH * N_ITEM + 1), "visibility": w1["s"].ravel().round(4),
                  "true_scratch": w1["truth"].ravel().astype(int), "label": w1["lab"].ravel().astype(int)}
                 ).to_csv(DATA / "items_one_set.csv", index=False)
    lots = pd.DataFrame({"lot": np.arange(1, N_BATCH + 1), "rater_lean": w1["t"].round(2), "lot_mean": w1["mu"].round(4),
                         "true_share": (w1["true"] * 100).round(2), "raw_share": (w1["raw"] * 100).round(2),
                         "fixed_share_gold20_random": (w1["fixed"] * 100).round(2),
                         "se_hat": w1["se_hat"].round(3), "sp_hat": w1["sp_hat"].round(3),
                         "se_true": w1["se_true"].round(3), "sp_true": w1["sp_true"].round(3)})
    lots.to_csv(RES / "lots_one_set.csv", index=False)

    # 1) 基本の置き方（くせの散らばり0.4・見誤り0.4）：見本の選び方 × 見本の件数（各200回）
    rows = []
    for gi, kind in enumerate(GOLD_TYPES):
        for g in [10, 20, 50, 100, 200, 1000]:
            ws = [one_world(np.random.default_rng(SEED * 1000 + gi * 100000 + g * 10 + r), 0.4, 0.4, g, kind) for r in range(200)]
            sm = summarize(ws)
            se_gap = np.concatenate([w["se_hat"] - w["se_true"] for w in ws]); sp_gap = np.concatenate([w["sp_hat"] - w["sp_true"] for w in ws])
            rows.append({"gold_type": kind, "gold_n": g, **sm,
                         "miss_true": round(float(np.mean([1 - w["se_true"] for w in ws])) * 100, 2),
                         "miss_hat": round(float(np.nanmean(np.concatenate([1 - w["se_hat"] for w in ws]))) * 100, 2),
                         "over_true": round(float(np.mean([1 - w["sp_true"] for w in ws])) * 100, 2),
                         "over_hat": round(float(np.nanmean(np.concatenate([1 - w["sp_hat"] for w in ws]))) * 100, 2)})
    base = pd.DataFrame(rows)
    base.to_csv(RES / "base_by_gold.csv", index=False)

    # 2) 確かめ：くせの散らばり × 見誤り × 見本の件数 × 選び方（各30回）
    grid = []
    for li, lean in enumerate([0.0, 0.2, 0.4, 0.8]):
        for ni, noise in enumerate([0.2, 0.4, 0.8]):
            for g in [20, 50, 200]:
                for gi, kind in enumerate(GOLD_TYPES):
                    ws = [one_world(np.random.default_rng(SEED * 31 + li * 1000000 + ni * 100000 + g * 100 + gi * 10 + r * 7919),
                                    lean, noise, g, kind, False) for r in range(30)]
                    grid.append({"lean_sd": lean, "noise": noise, "gold_n": g, "gold_type": kind, **summarize(ws)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    gb = grid[grid.lean_sd > 0]
    def cnt(df, cond):
        return int(cond(df).sum())
    rob = {"n_settings": int(len(grid)), "n_per_type": int(len(grid) / 3),
           "by_type": {}}
    for kind in GOLD_TYPES:
        d = grid[grid.gold_type == kind]
        rob["by_type"][kind] = {
            "n": int(len(d)),
            "n_fixed_better": cnt(d, lambda x: x.mae_fixed < x.mae_raw),
            "mae_raw_range": [float(d.mae_raw.min()), float(d.mae_raw.max())],
            "mae_fixed_range": [float(d.mae_fixed.min()), float(d.mae_fixed.max())],
            "ratio_fixed_raw_range": [round(float((d.mae_fixed / d.mae_raw).min()), 3), round(float((d.mae_fixed / d.mae_raw).max()), 3)]}
    for kind in GOLD_TYPES:
        for g in [20, 50, 200]:
            d = grid[(grid.gold_type == kind) & (grid.gold_n == g)]
            rob["by_type"][kind][f"n_fixed_better_g{g}"] = cnt(d, lambda x: x.mae_fixed < x.mae_raw)
    rob["n_better_by_type_lean"] = {kind: {str(l): cnt(grid[(grid.gold_type == kind) & (grid.lean_sd == l)], lambda x: x.mae_fixed < x.mae_raw)
                                           for l in [0.0, 0.2, 0.4, 0.8]} for kind in GOLD_TYPES}
    rob["ratio_range_by_type_lean"] = {kind: {str(l): [round(float(v.min()), 3), round(float(v.max()), 3)] for l in [0.0, 0.2, 0.4, 0.8]
                                              for v in [(lambda d: d.mae_fixed / d.mae_raw)(grid[(grid.gold_type == kind) & (grid.lean_sd == l)])]}
                                       for kind in GOLD_TYPES}
    dl = grid[(grid.gold_type == GOLD_TYPES[1]) & (grid.lean_sd == 0.8)]
    rob["half_lean08_ratio_range"] = [round(float((dl.mae_fixed / dl.mae_raw).min()), 3), round(float((dl.mae_fixed / dl.mae_raw).max()), 3)]
    dz = grid[(grid.gold_type == GOLD_TYPES[1]) & (grid.lean_sd == 0.0)]
    rob["half_lean0_n_fixed_better"] = cnt(dz, lambda x: x.mae_fixed < x.mae_raw); rob["half_lean0_n"] = int(len(dz))
    rob["half_lean0_bias_raw_range"] = [float(dz.bias_raw.min()), float(dz.bias_raw.max())]

    out = {"base_by_gold_200reps": base.to_dict("records"), "base_mae_raw_mean_18rows": round(float(base.mae_raw.mean()), 2), "robust": rob, "one_set_lots": lots.to_dict("records"),
           "setting": {"lot_n": N_BATCH, "items_per_lot": N_ITEM, "true_share_overall": 20, "lot_sd": LOT_SD,
                       "lean_sd_base": 0.4, "noise_base": 0.4, "clear_margin": CLEAR}}
    json.dump(out, open(RES / "a1234_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の10ロット（見本でたらめ20件）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    o = lots.sort_values("rater_lean").reset_index(drop=True)
    xs = np.arange(len(o))
    ax.scatter(xs, o.true_share, color=INK, s=34, label="本当の傷ありの割合", zorder=3)
    ax.scatter(xs, o.raw_share, color=ORANGE, s=30, marker="s", label="付けたまま", zorder=3)
    ax.scatter(xs, o.fixed_share_gold20_random, color=BLUE, s=30, marker="^", label="見本20件（でたらめに選ぶ）で直した", zorder=3)
    for xx, a_, b_ in zip(xs, o.true_share, o.raw_share):
        ax.plot([xx, xx], [a_, b_], color=ORANGE, lw=1, alpha=.6)
    ax.set_xticks(xs); ax.set_xticklabels([f"{v:+g}" for v in o.rater_lean], fontsize=8.5)
    ax.set_xlabel("付け手のくせ（置いた値。左ほど辛い＝傷ありと付けやすい、右ほど甘い）")
    ax.set_ylabel("ロットの傷ありの割合（%）"); ax.set_ylim(0, max(60, float(o[["raw_share", "fixed_share_gold20_random"]].max().max()) + 5))
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("1回分の10ロット：辛い付け手のロットほど、傷ありが多く付く", fontsize=11)
    save(fig, "a1234_one_set.png", SRC)

    # 図2：見本の件数と外れ（3つの選び方）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = [ORANGE, BLUE, GREEN]
    for kind, c in zip(GOLD_TYPES, cols):
        d = base[base.gold_type == kind]
        ax.plot(range(len(d)), d.mae_fixed, color=c, marker="o", label=f"見本で直す：{kind}")
    raw_mean = float(base.mae_raw.mean())
    ax.axhline(raw_mean, color=GRAY, ls="--", lw=1.2)
    ax.text(5.05, raw_mean + 0.25, f"付けたまま {raw_mean:.2f}", color=GRAY, fontsize=8.5, va="bottom")
    ax.set_xticks(range(6)); ax.set_xticklabels(["10", "20", "50", "100", "200", "1000"])
    ax.set_xlim(-0.3, 5.9)
    ax.set_xlabel("付け手1人あたりの見本の件数"); ax.set_ylabel("ロットの傷ありの割合の外れ（ポイント、平均）")
    ax.set_ylim(0, float(base.mae_fixed.max()) * 1.12)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("見本をはっきりした件だけから選ぶと、件数を増やしても外れは7ポイント台から下がらない", fontsize=10.5)
    save(fig, "a1234_by_gold_n.png", SRC + "。各200回、くせの散らばり0.4・見誤り0.4")

    # 図3：見本で見えた見逃しと、件全体での本当の見逃し（見本50件）
    d = base[base.gold_n == 50].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    xs = np.arange(len(d)); w_ = 0.2
    bars = [("miss_true", "件全体での本当の見逃し", INK), ("miss_hat", "見本で見えた見逃し", BLUE),
            ("over_true", "件全体での本当の付けすぎ", GRAY), ("over_hat", "見本で見えた付けすぎ", LIGHT)]
    for j, (col, lab, c) in enumerate(bars):
        ax.bar(xs + (j - 1.5) * w_, d[col], w_, color=c, label=lab)
        for xx, v in zip(xs, d[col]):
            ax.text(xx + (j - 1.5) * w_, v + 0.5, f"{v:.2f}", ha="center", fontsize=6.5)
    ax.set_xticks(xs); ax.set_xticklabels(d.gold_type, fontsize=9)
    ax.set_ylabel("割合（%、200回×10人の平均）"); ax.set_ylim(0, float(d[[b[0] for b in bars]].max().max()) * 1.25)
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    ax.set_title("はっきりした件だけの見本では、見逃しも付けすぎも小さく見える（見本50件）", fontsize=10.5)
    save(fig, "a1234_seen_vs_true.png", SRC + "\n見逃し＝本当の傷ありを傷なしと付けた割合、付けすぎ＝本当の傷なしを傷ありと付けた割合")
    print(base.to_string()); print(json.dumps(rob, ensure_ascii=False, indent=1)); print(lots.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
