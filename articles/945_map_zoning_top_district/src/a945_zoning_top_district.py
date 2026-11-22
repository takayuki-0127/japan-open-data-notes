"""945 区域の線の引き方で、「いちばん売れる地区」は入れ替わるのか？（架空のデータ）

架空の町（20×20 の街区、1マス＝1街区）。街区ごとの売上の「本当の水準」を作成者が置く
（町全体の底上げ＋売れる場所Aと売れる場所Bの2つの山）。1か月の売上はその水準のまわりで振れる（ポアソン分布）。
同じ1か月の売上を、線の引き方だけを変えた区割り（5地区、ボロノイ分割）で集計し、
売上の合計がいちばん大きい地区がどこに来るかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 945
SRC = "架空の町の街区と売上（作成者が乱数で作成、seed 945）"
G = 20
A_XY, B_XY = (5, 14), (14, 5)
XX, YY = np.meshgrid(np.arange(G), np.arange(G), indexing="xy")


def level(rb=0.85, w=2.5, base=10.0, peak=60.0):
    """街区ごとの本当の売上の水準（万円／月）"""
    da = (XX - A_XY[0]) ** 2 + (YY - A_XY[1]) ** 2
    db = (XX - B_XY[0]) ** 2 + (YY - B_XY[1]) ** 2
    return base + peak * (np.exp(-da / (2 * w * w)) + rb * np.exp(-db / (2 * w * w)))


def zoning(rng, k):
    """ランダムな k 個の中心から、いちばん近い中心で地区を決める（ボロノイ分割）。空の地区は作り直す"""
    while True:
        c = rng.uniform(-0.5, G - 0.5, size=(k, 2))
        d = (XX[None] - c[:, 0, None, None]) ** 2 + (YY[None] - c[:, 1, None, None]) ** 2
        z = d.argmin(0)
        if len(np.unique(z)) == k:
            return z


def top_info(z, sales, k):
    tot = np.bincount(z.ravel(), weights=sales.ravel(), minlength=k)
    size = np.bincount(z.ravel(), minlength=k)
    t = int(tot.argmax())
    return {"top": t, "has_A": bool(z[A_XY[1], A_XY[0]] == t), "has_B": bool(z[B_XY[1], B_XY[0]] == t),
            "is_largest": bool(size[t] == size.max()), "top_size": int(size[t]),
            "top_share": float(tot[t] / tot.sum()),
            "top_mean_per_cell": float(tot[t] / size[t])}


def run_setting(rng, n_zone, k=5, rb=0.85, w=2.5):
    sales = rng.poisson(level(rb, w)).astype(float)
    rows = []
    for _ in range(n_zone):
        z = zoning(rng, k)
        rows.append(top_info(z, sales, k))
    return pd.DataFrame(rows), sales


def summarize(df):
    a, b = df.has_A, df.has_B
    return {"share_A_only": round(float((a & ~b).mean()), 3), "share_B_only": round(float((b & ~a).mean()), 3),
            "share_both": round(float((a & b).mean()), 3), "share_neither": round(float((~a & ~b).mean()), 3),
            "share_top_is_largest": round(float(df.is_largest.mean()), 3),
            "top_share_p10": round(float(df.top_share.quantile(.1)), 3),
            "top_share_p90": round(float(df.top_share.quantile(.9)), 3)}


def main():
    rng = np.random.default_rng(SEED)
    lam = level()
    sales = rng.poisson(lam).astype(float)
    cells = pd.DataFrame({"x": XX.ravel(), "y": YY.ravel(), "level": lam.ravel().round(3), "sales": sales.ravel()})
    cells.to_csv(DATA / "cells_example_month.csv", index=False)

    # 1) 同じ1か月の売上を、2,000通りの区割り（5地区）で集計
    N = 2000
    rows, zs = [], []
    for i in range(N):
        z = zoning(rng, 5)
        if i < 4:
            zs.append(z)
        rows.append(top_info(z, sales, 5))
    base = pd.DataFrame(rows)
    # 街区ごとに「いちばん売れる地区」に入った割合
    in_top = np.zeros((G, G))
    rng_cnt = np.random.default_rng(SEED + 1)
    for _ in range(N):
        z = zoning(rng_cnt, 5)
        tot = np.bincount(z.ravel(), weights=sales.ravel(), minlength=5)
        in_top += (z == tot.argmax())
    in_top /= N
    base_sum = summarize(base)
    base_sum["n_zonings"] = N
    base_sum["expected_largest_if_size_irrelevant"] = 0.2
    base_sum["cell_in_top_A"] = round(float(in_top[A_XY[1], A_XY[0]]), 3)
    base_sum["cell_in_top_B"] = round(float(in_top[B_XY[1], B_XY[0]]), 3)
    base_sum["cells_in_top_ge_50pct"] = int((in_top >= 0.5).sum())
    base_sum["cells_in_top_le_5pct"] = int((in_top <= 0.05).sum())
    base_sum["cell_in_top_min"] = round(float(in_top.min()), 3)
    base_sum["cell_in_top_max"] = round(float(in_top.max()), 3)
    base_sum["total_A_half"] = None
    # 本当の水準での、Aの山とBの山の売上（半径4街区以内の合計）
    da = (XX - A_XY[0]) ** 2 + (YY - A_XY[1]) ** 2
    db = (XX - B_XY[0]) ** 2 + (YY - B_XY[1]) ** 2
    base_sum.pop("total_A_half")
    base_sum["sales_within4_A"] = int(sales[da <= 16].sum())
    base_sum["sales_within4_B"] = int(sales[db <= 16].sum())
    base_sum["level_within4_A"] = round(float(lam[da <= 16].sum()), 1)
    base_sum["level_within4_B"] = round(float(lam[db <= 16].sum()), 1)
    base_sum["total_sales"] = int(sales.sum())
    base.to_csv(RES / "zonings_2000.csv", index=False, float_format="%.4f")

    # 例の4つの区割り
    ex = []
    for j, z in enumerate(zs):
        info = top_info(z, sales, 5)
        tot = np.bincount(z.ravel(), weights=sales.ravel(), minlength=5)
        size = np.bincount(z.ravel(), minlength=5)
        ex.append({"zoning": j + 1, "top_has_A": info["has_A"], "top_has_B": info["has_B"],
                   "top_cells": info["top_size"], "top_sales": int(tot[info["top"]]),
                   "district_cells": [int(s) for s in size], "district_sales": [int(t) for t in tot]})
    pd.DataFrame({"x": XX.ravel(), "y": YY.ravel(),
                  **{f"zoning{j+1}": zs[j].ravel() for j in range(4)}}).to_csv(DATA / "zonings_example4.csv", index=False)

    # 2) 区割りを固定し、月ごとの振れだけで1位が変わるか（例の区割り1、1,000か月）
    z0 = zs[0]
    t0 = top_info(z0, sales, 5)["top"]
    same = []
    for _ in range(1000):
        s2 = rng.poisson(lam).astype(float)
        same.append(top_info(z0, s2, 5)["top"] == t0)
    month_only = {"same_top_as_example_month": round(float(np.mean(same)), 3)}
    # 区割りも月も変えず、区割りだけ2つ選んだとき、1位の地区がAとBで入れ替わる割合
    lab = np.where(base.has_A & ~base.has_B, "A", np.where(base.has_B & ~base.has_A, "B", "other"))
    i1, i2 = rng.integers(0, N, 20000), rng.integers(0, N, 20000)
    month_only["pair_zonings_A_vs_B_swap"] = round(float(((lab[i1] == "A") & (lab[i2] == "B") |
                                                         (lab[i1] == "B") & (lab[i2] == "A")).mean()), 3)

    # 3) 確かめ：置き方を1つずつ変える（各500通りの区割り、1か月の売上も作り直す）
    rob = []
    settings = [("Bの山の強さ（Aに対する比）", "rb", [0.3, 0.45, 0.6, 0.85, 1.0]),
                ("地区の数", "k", [3, 5, 8, 12]),
                ("山の広がり（街区）", "w", [1.5, 2.5, 4.0])]
    for label, key, vals in settings:
        for v in vals:
            kw = {"k": 5, "rb": 0.85, "w": 2.5}
            kw[key] = v
            r2 = np.random.default_rng(SEED * 100 + int(v * 100) + len(key))
            df, _ = run_setting(r2, 500, **kw)
            s = summarize(df)
            rob.append({"変えたもの": label, "値": v, "基本": (kw == {"k": 5, "rb": 0.85, "w": 2.5}),
                        "Aだけを含む": s["share_A_only"], "Bだけを含む": s["share_B_only"],
                        "両方を含む": s["share_both"], "どちらも含まない": s["share_neither"],
                        "1位が最も広い地区": s["share_top_is_largest"], "広さと無関係なら": round(1 / kw["k"], 3)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"base_2000_zonings": base_sum, "examples": ex, "fixed_zoning_month_noise": month_only,
           "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a945_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：売上の地図と、街区ごとに「いちばん売れる地区」に入った割合
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6))
    im = axes[0].imshow(sales, origin="lower", cmap="Blues")
    cb = fig.colorbar(im, ax=axes[0], shrink=.8); cb.set_label("1か月の売上（万円）")
    axes[0].set_title("1か月の売上（Bの山はAの0.85倍と置いた）", fontsize=10.5)
    im2 = axes[1].imshow(in_top * 100, origin="lower", cmap="Oranges", vmin=0, vmax=100)
    cb2 = fig.colorbar(im2, ax=axes[1], shrink=.8); cb2.set_label("1位の地区に入った割合（%）")
    axes[1].set_title("その街区が「いちばん売れる地区」に入った割合\n（2,000通りの区割り）", fontsize=10.5)
    for ax in axes:
        for (x, y), name in [(A_XY, "A"), (B_XY, "B")]:
            ax.text(x, y, name, ha="center", va="center", fontsize=12, color=INK, fontweight="bold",
                    bbox=dict(fc="white", ec="none", alpha=.85, pad=1.5))
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("架空の町（20×20街区）：売れる場所はAとBの2つ", fontsize=12)
    fig.tight_layout()
    save(fig, "a945_sales_map.png", SRC)

    # 図2：例の4つの区割り（1位の地区を色で）
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 7.4))
    for j, ax in enumerate(axes.ravel()):
        z = zs[j]
        tot = np.bincount(z.ravel(), weights=sales.ravel(), minlength=5)
        t = tot.argmax()
        img = np.where(z == t, 1.0, 0.0)
        ax.imshow(img, origin="lower", cmap=ListedColormap(["#eeeeec", "#f6c3a8"]), vmin=0, vmax=1)
        # 境界線（街区の辺に沿って引く）
        segs = []
        for yy_ in range(G):
            for xx_ in range(G - 1):
                if z[yy_, xx_] != z[yy_, xx_ + 1]:
                    segs.append([(xx_ + .5, yy_ - .5), (xx_ + .5, yy_ + .5)])
        for yy_ in range(G - 1):
            for xx_ in range(G):
                if z[yy_, xx_] != z[yy_ + 1, xx_]:
                    segs.append([(xx_ - .5, yy_ + .5), (xx_ + .5, yy_ + .5)])
        from matplotlib.collections import LineCollection
        ax.add_collection(LineCollection(segs, colors=INK, linewidths=1.2))
        for d in range(5):
            yy, xx = np.nonzero(z == d)
            # 地区の中で、重心にいちばん近い街区に数字を置く（A・Bの印から離す）
            dd = (xx - xx.mean()) ** 2 + (yy - yy.mean()) ** 2
            for (px, py) in [A_XY, B_XY]:
                dd = dd + 40.0 * ((np.abs(xx - px) <= 2) & (np.abs(yy - py) <= 2))
            m = dd.argmin()
            ax.text(xx[m], yy[m], f"{int(tot[d])}", ha="center", va="center", fontsize=9,
                    color=INK, fontweight="bold" if d == t else "normal")
        for (x, y), name in [(A_XY, "A"), (B_XY, "B")]:
            ax.plot(x, y, "o", ms=9, mfc="none", mec=BLUE, mew=1.8)
            ax.text(x + 0.9, y + 0.9, name, color=BLUE, fontsize=10, fontweight="bold")
        where = "Aを含む" if z[A_XY[1], A_XY[0]] == t and z[B_XY[1], B_XY[0]] != t else \
            ("Bを含む" if z[B_XY[1], B_XY[0]] == t and z[A_XY[1], A_XY[0]] != t else
             ("AとBを含む" if z[A_XY[1], A_XY[0]] == t else "AもBも含まない"))
        ax.set_title(f"区割り{j+1}：1位の地区は{where}", fontsize=10.5)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("同じ1か月の売上でも、線の引き方で「いちばん売れる地区」（色付き）が変わる\n数字は地区の売上の合計（万円）", fontsize=12)
    fig.tight_layout()
    save(fig, "a945_zonings.png", SRC)

    # 図3：1位の地区がどこを含むか（置き方ごと）
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    lab = [f"{r['変えたもの'].split('（')[0]} {r['値']:g}" + ("（基本）" if r["基本"] else "") for r in rob.to_dict("records")]
    lab = [l.replace("Bの山の強さ", "Bの強さ").replace("山の広がり", "山の広がり") for l in lab]
    y = np.arange(len(rob))[::-1]
    left = np.zeros(len(rob))
    for col, c, nm in [("Aだけを含む", BLUE, "Aだけを含む"), ("Bだけを含む", ORANGE, "Bだけを含む"),
                       ("両方を含む", GREEN, "AとBの両方を含む"), ("どちらも含まない", GRAY, "どちらも含まない")]:
        v = rob[col].values * 100
        ax.barh(y, v, left=left, color=c, label=nm, height=.7, edgecolor="white", linewidth=1)
        left += v
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("区割りのうちの割合（%、各500通り）")
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="upper center", bbox_to_anchor=(0.45, -0.13))
    ax.set_title("「いちばん売れる地区」がAを含むかBを含むかは、区割りしだいで分かれる")
    save(fig, "a945_robustness.png", SRC, y=-0.08)
    print(json.dumps({k: v for k, v in out.items() if k != "robustness"}, ensure_ascii=False, indent=1))
    print(rob.to_string())


if __name__ == "__main__":
    main()
