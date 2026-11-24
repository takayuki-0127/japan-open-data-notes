"""1247 読み放題で読まれたページ数から、最後まで読んだ人の数はどこまで分かるのか？（架空のデータ）

架空の電子書籍（読み放題で読まれる本）。読み始めた人ごとに、どこでやめるかを作成者が置いた決まりで乱数で引く。
・はじめのほうでやめる人（割合 e）：最初の1割のページのどこかでやめる
・それ以外の人：1ページ読むごとに確率 h でやめる。最後のページまで残った人が「最後まで読んだ人」
・最後まで読んだ人の一部（割合 r）は、本の3割のページを読み返す（読み返しもページ数に数えられると置く）
書き手に見えるのは、読まれたページ数の合計だけ（読み始めた人数・どこでやめたかは見えない）と置き、
「読まれたページ数 ÷ 本のページ数」が、本当に最後まで読んだ人の数にどれだけ合うかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1247
SRC = "架空の電子書籍の読まれ方（作成者が乱数で作成、seed 1247）"
REREAD_PART = 0.3


def readers(rng, n, P, e, h, r):
    """読み始めた n 人の読んだページ数と、最後まで読んだか"""
    early = rng.random(n) < e
    stop_early = rng.integers(1, max(int(P * 0.1), 1) + 1, n)
    if h > 0:
        stop_h = rng.geometric(h, n)               # この数のページ目でやめる
    else:
        stop_h = np.full(n, P + 1)
    stop = np.where(early, stop_early, stop_h)
    finished = stop > P
    pages = np.minimum(stop, P).astype(float)
    reread = finished & (rng.random(n) < r)
    pages = pages + reread * round(P * REREAD_PART)
    return pages, finished


def make_books(rng, n_books=1000, P=200, r=0.0):
    rows = []
    for b in range(n_books):
        e = rng.uniform(0, 0.5); h = rng.uniform(0, 0.01); n = int(rng.integers(100, 2001))
        pages, fin = readers(rng, n, P, e, h, r)
        rows.append({"book_id": b + 1, "early_share": round(e, 4), "stop_per_page": round(h, 5), "starters": n,
                     "pages_total": int(pages.sum()), "finished": int(fin.sum())})
    df = pd.DataFrame(rows)
    df["pages_over_book"] = df.pages_total / P
    df["ratio"] = df.pages_over_book / df.finished.clip(lower=1)
    return df


def close_pair_hit(df, tol=0.10):
    """読まれたページ数が10%以内の2冊で、最後まで読んだ人の多いほうを、ページ数の多いほうと読んで当たる割合"""
    t = df.pages_total.values.astype(float); f = df.finished.values
    i, j = np.triu_indices(len(df), 1)
    close = np.abs(t[i] - t[j]) / np.maximum(t[i], t[j]) < tol
    ok = close & (f[i] != f[j])
    hit = np.sign(t[i] - t[j]) == np.sign(f[i] - f[j])
    return float(hit[ok].mean()), int(ok.sum())


def summarize(df):
    rr = df.ratio[df.finished > 0]
    return {"ratio_median": round(float(rr.median()), 3), "ratio_p10": round(float(rr.quantile(.1)), 3),
            "ratio_p90": round(float(rr.quantile(.9)), 3),
            "within20_share": round(float(((rr >= 0.8) & (rr <= 1.2)).mean()) * 100, 2),
            "over_share": round(float((df.pages_over_book >= df.finished).mean()) * 100, 2),
            "close_pair_hit": round(close_pair_hit(df)[0] * 100, 2)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    P = 200

    # 1) 架空の1,000冊（基本：200ページ、読み返しなし）
    books = make_books(rng, 1000, P, 0.0)
    books.drop(columns=["ratio"]).round(4).to_csv(DATA / "books_1000.csv", index=False)
    base = summarize(books)
    base["close_pair_n"] = close_pair_hit(books)[1]
    base["finished_share_of_starters_p10"] = round(float((books.finished / books.starters).quantile(.1)) * 100, 2)
    base["finished_share_of_starters_p90"] = round(float((books.finished / books.starters).quantile(.9)) * 100, 2)

    # 読まれたページ数が同じくらい（本の250〜300冊分）の本で、最後まで読んだ人の幅
    band = books[(books.pages_over_book >= 250) & (books.pages_over_book < 300)]
    base["band_250_300"] = {"books": int(len(band)), "finished_min": int(band.finished.min()),
                            "finished_p10": float(band.finished.quantile(.1)),
                            "finished_p90": float(band.finished.quantile(.9)),
                            "finished_max": int(band.finished.max())}

    # 2) 読まれ方の形3つ：同じ10万ページ（本の500冊分）が読まれたとき
    shapes = [("はじめでやめる人が多い", 0.5, 0.01), ("少しずつ減る", 0.0, 0.008), ("ほとんど読み切る", 0.05, 0.0005)]
    srows = []
    for k, (nm, e, h) in enumerate(shapes):
        pages, fin = readers(np.random.default_rng(SEED * 10 + k), 400000, P, e, h, 0.0)
        per = pages.mean(); fs = fin.mean()
        n_start = 100000 / per
        srows.append({"shape": nm, "early_share": e, "stop_per_page": h,
                      "pages_per_starter": round(float(per), 2), "finished_share_of_starters": round(float(fs) * 100, 2),
                      "starters_for_100k_pages": round(float(n_start), 1),
                      "finished_for_100k_pages": round(float(n_start * fs), 1),
                      "pages_over_book": 500.0,
                      "formula_pages_per_starter": round(e * (1 + int(P * 0.1)) / 2 + (1 - e) * (1 - (1 - h) ** P) / h, 2),
                      "formula_finished_share": round((1 - e) * (1 - h) ** P * 100, 2)})
    shp = pd.DataFrame(srows)
    shp.to_csv(RES / "shapes_100k_pages.csv", index=False)

    # 3) 置き方を変えると（本のページ数 × 読み返す人の割合、9通り、各1,000冊）
    grid = []
    for Pg in [100, 200, 400]:
        for r in [0.0, 0.1, 0.3]:
            d = make_books(np.random.default_rng(SEED * 100 + Pg + int(r * 10)), 1000, Pg, r)
            s = summarize(d)
            grid.append({"book_pages": Pg, "reread_share": r, **s})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gr = {c: [float(grid[c].min()), float(grid[c].max())] for c in
          ["ratio_median", "ratio_p10", "ratio_p90", "within20_share", "over_share", "close_pair_hit"]}

    out = {"setup": {"book_pages": P, "books": 1000, "early_share": "0〜0.5の一様", "stop_per_page": "0〜0.01の一様",
                     "starters": "100〜2,000人の一様", "reread_part": REREAD_PART},
           "base_1000_books": base, "shapes_100k_pages": shp.to_dict("records"), "grid_range": gr}
    json.dump(out, open(RES / "a1247_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：ページ数÷本のページ数 と 本当に最後まで読んだ人
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(books.pages_over_book, books.finished, s=8, color=BLUE, alpha=.5, lw=0)
    mx = float(books.pages_over_book.max()) * 1.03
    ax.plot([0, mx], [0, mx], color=ORANGE, lw=1.2, ls="--")
    ax.text(mx * 0.08, mx * 0.55, "点線：冊分＝最後まで読んだ人", color=ORANGE, fontsize=8.5)
    ax.axvspan(250, 300, color=GRAY, alpha=.25)
    bb = base["band_250_300"]
    ax.annotate(f"250〜300冊分の{bb['books']}冊：\n最後まで読んだ人は{bb['finished_min']}〜{bb['finished_max']}人",
                xy=(275, 280), xytext=(330, 1250), fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.8))
    ax.set_xlim(0, mx); ax.set_ylim(0, mx)
    ax.set_xlabel("読まれたページ数 ÷ 本のページ数（冊分）"); ax.set_ylabel("本当に最後まで読んだ人（人）")
    ax.set_title("「冊分」は最後まで読んだ人の上限にしかならない（作りどおり、1,000冊）", fontsize=11.5)
    save(fig, "a1247_scatter.png", SRC)

    # 図2：同じ10万ページでの、読まれ方の形ごとの最後まで読んだ人
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    yy = np.arange(len(shp))[::-1]
    ax.barh(yy, shp.finished_for_100k_pages, color=[ORANGE, LIGHT, BLUE], height=0.55)
    for y, v, n in zip(yy, shp.finished_for_100k_pages, shp.starters_for_100k_pages):
        if v > 400:
            ax.text(10, y, f"{v:.1f}人（読み始めた人{n:,.1f}人）", va="center", fontsize=9, color="white")
        else:
            ax.text(v + 6, y, f"{v:.1f}人（読み始めた人{n:,.1f}人）", va="center", fontsize=9)
    ax.axvline(500, color=GRAY, lw=1, ls=":"); ax.text(505, 1.5, "点線：500冊分", color=GRAY, fontsize=8.5, va="center")
    ax.set_yticks(yy); ax.set_yticklabels(shp["shape"]); ax.set_xlim(0, 720)
    ax.set_xlabel("最後まで読んだ人（人）")
    ax.set_title("同じ10万ページ（200ページの本の500冊分）でも、読まれ方で人数が変わる", fontsize=11.5)
    save(fig, "a1247_shapes.png", SRC)

    # 図3：置き方9通り：ページ数÷本のページ数が、最後まで読んだ人の何倍か（中央値と10〜90%）
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    xx = np.arange(len(grid))
    ax.bar(xx, grid.ratio_median, color=BLUE, width=0.6)
    ax.errorbar(xx, grid.ratio_median, yerr=[grid.ratio_median - grid.ratio_p10, grid.ratio_p90 - grid.ratio_median],
                fmt="none", ecolor=INK, lw=1, capsize=3)
    for x_, v in zip(xx, grid.ratio_median):
        ax.text(x_, 0.08, f"{v:.2f}", ha="center", fontsize=8.5, color="white")
    ax.axhline(1, color=ORANGE, lw=1, ls="--")
    ax.set_xticks(xx); ax.set_xticklabels([f"{p}ページ\n読み返す人\n{int(r*100)}%" for p, r in zip(grid.book_pages, grid.reread_share)], fontsize=7.5)
    ax.set_ylim(0, None); ax.set_ylabel("冊分 ÷ 最後まで読んだ人（倍）")
    ax.set_title("置き方9通り：冊分は最後まで読んだ人の何倍か（棒は中央値、線は10〜90%）", fontsize=11.5)
    save(fig, "a1247_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
