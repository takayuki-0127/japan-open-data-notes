"""1293 荷物の体積の合計を箱1つの容量で割って見込んだ箱の数は、1つずつ詰めた本当の箱の数よりどれだけ少なく出るのか？（架空のデータ）

架空の通販の倉庫。その日に店へまとめて送る品物を、同じ大きさの箱に1つずつ詰める。
品物の体積は箱の容量を1とした比で置く（対数で正規の分布、箱より大きいものは引き直す）。
形は気にせず、体積だけで入るかどうかを決める（縦・横・高さの並べ方は入れていない）。
見込み＝体積の合計÷1の切り上げ。
詰め方①：今の箱に入らなければ、その箱を閉じて新しい箱を開ける（開いている箱は1つ）
詰め方②：開いている箱のどれかに入れば、いちばん先に開けた箱に入れる（箱は閉じない）
すべてシミュレーション。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1293
SRC = "架空の通販の箱詰めのシミュレーション（作成者が乱数で作成、seed 1293）"
TARGET_BOXES = 20          # その日の体積の合計が、平均で箱20個分になるように品物の数を決める
BASE_MEAN, BASE_SIG = 0.1, 0.6
MEANS = [0.02, 0.05, 0.1, 0.2, 0.3]
SIGS = [0.3, 0.6, 1.0]
DAYS_BASE, DAYS_GRID = 2000, 400


def draw(rng, n, mean, sig):
    mu = np.log(mean) - sig ** 2 / 2
    x = rng.lognormal(mu, sig, n)
    bad = x > 1.0
    while bad.any():
        x[bad] = rng.lognormal(mu, sig, bad.sum())
        bad = x > 1.0
    return x


def pack_close(x):
    """① 入らなければ閉じる。箱ごとの中身の合計を返す"""
    loads = []
    cur = 0.0
    for v in x:
        if cur + v > 1.0 + 1e-12:
            loads.append(cur); cur = 0.0
        cur += v
    loads.append(cur)
    return loads


def pack_any(x):
    """② 入る箱のうち、いちばん先に開けた箱へ"""
    rem = np.ones(len(x))
    nb = 0
    for v in x:
        if nb:
            ok = np.nonzero(rem[:nb] >= v - 1e-12)[0]
            if len(ok):
                rem[ok[0]] -= v; continue
        rem[nb] -= v; nb += 1
    return list(1.0 - rem[:nb])


def run(rng, mean, sig, days, keep=False):
    n = int(round(TARGET_BOXES / mean))
    rows = []
    gaps_close = []
    for d in range(days):
        x = draw(rng, n, mean, sig)
        tot = float(x.sum())
        est = int(np.ceil(tot - 1e-9))
        lc = pack_close(x)
        la = pack_any(x)
        rows.append({"day": d, "items": n, "volume_sum": tot, "estimate_boxes": est,
                     "boxes_close": len(lc), "boxes_any": len(la),
                     "gap_sum_closed": float(sum(1.0 - l for l in lc[:-1]))})
        if keep:
            # ①で閉じた箱のすきまと、閉じさせた「次の品物」の大きさ
            gaps_close.extend([1.0 - l for l in lc[:-1]])
    df = pd.DataFrame(rows)
    return df, (np.array(gaps_close) if keep else None)


def summ(df):
    e = df.estimate_boxes
    out = {"items": int(df["items"].iloc[0]),
           "mean_estimate": df.estimate_boxes.mean(),
           "mean_close": df.boxes_close.mean(), "mean_any": df.boxes_any.mean(),
           "extra_close_mean": (df.boxes_close - e).mean(), "extra_any_mean": (df.boxes_any - e).mean(),
           "est_short_close_pct": (1 - (e / df.boxes_close).mean()) * 100,
           "est_short_any_pct": (1 - (e / df.boxes_any).mean()) * 100,
           "share_days_close_eq_est": (df.boxes_close == e).mean() * 100,
           "share_days_any_eq_est": (df.boxes_any == e).mean() * 100,
           "fill_close_pct": (df.volume_sum / df.boxes_close).mean() * 100,
           "fill_any_pct": (df.volume_sum / df.boxes_any).mean() * 100,
           "item_mean_actual": (df.volume_sum / df["items"]).mean(),
           "gap_sum_closed_mean": df.gap_sum_closed.mean()}
    return out


def r4(d):
    return {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in d.items()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base, gaps = run(rng, BASE_MEAN, BASE_SIG, DAYS_BASE, keep=True)
    base_r = base.copy()
    base_r["volume_sum"] = base_r.volume_sum.round(4)
    base_r["gap_sum_closed"] = base_r.gap_sum_closed.round(4)
    base_r.to_csv(DATA / "days_base.csv", index=False)
    bs = r4(summ(base))
    dist = (base.boxes_close - base.estimate_boxes).value_counts(normalize=True).sort_index() * 100
    dist_a = (base.boxes_any - base.estimate_boxes).value_counts(normalize=True).sort_index() * 100
    ext = pd.DataFrame({"extra_boxes": sorted(set(dist.index) | set(dist_a.index))})
    ext["share_close_pct"] = ext.extra_boxes.map(dist).fillna(0).round(2)
    ext["share_any_pct"] = ext.extra_boxes.map(dist_a).fillna(0).round(2)
    ext.to_csv(RES / "base_extra_dist.csv", index=False)
    bs["gap_close_mean"] = round(float(gaps.mean()), 4)
    bs["gap_close_median"] = round(float(np.median(gaps)), 4)

    grid = []
    for m in MEANS:
        for s in SIGS:
            df, g = run(rng, m, s, DAYS_GRID, keep=True)
            r = summ(df)
            r.update({"item_mean": m, "item_sigma": s, "gap_close_mean": float(g.mean())})
            grid.append(r)
    grid = pd.DataFrame(grid)
    cols = ["item_mean", "item_sigma", "items", "mean_estimate", "mean_close", "mean_any", "extra_close_mean",
            "extra_any_mean", "est_short_close_pct", "est_short_any_pct", "fill_close_pct", "fill_any_pct",
            "share_days_close_eq_est", "share_days_any_eq_est", "gap_close_mean", "gap_sum_closed_mean", "item_mean_actual"]
    grid = grid[cols].round(4)
    for c in ["est_short_close_pct", "est_short_any_pct", "fill_close_pct", "fill_any_pct"]:
        grid[c] = grid[c].round(2)
    grid.to_csv(RES / "grid.csv", index=False)

    main_j = {"base": bs, "base_settings": {"item_mean": BASE_MEAN, "item_sigma": BASE_SIG, "days": DAYS_BASE,
                                            "target_boxes": TARGET_BOXES},
              "grid_range": {"est_short_close_pct_min": float(grid.est_short_close_pct.min()),
                             "est_short_close_pct_max": float(grid.est_short_close_pct.max()),
                             "est_short_any_pct_min": float(grid.est_short_any_pct.min()),
                             "est_short_any_pct_max": float(grid.est_short_any_pct.max()),
                             "extra_close_min": float(grid.extra_close_mean.min()),
                             "extra_close_max": float(grid.extra_close_mean.max()),
                             "extra_any_min": float(grid.extra_any_mean.min()),
                             "extra_any_max": float(grid.extra_any_mean.max())}}
    with open(RES / "a1293_main.json", "w", encoding="utf-8") as f:
        json.dump(main_j, f, ensure_ascii=False, indent=1)

    # 図1：基本の置き方での余分な箱の数の分布
    fig, ax = plt.subplots(figsize=(7, 4))
    w = 0.38
    ax.bar(ext.extra_boxes - w / 2, ext.share_close_pct, w, color=BLUE, label="① 入らなければ閉じる")
    ax.bar(ext.extra_boxes + w / 2, ext.share_any_pct, w, color=ORANGE, label="② 入る箱に戻して入れる")
    ax.set_xlabel("本当の箱の数 − 見込み（体積の合計÷容量の切り上げ）")
    ax.set_ylabel("日の割合（%）")
    ax.set_ylim(0, None)
    ax.set_xticks(ext.extra_boxes)
    ax.set_title(f"品物の大きさが平均で箱の{BASE_MEAN:.0%}のとき（{DAYS_BASE:,}日）")
    ax.legend(frameon=False)
    save(fig, "a1293_extra_dist.png", SRC)

    # 図2：品物の大きさの平均ごとの見込みの足りなさ（散らばり0.6）
    g6 = grid[grid.item_sigma == 0.6]
    fig, ax = plt.subplots(figsize=(7, 4))
    xs = np.arange(len(g6))
    ax.bar(xs - w / 2, g6.est_short_close_pct, w, color=BLUE, label="① 入らなければ閉じる")
    ax.bar(xs + w / 2, g6.est_short_any_pct, w, color=ORANGE, label="② 入る箱に戻して入れる")
    for i, (a, b) in enumerate(zip(g6.est_short_close_pct, g6.est_short_any_pct)):
        ax.text(i - w / 2, a, f"{a:.2f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + w / 2, b, f"{b:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs, [f"{m:.0%}" for m in g6.item_mean])
    ax.set_xlabel("品物1つの大きさの平均（箱の容量に対する割合）")
    ax.set_ylabel("見込みが本当より少ない割合（%）")
    ax.set_ylim(0, None)
    ax.set_title("見込みが少なく出る割合（散らばり0.6、各400日）")
    ax.legend(frameon=False)
    save(fig, "a1293_by_item_size.png", SRC)

    # 図3：①で閉じた箱のすきまの分布
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(gaps, bins=np.linspace(0, 0.6, 31), color=LIGHT, edgecolor=BLUE)
    ax.axvline(gaps.mean(), color=INK, lw=1)
    ax.text(gaps.mean(), ax.get_ylim()[1] * 0.92, f" 平均 {round(float(gaps.mean()), 4)}", fontsize=9)
    ax.set_xlabel("閉じた箱に残ったすきま（箱の容量に対する割合）")
    ax.set_ylabel("箱の数")
    ax.set_title("① 入らなければ閉じるときに残るすきま（基本の置き方）")
    save(fig, "a1293_gap_hist.png", SRC)

    print(json.dumps(main_j, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
