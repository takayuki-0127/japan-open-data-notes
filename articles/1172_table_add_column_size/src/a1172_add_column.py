"""1172 1行に項目を1つ足すと、表全体の量は足した項目の大きさの分だけ増えるのか？（架空のデータ）

作成者が置いた架空の表の保存の決まりで、行ごとの大きさとページの数を数える。
決まり：行の見出し23B（行に空の項目があれば、項目の数÷8（切り上げ）Bの印を足す）を8の倍数に切り上げる。
決まった大きさの項目（1・2・4・8B）はその大きさの倍数の位置に置き、文章は1Bの長さ＋中身。空の項目は0B。
行の大きさは8の倍数に切り上げる。1ページ8,192B、ページの見出し24B、1行ごとに4Bの置き場所の印。行はページをまたがず、前から順に詰める。
(1) 基本の表（100万行、文章の項目あり）と、決まった大きさの項目だけの表（100万行）に、項目を1つ足す7通り・4通り
(2) 行の数（100・1,000・1万・100万行）を変えた、決まった大きさだけの表
(3) 確かめ：でたらめに作った表500個（項目3〜12個）に、でたらめな大きさの項目を末尾に1つ足す（各10万行）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1172
SRC = "架空の表（作成者が置いた保存の決まりと乱数、seed 1172）"
PAGE, PAGE_HEAD, SLOT = 8192, 24, 4
CAP = PAGE - PAGE_HEAD
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def up(x, a):
    return ((x + a - 1) // a) * a


def text_len(rng, n, med, null_p):
    ln = np.minimum(126, np.round(rng.lognormal(np.log(med), 0.8, n))).astype(np.int64)
    isnull = rng.random(n) < null_p
    return ln, isnull


def row_sizes(cols, n):
    """cols: [(kind, size or lengths, isnull array or None)]。行ごとの大きさ（B）"""
    ncol = len(cols)
    anynull = np.zeros(n, bool)
    for kind, v, isnull in cols:
        if isnull is not None:
            anynull |= isnull
    head = np.where(anynull, up(23 + (ncol + 7) // 8, 8), up(23, 8))
    off = np.zeros(n, np.int64)
    for kind, v, isnull in cols:
        if kind == "fixed":
            new = up(off, v) + v
        else:  # 文章
            new = off + 1 + v
        if isnull is not None:
            off = np.where(isnull, off, new)
        else:
            off = new
    return head + up(off, 8)


def pages_for(sizes):
    need = sizes + SLOT
    cs = np.concatenate([[0], np.cumsum(need)])
    i, pages, n = 0, 0, len(sizes)
    while i < n:
        j = np.searchsorted(cs, cs[i] + CAP, side="right") - 1
        j = max(j, i + 1)
        pages += 1
        i = j
    return pages


def measure(base_cols, new_cols, n, naive_bytes):
    s0, s1 = row_sizes(base_cols, n), row_sizes(new_cols, n)
    p0, p1 = pages_for(s0), pages_for(s1)
    return {"rows": n, "row_bytes_before": int(s0.sum()), "row_bytes_after": int(s1.sum()),
            "pages_before": p0, "pages_after": p1,
            "table_bytes_before": p0 * PAGE, "table_bytes_after": p1 * PAGE,
            "naive_bytes": r(naive_bytes, 1),
            "row_increase_ratio": r((s1.sum() - s0.sum()) / naive_bytes),
            "table_increase_ratio": r((p1 - p0) * PAGE / naive_bytes),
            "rows_size_changed_pct": r((s1 != s0).mean() * 100, 2),
            "mean_row_before": r(s0.mean(), 2), "mean_row_after": r(s1.mean(), 2)}


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"page_bytes": PAGE, "page_head_bytes": PAGE_HEAD, "slot_bytes": SLOT,
                       "row_head_bytes": 23, "row_align": 8}}
    N = 1_000_000
    memo_len, memo_null = text_len(rng, N, 12, 0.3)
    base = [("fixed", 8, None), ("fixed", 8, None), ("fixed", 8, None), ("fixed", 2, None), ("fixed", 1, None),
            ("fixed", 4, None), ("text", memo_len, memo_null)]
    names = ["番号8B", "利用者8B", "日時8B", "状態2B", "印1B", "金額4B", "メモ（文章）"]
    # data：基本の表の先頭1万行の各行の大きさ
    s_base = row_sizes(base, N)
    null90 = rng.random(N) < 0.9
    add_len, _ = text_len(rng, N, 8, 0.0)
    scen = [("end4", "末尾に4Bの数", base + [("fixed", 4, None)], 4 * N),
            ("end8", "末尾に8Bの数", base + [("fixed", 8, None)], 8 * N),
            ("end1", "末尾に1Bの印", base + [("fixed", 1, None)], 1 * N),
            ("end2", "末尾に2Bの数", base + [("fixed", 2, None)], 2 * N),
            ("mid2", "印1Bのすぐ後に2Bの数", base[:5] + [("fixed", 2, None)] + base[5:], 2 * N),
            ("end4_null90", "末尾に4Bの数（9割の行で空）", base + [("fixed", 4, null90)], 4 * N),
            ("end_text", "末尾に文章（平均の大きさで数える）", base + [("text", add_len, None)], float((1 + add_len).sum()))]
    rows = []
    for key, name, cols, naive in scen:
        m = measure(base, cols, N, naive)
        rows.append({"table": "memo", "scenario": key, "name": name, **m})
        print(key, round(time.time() - T0, 1), flush=True)
    fixed = base[:6]
    fscen = [("end4", "末尾に4Bの数", fixed + [("fixed", 4, None)], 4 * N),
             ("end8", "末尾に8Bの数", fixed + [("fixed", 8, None)], 8 * N),
             ("end1", "末尾に1Bの印", fixed + [("fixed", 1, None)], 1 * N),
             ("mid1", "印1Bのすぐ後に1Bの印", fixed[:5] + [("fixed", 1, None)] + fixed[5:], 1 * N)]
    for key, name, cols, naive in fscen:
        m = measure(fixed, cols, N, naive)
        rows.append({"table": "fixed", "scenario": key, "name": name, **m})
    main_df = pd.DataFrame(rows)
    main_df.to_csv(RES / "scenarios.csv", index=False)
    out["scenarios"] = rows
    out["base_table"] = {"columns": names, "rows": N, "memo_null_pct": r(memo_null.mean() * 100, 2),
                         "mean_row_bytes": r(s_base.mean(), 2), "pages": rows[0]["pages_before"],
                         "table_mb": r(rows[0]["table_bytes_before"] / 1e6, 3),
                         "fixed_row_bytes": int(row_sizes(fixed, 1)[0]),
                         "fixed_pages": [x for x in rows if x["table"] == "fixed"][0]["pages_before"]}
    pd.DataFrame({"row_id": np.arange(1, 10_001), "memo_len": np.where(memo_null[:10_000], -1, memo_len[:10_000]),
                  "row_bytes": s_base[:10_000],
                  "row_bytes_add4_end": row_sizes(scen[0][2], N)[:10_000]}).to_csv(DATA / "rows_example.csv", index=False)

    # (2) 行の数
    nrows = []
    for n in [100, 1_000, 10_000, 100_000, 1_000_000]:
        fx = [(k, v, None) for k, v, _ in fixed]
        m = measure(fx, fx + [("fixed", 4, None)], n, 4 * n)
        ml, mn = text_len(rng, n, 12, 0.3)
        b2 = [("fixed", 8, None)] * 3 + [("fixed", 2, None), ("fixed", 1, None), ("fixed", 4, None), ("text", ml, mn)]
        m2 = measure(b2, b2 + [("fixed", 4, None)], n, 4 * n)
        nrows.append({"rows": n, "fixed_pages_before": m["pages_before"], "fixed_pages_after": m["pages_after"],
                      "fixed_table_increase_ratio": m["table_increase_ratio"],
                      "memo_pages_before": m2["pages_before"], "memo_pages_after": m2["pages_after"],
                      "memo_table_increase_ratio": m2["table_increase_ratio"]})
    nrows = pd.DataFrame(nrows)
    nrows.to_csv(RES / "by_rows.csv", index=False)
    out["by_rows"] = nrows.to_dict(orient="records")
    print("rows", round(time.time() - T0, 1), flush=True)

    # (3) でたらめな表500個
    NG = 100_000
    grid = []
    kinds = [1, 2, 4, 8, "text"]
    for t in range(500):
        k = int(rng.integers(3, 13))
        cols = []
        for _ in range(k):
            c = kinds[rng.integers(0, 5)]
            if c == "text":
                ln, nl = text_len(rng, NG, float(rng.choice([4, 12, 40])), float(rng.choice([0.0, 0.3])))
                cols.append(("text", ln, nl))
            else:
                nl = (rng.random(NG) < 0.3) if rng.random() < 0.2 else None
                cols.append(("fixed", c, nl))
        add = int(rng.choice([1, 2, 4, 8]))
        m = measure(cols, cols + [("fixed", add, None)], NG, add * NG)
        grid.append({"table_id": t + 1, "n_cols": k, "has_text": any(c[0] == "text" for c in cols),
                     "has_null": any(c[2] is not None and np.asarray(c[2]).any() for c in cols),
                     "added_bytes": add, **{kk: m[kk] for kk in ["mean_row_before", "mean_row_after", "pages_before",
                                                               "pages_after", "row_increase_ratio", "table_increase_ratio",
                                                               "rows_size_changed_pct"]}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "random_tables.csv", index=False)
    tr = grid.table_increase_ratio
    out["random_tables"] = {"tables": len(grid), "rows_each": NG,
                            "ratio_p10": r(tr.quantile(0.1)), "ratio_median": r(tr.median()), "ratio_p90": r(tr.quantile(0.9)),
                            "ratio_min": r(tr.min()), "ratio_max": r(tr.max()),
                            "zero_pct": r((tr < 0.05).mean() * 100, 2),
                            "within_20pct_pct": r(((tr >= 0.8) & (tr <= 1.2)).mean() * 100, 2),
                            "over_1_5_pct": r((tr > 1.5).mean() * 100, 2),
                            "by_added": {int(a): {"median": r(g.table_increase_ratio.median()),
                                                  "p10": r(g.table_increase_ratio.quantile(0.1)),
                                                  "p90": r(g.table_increase_ratio.quantile(0.9)),
                                                  "zero_pct": r((g.table_increase_ratio < 0.05).mean() * 100, 2),
                                                  "tables": len(g)} for a, g in grid.groupby("added_bytes")},
                            "by_text": {("text" if h else "fixed_only"): {"median": r(g.table_increase_ratio.median()),
                                                                          "within_20pct_pct": r(((g.table_increase_ratio >= 0.8) & (g.table_increase_ratio <= 1.2)).mean() * 100, 2),
                                                                          "tables": len(g)} for h, g in grid.groupby("has_text")}}
    g89 = grid[(grid.n_cols == 8) & grid.has_null]
    gno = grid[~((grid.n_cols == 8) & grid.has_null)]
    out["random_tables"]["cols8_to9_with_null"] = {"tables": len(g89), "median": r(g89.table_increase_ratio.median()),
                                                   "min": r(g89.table_increase_ratio.min()),
                                                   "max": r(g89.table_increase_ratio.max()),
                                                   "others_median": r(gno.table_increase_ratio.median())}
    out["random_tables"]["added8_min"] = r(grid[grid.added_bytes == 8].table_increase_ratio.min())
    out["random_tables"]["added8_max"] = r(grid[grid.added_bytes == 8].table_increase_ratio.max())
    m = {x["table"] + "_" + x["scenario"]: x for x in rows}
    out["headline"] = {"memo_end4": m["memo_end4"]["table_increase_ratio"], "memo_end1": m["memo_end1"]["table_increase_ratio"],
                       "memo_mid2": m["memo_mid2"]["table_increase_ratio"], "fixed_end4": m["fixed_end4"]["table_increase_ratio"],
                       "fixed_end1": m["fixed_end1"]["table_increase_ratio"], "fixed_end8": m["fixed_end8"]["table_increase_ratio"],
                       "random_median": out["random_tables"]["ratio_median"],
                       "random_p10": out["random_tables"]["ratio_p10"], "random_p90": out["random_tables"]["ratio_p90"]}

    # 図1：基本の表と決まった大きさだけの表（表全体の増え÷足した項目の大きさ×行数）
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    labs = [f"{x['name']}\n（{'文章あり' if x['table'] == 'memo' else '決まった大きさだけ'}）" for x in rows]
    vals = [x["table_increase_ratio"] for x in rows]
    cols_ = [BLUE if x["table"] == "memo" else ORANGE for x in rows]
    y = np.arange(len(rows))[::-1]
    ax.barh(y, vals, color=cols_)
    for yy, v in zip(y, vals):
        ax.text(v + 0.05, yy, f"{v:g}倍", va="center", fontsize=8.5)
    ax.axvline(1, color=INK, lw=1)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=8)
    ax.set_xlim(0, max(vals) * 1.15)
    ax.set_xlabel("表全体の増え ÷（足した項目の大きさ×行数）")
    ax.set_title("同じ1項目でも、表全体の増え方は0倍から8倍まで違う")
    save(fig, "a1172_scenarios.png", SRC)

    # 図2：行の数
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = np.arange(len(nrows))
    w = 0.38
    ax.bar(xs - w / 2, nrows.fixed_table_increase_ratio, width=w, color=ORANGE, label="決まった大きさだけの表")
    ax.bar(xs + w / 2, nrows.memo_table_increase_ratio, width=w, color=BLUE, label="文章ありの表")
    for x, a, b2 in zip(xs, nrows.fixed_table_increase_ratio, nrows.memo_table_increase_ratio):
        ax.text(x - w / 2, a + 0.05, f"{a:g}", ha="center", fontsize=8)
        ax.text(x + w / 2, b2 + 0.05, f"{b2:g}", ha="center", fontsize=8)
    ax.axhline(1, color=INK, lw=1)
    ax.set_xticks(xs); ax.set_xticklabels([f"{n:,}行" for n in nrows.rows])
    ax.set_ylim(0, max(nrows.fixed_table_increase_ratio.max(), nrows.memo_table_increase_ratio.max()) * 1.2 + 0.3)
    ax.set_ylabel("表全体の増え ÷（4B×行数）")
    ax.set_title("末尾に4Bを足したとき：行が少ないとページの切れ目で決まる", pad=24)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    save(fig, "a1172_by_rows.png", SRC)

    # 図3：でたらめな表500個
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bins = np.arange(0, 8.6, 0.25)
    gs = [np.clip(grid[grid.added_bytes == a].table_increase_ratio, 0, 8.4) for a in [1, 2, 4, 8]]
    ax.hist(gs, bins=bins, stacked=True, color=[GRAY, GREEN, BLUE, ORANGE],
            label=[f"{a}Bを足す（{len(g)}個）" for a, g in zip([1, 2, 4, 8], gs)])
    ax.axvline(1, color=INK, lw=1)
    ax.set_xlabel("表全体の増え ÷（足した項目の大きさ×行数）（8.4以上は8.4）")
    ax.set_ylabel("表の数（500個のうち）")
    ax.set_title("でたらめに作った表500個に1項目を足したとき（積み上げ）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1172_random_tables.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1172_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
