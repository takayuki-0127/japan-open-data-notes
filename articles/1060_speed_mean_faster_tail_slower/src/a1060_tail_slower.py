"""1060 平均が速くなっても、遅い側の数%は遅くなっていることはあるのか？（架空のデータ）

架空のアプリの応答時間（ミリ秒）。軽い処理（95%）と重い処理（5%）がまざる。
変更（よく使う結果を手元に置いておく仕組み）を入れると、軽い処理の多くは速くなるが、
置き場にない軽い処理と重い処理は少し遅くなる、と作成者が置いた。応答時間は置いた分布からの乱数で、実機の計測はしていない。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1060
SRC = "架空のアプリの応答時間（作成者が置いた分布からの乱数、seed 1060）"
BASE = {"heavy_share": 0.05, "hit": 0.80, "miss_slow": 0.05, "heavy_slow": 0.20}
N_BIG = 2_000_000
QS = [0.5, 0.9, 0.95, 0.99, 0.999]
QNAME = {0.5: "中央値", 0.9: "90%点", 0.95: "95%点", 0.99: "99%点", 0.999: "99.9%点"}


def draw(rng, n, after, heavy_share=0.05, hit=0.80, miss_slow=0.05, heavy_slow=0.20):
    """n 件の応答時間（ms）と種類（0軽い・1重い・2軽いで置き場にあった）"""
    heavy = rng.random(n) < heavy_share
    base = np.where(heavy, 300 * np.exp(rng.normal(0, 0.5, n)), 60 * np.exp(rng.normal(0, 0.4, n)))
    kind = heavy.astype(int)
    if not after:
        return base, kind
    hitm = (~heavy) & (rng.random(n) < hit)
    ms = np.where(heavy, base * (1 + heavy_slow), base * (1 + miss_slow))
    ms = np.where(hitm, 15 * np.exp(rng.normal(0, 0.3, n)), ms)
    kind = np.where(hitm, 2, kind)
    return ms, kind


def stats(x):
    d = {"平均": float(x.mean())}
    d.update({QNAME[q]: float(v) for q, v in zip(QS, np.quantile(x, QS))})
    return d


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    b, kb = draw(rng, N_BIG, False, **BASE)
    a, ka = draw(rng, N_BIG, True, **BASE)
    sb, sa = stats(b), stats(a)
    tab = pd.DataFrame({"before_ms": sb, "after_ms": sa})
    tab["change_pct"] = 100 * (tab.after_ms / tab.before_ms - 1)
    tab = tab.round(3)
    tab.index.name = "measure"
    tab.to_csv(RES / "before_after.csv")

    # 遅い側の処理は何でできているか（変更後の99%点を超えた処理の種類）
    over_a = a > sa["99%点"]
    over_b = b > sb["99%点"]
    heavy_in_top1_after = float((ka[over_a] == 1).mean())
    heavy_in_top1_before = float((kb[over_b] == 1).mean())

    # 1件ごとの変化の割合（式どおり）：遅くなる処理＝重い処理＋置き場になかった軽い処理
    slower_share_formula = BASE["heavy_share"] + (1 - BASE["heavy_share"]) * (1 - BASE["hit"])

    # パーセンタイルごとの変化（1〜99.9）
    ps = np.r_[np.arange(1, 100), 99.5, 99.9]
    qb, qa = np.percentile(b, ps), np.percentile(a, ps)
    curve = pd.DataFrame({"percentile": ps, "before_ms": qb.round(3), "after_ms": qa.round(3),
                          "change_pct": (100 * (qa / qb - 1)).round(3)})
    curve.to_csv(RES / "percentile_curve.csv", index=False)
    slower_from = float(curve[curve.change_pct > 0].percentile.min())
    p99_formula_heavy = 100 * BASE["heavy_slow"]   # 99%点がほぼ重い処理だけなら、変化は重い処理の遅くなり方の写し

    # 2,000件ずつ（と200件ずつ）測って比べたとき：平均で速く見え、99%点で遅く見えた回
    tests = {}
    for n in (200, 2000):
        rr = []
        for rep in range(1000):
            g = np.random.default_rng(SEED * 1000 + rep + n)
            x, _ = draw(g, n, False, **BASE)
            y, _ = draw(g, n, True, **BASE)
            rr.append((y.mean() < x.mean(), np.quantile(y, .99) > np.quantile(x, .99),
                       np.median(y) < np.median(x)))
        rr = np.array(rr)
        tests[n] = {"mean_faster_pct": r(100 * rr[:, 0].mean(), 2), "p99_slower_pct": r(100 * rr[:, 1].mean(), 2),
                    "p99_missed_pct": r(100 - 100 * rr[:, 1].mean(), 2),
                    "mean_faster_and_p99_slower_pct": r(100 * (rr[:, 0] & rr[:, 1]).mean(), 2),
                    "median_faster_pct": r(100 * rr[:, 2].mean(), 2)}

    # 置き方を変えた27通り：重い処理の割合 × 置き場にある割合 × 重い処理の遅くなり方（置き場にない軽い処理は+5%のまま）
    grows = []
    i = 0
    for hs in (0.02, 0.05, 0.10):
        for hit in (0.5, 0.8, 0.95):
            for hsl in (0.0, 0.10, 0.20):
                g = np.random.default_rng(SEED * 7 + i); i += 1
                kw = {"heavy_share": hs, "hit": hit, "miss_slow": 0.05, "heavy_slow": hsl}
                x, _ = draw(g, 400_000, False, **kw)
                y, _ = draw(g, 400_000, True, **kw)
                sx, sy = stats(x), stats(y)
                row = {"heavy_share": hs, "hit": hit, "heavy_slow": hsl}
                for k in sx:
                    row[f"chg_{k}"] = r(100 * (sy[k] / sx[k] - 1), 2)
                cq = 100 * (np.percentile(y, ps) / np.percentile(x, ps) - 1)
                row["slower_from_percentile"] = float(ps[cq > 1].min()) if (cq > 1).any() else None
                grows.append(row)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    g_mean_faster = grid["chg_平均"] < 0
    g_p99_slower = grid["chg_99%点"] > 1
    g_p999_slower = grid["chg_99.9%点"] > 1

    # data：変更の前後それぞれ2万件
    n_d = 20000
    pd.DataFrame({"request_id": np.arange(1, 2 * n_d + 1), "period": ["before"] * n_d + ["after"] * n_d,
                  "kind": np.r_[kb[:n_d], ka[:n_d]], "ms": np.round(np.r_[b[:n_d], a[:n_d]], 2)}
                 ).to_csv(DATA / "requests_before_after.csv", index=False)

    head = {
        "mean_before": r(sb["平均"], 2), "mean_after": r(sa["平均"], 2),
        "mean_chg_pct": r(tab.loc["平均", "change_pct"], 2),
        "median_chg_pct": r(tab.loc["中央値", "change_pct"], 2),
        "p90_chg_pct": r(tab.loc["90%点", "change_pct"], 2),
        "p95_chg_pct": r(tab.loc["95%点", "change_pct"], 2),
        "p99_before": r(sb["99%点"], 2), "p99_after": r(sa["99%点"], 2),
        "p99_chg_pct": r(tab.loc["99%点", "change_pct"], 2),
        "p999_chg_pct": r(tab.loc["99.9%点", "change_pct"], 2),
        "slower_from_percentile": slower_from,
        "p99_chg_if_copy_of_heavy_pct": r(p99_formula_heavy, 2),
        "slower_share_formula_pct": r(100 * slower_share_formula, 2),
        "heavy_in_top1pct_before_pct": r(100 * heavy_in_top1_before, 2),
        "heavy_in_top1pct_after_pct": r(100 * heavy_in_top1_after, 2),
        "tests": tests,
        "grid_mean_faster_count": int(g_mean_faster.sum()),
        "grid_p99_slower_count": int(g_p99_slower.sum()),
        "grid_mean_faster_and_p99_slower_count": int((g_mean_faster & g_p99_slower).sum()),
        "grid_mean_faster_and_p999_slower_count": int((g_mean_faster & g_p999_slower).sum()),
        "grid_mean_chg_min": r(grid["chg_平均"].min(), 2), "grid_mean_chg_max": r(grid["chg_平均"].max(), 2),
        "grid_p99_chg_min": r(grid["chg_99%点"].min(), 2), "grid_p99_chg_max": r(grid["chg_99%点"].max(), 2),
        "grid_p99_chg_heavy0_min": r(grid[grid.heavy_slow == 0]["chg_99%点"].min(), 2),
        "grid_p99_chg_heavy0_max": r(grid[grid.heavy_slow == 0]["chg_99%点"].max(), 2),
        "grid_p99_chg_heavy20_min": r(grid[grid.heavy_slow == 0.2]["chg_99%点"].min(), 2),
        "grid_p99_chg_heavy20_max": r(grid[grid.heavy_slow == 0.2]["chg_99%点"].max(), 2),
        "grid_p99_chg_heavy10_min": r(grid[grid.heavy_slow == 0.1]["chg_99%点"].min(), 2),
        "grid_p99_chg_heavy10_max": r(grid[grid.heavy_slow == 0.1]["chg_99%点"].max(), 2),
        "grid_slower_from_min": r(grid[grid.heavy_slow > 0].slower_from_percentile.min(), 1),
        "grid_slower_from_max": r(grid[grid.heavy_slow > 0].slower_from_percentile.max(), 1),
        "grid_heavy0_any_slower_1pct_count": int(grid[grid.heavy_slow == 0].slower_from_percentile.notna().sum()),
    }
    head["run_sec"] = r(time.time() - t0, 1)
    out = {"headline": {k: v for k, v in head.items() if k != "run_sec"}, "set": BASE,
           "before_after": tab.reset_index().to_dict("records")}
    json.dump(out, open(RES / "a1060_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：パーセンタイルごとの変化
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(curve.percentile, curve.change_pct, color=BLUE, lw=2)
    ax.axhline(0, color=INK, lw=1)
    ax.axhline(tab.loc["平均", "change_pct"], color=ORANGE, lw=1, ls="--")
    ax.text(2, tab.loc["平均", "change_pct"] + 2, f"平均の変化 {tab.loc['平均', 'change_pct']:.1f}%", color=ORANGE, fontsize=9)
    ax.fill_between(curve.percentile, 0, curve.change_pct, where=curve.change_pct > 0, color=ORANGE, alpha=.25)
    ax.set_xlabel("パーセンタイル（速い順に並べて何%の位置か）"); ax.set_ylabel("変更の前と比べた変化（%）")
    ax.set_xlim(0, 100)
    ax.set_title(f"速い側は大きく速くなり、{slower_from:.0f}%点より遅い側は遅くなった")
    save(fig, "a1060_curve.png", SRC)

    # 図2：物差しごとの変化（棒、0から）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    names = list(tab.index)
    vals = tab.change_pct.values
    ax.barh(names[::-1], vals[::-1], color=[ORANGE if v > 0 else BLUE for v in vals[::-1]])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + (1.5 if v > 0 else -1.5), i, f"{v:+.1f}%", va="center", ha="left" if v > 0 else "right", fontsize=9)
    ax.axvline(0, color=INK, lw=1)
    ax.set_xlim(min(vals) * 1.3, max(vals) * 1.6)
    ax.set_xlabel("変更の前と比べた変化（%、各200万件。マイナスが速くなった）")
    ax.set_title("平均と中央値は速くなり、99%点と99.9%点は遅くなった")
    save(fig, "a1060_measures.png", SRC)

    # 図3：27通りの平均の変化と99%点の変化
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for hsl, c, mk in zip((0.0, 0.10, 0.20), (LIGHT, BLUE, ORANGE), ("o", "s", "^")):
        gg = grid[grid.heavy_slow == hsl]
        ax.scatter(gg["chg_平均"], gg["chg_99%点"], color=c, marker=mk, s=45, label=f"重い処理の遅くなり +{hsl*100:.0f}%")
    ax.axhline(0, color=INK, lw=1); ax.axvline(0, color=INK, lw=1)
    ax.set_xlabel("平均の変化（%）"); ax.set_ylabel("99%点の変化（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    ax.set_title("置き方27通り：平均はどれも速くなり、99%点は重い処理しだい")
    save(fig, "a1060_grid.png", SRC, y=-0.1)
    print(json.dumps(head, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
