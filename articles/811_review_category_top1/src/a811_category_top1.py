"""811 カテゴリの1位は、実力か件数の少なさか？（架空のデータ）

架空の店を「カテゴリ」（同じ種類の店の集まり）に分け、カテゴリごとに見かけの星の平均で1位を決める。
店ごとに「本当の満足度」を置き、1位の店がカテゴリで本当にいちばん良い店かを数える。
店の作り方（本当の満足度・件数・1件の星）は 801 と同じ。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 811
SRC = "架空の店と口コミ（作成者が乱数で作成、seed 811）"
STARS = np.arange(1, 6)
SIZES = [10, 30, 100, 300]          # カテゴリの店の数
RULES = [("件数の条件なし", 1), ("10件以上の店だけ", 10), ("30件以上の店だけ", 30)]
REPS = 2000                         # カテゴリを作り直す回数（大きさごと）


def star_probs(mu):
    """平均が mu になる1〜5の分布（801 と同じ）"""
    m = mu.copy()
    for _ in range(30):
        w = np.exp(-0.5 * ((STARS[None, :] - m[:, None]) / 0.9) ** 2)
        p = w / w.sum(1, keepdims=True)
        m = m + (mu - (p * STARS).sum(1))
    return p


def true_sat(rng, n, spread, clip=False):
    """本当の満足度：平均3.9の正規分布。2.5〜4.8の外は引き直す（801 の「切る」と違い、4.8の同点を作らない）"""
    x = rng.normal(3.9, spread, n)
    if clip:  # 確かめ用：801 と同じ「切る」置き方
        return np.clip(x, 2.5, 4.8)
    bad = (x < 2.5) | (x > 4.8)
    while bad.any():
        x[bad] = rng.normal(3.9, spread, bad.sum())
        bad = (x < 2.5) | (x > 4.8)
    return x


def make_shops(rng, n, spread=0.35, nmax=1000, clip=False):
    true = true_sat(rng, n, spread, clip)
    n_rev = np.round(np.exp(rng.uniform(0, np.log(nmax), n))).astype(int)
    cnt = rng.multinomial(n_rev, star_probs(true))
    obs = (cnt * STARS).sum(1) / n_rev
    return true, n_rev, obs


def top1_stats(rng, size, reps, spread=0.35, nmax=1000, clip=False):
    """大きさ size のカテゴリを reps 個作り、ルールごとに1位の店を調べる"""
    true, n, obs = make_shops(rng, size * reps, spread, nmax, clip)
    true, n, obs = true.reshape(reps, size), n.reshape(reps, size), obs.reshape(reps, size)
    tmax = true.max(1)
    # 本当の順位：自分より本当の満足度が高い店の数＋1
    rank_true = (true[:, None, :] > true[:, :, None]).sum(2) + 1
    out = {}
    for name, th in RULES:
        o = np.where(n >= th, obs, -np.inf)
        # 同点のときは件数の多い店を上にする
        key = o + n * 1e-10
        top = key.argmax(1)
        ok = np.isfinite(o[np.arange(reps), top])
        r = np.arange(reps)[ok]; t = top[ok]
        elig_max = np.where(n >= th, true, -np.inf).max(1)
        out[name] = {"hit": round(float((rank_true[r, t] == 1).mean()), 3),
                     "true_rank_median": float(np.median(rank_true[r, t])),
                     "top3_share": round(float((rank_true[r, t] <= 3).mean()), 3),
                     "n_median": float(np.median(n[r, t])),
                     "n_le_5_share": round(float((n[r, t] <= 5).mean()), 3),
                     "shown_mean": round(float(obs[r, t].mean()), 3),
                     "true_mean": round(float(true[r, t].mean()), 3),
                     "over": round(float((obs[r, t] - true[r, t]).mean()), 3),
                     "best_excluded": round(float((elig_max < tmax).mean()), 3)}
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 0) 1回分のデータ：大きさの違う30カテゴリ（10〜300軒、対数で一様）
    sizes = np.round(np.exp(rng.uniform(np.log(10), np.log(300), 30))).astype(int)
    rows = []
    for c, s in enumerate(sizes, 1):
        tr, nn, ob = make_shops(rng, s)
        rows.append(pd.DataFrame({"category": f"C{c:02d}", "true": tr, "n": nn, "mean": ob}))
    df = pd.concat(rows, ignore_index=True)
    df.insert(0, "shop_id", np.arange(1, len(df) + 1))
    df.to_csv(DATA / "categories.csv", index=False, float_format="%.4f")
    one = []
    for c, g in df.groupby("category"):
        top = g.sort_values(["mean", "n"], ascending=False).iloc[0]
        one.append({"category": c, "shops": len(g), "top1_n": int(top.n), "top1_mean": round(float(top["mean"]), 3),
                    "top1_true": round(float(top.true), 3), "top1_is_best": bool(top.true == g.true.max()),
                    "best_n": int(g.loc[g.true.idxmax(), "n"]), "best_mean": round(float(g.loc[g.true.idxmax(), "mean"]), 3),
                    "best_true": round(float(g.true.max()), 3)})
    one = pd.DataFrame(one)
    one_sum = {"categories": 30, "shops": int(len(df)), "top1_is_best": int(one.top1_is_best.sum()),
               "top1_n_le_5": int((one.top1_n <= 5).sum()), "top1_shown_5_0": int((one.top1_mean >= 5).sum())}

    # 1) カテゴリの大きさ × ルール（各2000回）
    main_tab = {}
    for s in SIZES:
        main_tab[str(s)] = top1_stats(np.random.default_rng(SEED * 100 + s), s, REPS)
    flat = [{"size": int(s), "rule": r, **v} for s, d in main_tab.items() for r, v in d.items()]
    pd.DataFrame(flat).to_csv(RES / "top1_by_size_rule.csv", index=False)

    # 2) 確かめ：店どうしの差・件数の上限を変える（100軒のカテゴリ）
    robust = {}
    for label, sp, nm in [("基本（差0.35・件数1〜1,000件）", 0.35, 1000), ("店どうしの差0.2", 0.2, 1000),
                          ("店どうしの差0.5", 0.5, 1000), ("件数1〜100件", 0.35, 100)]:
        d = top1_stats(np.random.default_rng(SEED * 7 + int(sp * 100) + nm), 100, REPS, sp, nm)
        robust[label] = {r: {"hit": v["hit"], "top3_share": v["top3_share"], "best_excluded": v["best_excluded"]}
                         for r, v in d.items()}

    # 確かめ：801 と同じく2.5〜4.8の外を「切る」置き方（4.8ちょうどの同点の店は、どれも本当の1位として数える）
    clip_chk = {}
    for size in (100, 300):
        d = top1_stats(np.random.default_rng(SEED * 13 + size), size, REPS, clip=True)
        clip_chk[str(size)] = {r: {"hit": v["hit"], "top3_share": v["top3_share"], "best_excluded": v["best_excluded"]}
                               for r, v in d.items()}
    out = {"one_draw_30_categories": one_sum, "top1_by_size_rule_2000reps": main_tab, "robustness_size100": robust,
           "clip_like_801": clip_chk}
    json.dump(out, open(RES / "a811_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    one.to_csv(RES / "one_draw_top1.csv", index=False)

    # 図1：1位が本当にいちばん良い店だった割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = np.arange(len(SIZES)); w = 0.26
    for i, ((name, _), col) in enumerate(zip(RULES, [GRAY, BLUE, GREEN])):
        v = [main_tab[str(s)][name]["hit"] * 100 for s in SIZES]
        ax.bar(xs + (i - 1) * w, v, w, color=col, label=name)
        for x, y in zip(xs + (i - 1) * w, v):
            ax.text(x, y + 1, f"{np.floor(y + 0.5 + 1e-9):.0f}", ha="center", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels([f"{s}軒" for s in SIZES]); ax.set_xlabel("カテゴリの店の数")
    ax.set_ylabel("1位が本当にいちばん良い店だった割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("店の多いカテゴリほど、星の平均の1位は本当の1位から外れる")
    save(fig, "a811_hit.png", SRC)

    # 図2：1回分の例（1位が本当の1位でなかったカテゴリのうち、いちばん店の多いもの）
    cbig = one[~one.top1_is_best].sort_values("shops").iloc[-1].category
    g = df[df.category == cbig]
    top = g.sort_values(["mean", "n"], ascending=False).iloc[0]; best = g.loc[g.true.idxmax()]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(g.n, g["mean"], s=9, color=BLUE, alpha=.45, lw=0)
    ax.scatter([top.n], [top["mean"]], s=70, color=ORANGE, zorder=3)
    ax.annotate(f"星の平均の1位：{int(top.n)}件で星{top['mean']:.1f}（本当の満足度{top.true:.2f}）",
                (top.n, top["mean"]), xytext=(40, 5.25), textcoords="data", fontsize=9, color=ORANGE,
                arrowprops=dict(arrowstyle="-", color=ORANGE, lw=.8))
    ax.scatter([best.n], [best["mean"]], s=70, color=GREEN, marker="D", zorder=3)
    ax.annotate(f"本当にいちばん良い店：{int(best.n)}件で星{best['mean']:.2f}（本当の満足度{best.true:.2f}）",
                (best.n, best["mean"]), xytext=(20, 2.2), textcoords="data", fontsize=9, color=GREEN,
                arrowprops=dict(arrowstyle="-", color=GREEN, lw=.8))
    ax.set_ylim(1.9, 5.4)
    ax.set_xscale("log"); ax.set_xlabel("口コミの件数（対数の目盛り）"); ax.set_ylabel("見かけの星の平均")
    ax.set_title(f"1回分の例：店{len(g)}軒のカテゴリ（{cbig}）の1位と本当の1位", pad=10)
    save(fig, "a811_example.png", SRC)

    # 図3：1位の店の見かけの平均と本当の満足度
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for name, col, mk in [("件数の条件なし", GRAY, "o"), ("10件以上の店だけ", BLUE, "s")]:
        ax.plot(SIZES, [main_tab[str(s)][name]["shown_mean"] for s in SIZES], color=col, marker=mk, label=f"{name}：見かけの平均")
        ax.plot(SIZES, [main_tab[str(s)][name]["true_mean"] for s in SIZES], color=col, marker=mk, ls="--", mfc="white",
                label=f"{name}：本当の満足度")
    ax.set_xscale("log"); ax.set_xticks(SIZES); ax.set_xticklabels([f"{s}軒" for s in SIZES]); ax.minorticks_off()
    ax.set_xlabel("カテゴリの店の数"); ax.set_ylabel("1位の店の平均（2,000回）"); ax.set_ylim(4.1, 5.25)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left")
    ax.set_title("1位の店の星は、本当の満足度より高く見えている")
    save(fig, "a811_gap.png", SRC)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
