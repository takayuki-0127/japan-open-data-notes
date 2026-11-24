"""1163 同じ中身をまとめて減る量は、試しに使った一部のデータから見込めるのか？（架空のデータ）

作成者が置いた架空のアプリの保存ファイル20万件（2,000のフォルダ）。中身ごとに写しの数 k を置く：
k=1（写しなし）が55%、残りは k−1 が「1÷一様乱数」の切り捨て（上限999、写しの数が右に長い）。
写しは50%の確率で元と同じフォルダ、残りはでたらめなフォルダに置く。中身の大きさは中央値200KB・対数の標準偏差1.5。
同じ中身をまとめて減る量の割合＝1−（中身ごとに1つだけ残した量÷全部の量）。正しい答えは20万件すべてでの値。
(1) 一部のファイルをでたらめに選ぶ・一部のフォルダを丸ごと選ぶ、の2つで、選ぶ割合0.5〜50%の7段（各100回）
(2) でたらめに選ぶ場合の式（写し k の中身が選んだ中に何件入るかを二項の形で数えた見込み）と比べる
(3) 確かめ：写しなしの割合（30・55・80%）×写しの数の形（右に長い・短い）×同じフォルダに置く確率（0・50・90%）の18通り（選ぶ割合1%・10%、各40回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1163
SRC = "架空のアプリの保存ファイル（作成者が置いた写しの数と置き場所からの乱数、seed 1163）"
N, FOLDERS = 200_000, 2_000
MED, SIG = 200.0, 1.5
BASE = {"p_single": 0.55, "tail": "long", "same": 0.5}
FRACS = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
R_BASE, R_GRID = 100, 40
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def copies(rng, m, p_single, tail):
    k = np.ones(m, dtype=np.int64)
    dup = rng.random(m) >= p_single
    nd = int(dup.sum())
    if tail == "long":
        extra = np.minimum(np.floor(1.0 / rng.random(nd)), 999).astype(np.int64)
    else:
        extra = rng.geometric(0.5, nd).astype(np.int64)   # 1,2,3…（平均2）
    k[dup] = 1 + extra
    return k


def build(rng, p_single, tail, same):
    k = copies(rng, N, p_single, tail)
    cs = np.cumsum(k)
    m = int(np.searchsorted(cs, N) + 1)
    k = k[:m].copy()
    k[-1] -= cs[m - 1] - N
    size = rng.lognormal(np.log(MED), SIG, m)
    cid = np.repeat(np.arange(m), k)
    home = rng.integers(0, FOLDERS, m)
    first = np.r_[True, cid[1:] != cid[:-1]]
    stay = first | (rng.random(N) < same)
    folder = np.where(stay, home[cid], rng.integers(0, FOLDERS, N))
    return {"k": k, "size": size, "cid": cid, "fsize": size[cid], "folder": folder}


def saving(cid, fsize):
    tot = fsize.sum()
    u, idx = np.unique(cid, return_index=True)
    return 1 - fsize[idx].sum() / tot


def formula_random(d, f):
    k, s = d["k"], d["size"]
    saved = (s * (k * f - 1 + (1 - f) ** k)).sum()
    return saved / (s * k * f).sum()


def sample_runs(rng, d, f, R):
    res = {"random": [], "folder": []}
    m = int(round(N * f))
    nf = max(1, int(round(FOLDERS * f)))
    for _ in range(R):
        idx = rng.choice(N, m, replace=False)
        res["random"].append(saving(d["cid"][idx], d["fsize"][idx]))
        fs = np.zeros(FOLDERS, bool)
        fs[rng.choice(FOLDERS, nf, replace=False)] = True
        sel = fs[d["folder"]]
        res["folder"].append(saving(d["cid"][sel], d["fsize"][sel]))
    return {k: np.array(v) for k, v in res.items()}


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    d = build(rng, **BASE)
    true = saving(d["cid"], d["fsize"])
    k = d["k"]
    out["base_setting"] = {"files": N, "folders": FOLDERS, "contents": int(len(k)),
                           "single_content_pct": r((k == 1).mean() * 100, 2),
                           "files_in_dup_groups_pct": r((k[d["cid"]] > 1).mean() * 100, 2),
                           "max_copies": int(k.max()), "true_saving_pct": r(true * 100, 2),
                           "true_saving_count_pct": r((1 - len(k) / N) * 100, 2)}
    pd.DataFrame({"file_id": np.arange(1, 20_001), "content_id": d["cid"][:20_000],
                  "folder_id": d["folder"][:20_000], "size_kb": np.round(d["fsize"][:20_000], 2)}).to_csv(
        DATA / "files_example.csv", index=False)

    rows = []
    for f in FRACS:
        rr = sample_runs(rng, d, f, R_BASE)
        row = {"sample_pct": f * 100, "true_saving_pct": r(true * 100, 2),
               "formula_random_pct": r(formula_random(d, f) * 100, 2)}
        for m in ["random", "folder"]:
            v = rr[m]
            row.update({f"{m}_median_pct": r(np.median(v) * 100, 2), f"{m}_p10_pct": r(np.quantile(v, 0.1) * 100, 2),
                        f"{m}_p90_pct": r(np.quantile(v, 0.9) * 100, 2),
                        f"{m}_over_true": r(np.median(v) / true)})
        rows.append(row)
        print("base", f, round(time.time() - T0, 1), flush=True)
    base = pd.DataFrame(rows)
    base.to_csv(RES / "base_by_fraction.csv", index=False)
    out["base_by_fraction"] = rows
    out["base_formula_max_gap_points"] = r((base.random_median_pct - base.formula_random_pct).abs().max(), 2)

    grows = []
    for ps in [0.3, 0.55, 0.8]:
        for tail in ["long", "short"]:
            for same in [0.0, 0.5, 0.9]:
                dg = build(rng, ps, tail, same)
                tg = saving(dg["cid"], dg["fsize"])
                for f in [0.01, 0.1]:
                    rr = sample_runs(rng, dg, f, R_GRID)
                    grows.append({"single_pct": ps * 100, "copies_tail": "右に長い" if tail == "long" else "短い",
                                  "same_folder_pct": same * 100, "sample_pct": f * 100, "true_saving_pct": r(tg * 100, 2),
                                  "random_median_pct": r(np.median(rr["random"]) * 100, 2),
                                  "folder_median_pct": r(np.median(rr["folder"]) * 100, 2),
                                  "random_over_true": r(np.median(rr["random"]) / tg),
                                  "folder_over_true": r(np.median(rr["folder"]) / tg),
                                  "formula_random_pct": r(formula_random(dg, f) * 100, 2)})
            print("grid", ps, tail, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    g1, g10 = grid[grid.sample_pct == 1], grid[grid.sample_pct == 10]
    out["grid"] = {"settings": int(len(grid) // 2),
                   "true_range": [r(grid.true_saving_pct.min(), 2), r(grid.true_saving_pct.max(), 2)],
                   "random_over_true_1pct": [r(g1.random_over_true.min()), r(g1.random_over_true.max())],
                   "random_over_true_10pct": [r(g10.random_over_true.min()), r(g10.random_over_true.max())],
                   "folder_over_true_1pct": [r(g1.folder_over_true.min()), r(g1.folder_over_true.max())],
                   "folder_over_true_10pct": [r(g10.folder_over_true.min()), r(g10.folder_over_true.max())],
                   "folder_beats_random_1pct": int((g1.folder_over_true > g1.random_over_true).sum()),
                   "formula_max_gap_points": r((grid.random_median_pct - grid.formula_random_pct).abs().max(), 2)}
    for tl in ["右に長い", "短い"]:
        for nm, gx in [("1pct", g1), ("10pct", g10)]:
            gt = gx[gx.copies_tail == tl]
            out["grid"][f"{tl}_random_over_true_{nm}"] = [r(gt.random_over_true.min()), r(gt.random_over_true.max())]
    for same in [0.0, 50.0, 90.0]:
        gs = g1[g1.same_folder_pct == same]
        out["grid"][f"same{int(same)}_folder_over_true_1pct"] = [r(gs.folder_over_true.min()), r(gs.folder_over_true.max())]
    b1 = base[base.sample_pct == 1].iloc[0]
    b10 = base[base.sample_pct == 10].iloc[0]
    out["headline"] = {"true_saving_pct": r(true * 100, 2), "random_1pct": b1.random_median_pct,
                       "random_10pct": b10.random_median_pct, "folder_1pct": b1.folder_median_pct,
                       "folder_10pct": b10.folder_median_pct}

    # 図1：選ぶ割合と、一部で見えた減る量
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = base.sample_pct
    ax.plot(x, base.random_median_pct, "o-", color=BLUE, label="ファイルをでたらめに選ぶ（中央値）")
    ax.fill_between(x, base.random_p10_pct, base.random_p90_pct, color=BLUE, alpha=0.15, lw=0)
    ax.plot(x, base.folder_median_pct, "s-", color=ORANGE, label="フォルダを丸ごと選ぶ（中央値）")
    ax.fill_between(x, base.folder_p10_pct, base.folder_p90_pct, color=ORANGE, alpha=0.15, lw=0)
    ax.plot(x, base.formula_random_pct, ":", color=INK, lw=1.2, label="でたらめに選ぶときの式")
    ax.axhline(true * 100, color=GREEN, lw=1.5)
    ax.text(8, true * 100 + 1.5, f"20万件すべてで減る量 {true * 100:.2f}%", color=GREEN, fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v:g}%" for v in x])
    ax.set_ylim(0, 100)
    ax.set_xlabel("試しに使った一部の割合（対数の目盛り）")
    ax.set_ylabel("一部の中で、同じ中身をまとめて減った量（%）")
    ax.set_title("一部が小さいほど、減る量は小さく見える（基本の置き方）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a1163_by_fraction.png", SRC)

    # 図2：写しの数の分かれ方（基本）
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bins = [1, 2, 3, 5, 10, 100, 1000]
    lab = ["1（写しなし）", "2", "3〜4", "5〜9", "10〜99", "100以上"]
    kk = k
    cnt = [((kk >= lo) & (kk < hi)).sum() for lo, hi in zip(bins[:-1], bins[1:])]
    byt = [(d["size"][(kk >= lo) & (kk < hi)] * kk[(kk >= lo) & (kk < hi)]).sum() for lo, hi in zip(bins[:-1], bins[1:])]
    file_share = np.array([(kk[(kk >= lo) & (kk < hi)]).sum() for lo, hi in zip(bins[:-1], bins[1:])]) / N * 100
    byte_share = np.array(byt) / d["fsize"].sum() * 100
    xs = np.arange(len(lab))
    ax.bar(xs, file_share, color=BLUE)
    for i, v in enumerate(file_share):
        ax.text(i, v + 1, f"{r(v, 2):g}%", ha="center", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels(lab, fontsize=9)
    ax.set_ylim(0, max(file_share) * 1.2)
    ax.set_xlabel("同じ中身の写しの数（その中身が何件あるか）")
    ax.set_ylabel("20万件に占める割合（%）")
    ax.set_title("ファイルの多くは、写しの数の多い中身に属する（基本の置き方）")
    save(fig, "a1163_copies.png", SRC)
    pd.DataFrame({"copies_band": lab, "contents": cnt, "files_pct": np.round(file_share, 2),
                  "bytes_pct": np.round(byte_share, 2)}).to_csv(RES / "base_copies.csv", index=False)
    out["base_copies"] = {lb: {"files_pct": r(fs, 2), "bytes_pct": r(bs, 2)} for lb, fs, bs in zip(lab, file_share, byte_share)}

    # 図3：18通り、1%で見えた減る量÷正しい答え
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    gg = grid[grid.sample_pct == 1].reset_index(drop=True)
    xs = np.arange(len(gg))
    ax.bar(xs - 0.2, gg.random_over_true, width=0.4, color=BLUE, label="ファイルをでたらめに選ぶ")
    ax.bar(xs + 0.2, gg.folder_over_true, width=0.4, color=ORANGE, label="フォルダを丸ごと選ぶ")
    ax.axhline(1, color=INK, lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{s:g}%\n{'長' if t == '右に長い' else '短'}\n{q:g}%" for s, t, q in
                        zip(gg.single_pct, gg.copies_tail, gg.same_folder_pct)], fontsize=7.5)
    ax.set_ylim(0, 1.1)
    ax.set_xlabel("写しなしの割合（上）・写しの数の形（中：長／短）・同じフォルダに置く確率（下）")
    ax.set_ylabel("1%で見えた減る量 ÷ 正しい答え（中央値）")
    ax.set_title("1%の一部で見えた減る量は、18通りで正しい答えに届かない", pad=28)
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    save(fig, "a1163_grid_1pct.png", SRC, y=-0.1)

    (RES / "a1163_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    print("sec", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
