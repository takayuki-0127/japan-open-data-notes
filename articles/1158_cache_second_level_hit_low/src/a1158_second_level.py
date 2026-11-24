"""1158 1段目で外れたものだけが2段目に来るとき、2段目の当たり率はなぜ低く見えるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ10万件への問い合わせの列。i番目に人気のデータが選ばれる確率は 1÷i^a に比例すると置いた。
置き場所（キャッシュ）を2段に重ねる。問い合わせはまず小さい1段目に行き、外れたものだけが大きい2段目に行く。
2段目でも外れたら元のデータを取りに行く。どちらの段も件数で数え、いっぱいなら、いちばん長く使われていないものを捨てる。
外れたデータは、取ってきた段とその上の段に置く。
(1) 基本の置き方（a=0.8、1段目は全体の1%、2段目は8%）で、1段目の当たり率・2段目に来た問い合わせのうちの当たり率・
    全体に対する2段目の当たりの割合・2段を合わせた当たり率・2段目と同じ大きさの置き場所を1段だけ置いたときの当たり率を比べる
(2) 人気の順位の帯ごとに、全体の問い合わせと2段目に来た問い合わせの中身、帯ごとの2段目の当たり率を数える
(3) 確かめ：偏り a（0.6・0.8・1.0・1.2）×1段目の大きさ（0.25・1・4%）×2段目の大きさ（4・8・16%）の36通り
"""
import json
import time
from collections import OrderedDict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1158
SRC = "架空のアプリへの問い合わせ（作成者が置いた人気の偏りからの乱数、seed 1158）"
N_ITEMS = 100_000
WARM, MEAS = 100_000, 300_000
ALPHAS = [0.6, 0.8, 1.0, 1.2]
L1_PCT = [0.25, 1, 4]
L2_PCT = [4, 8, 16]
BASE = (0.8, 1, 8)
BANDS = [(1, 100, "1〜100位"), (101, 1000, "101〜1,000位"), (1001, 10000, "1,001〜1万位"), (10001, N_ITEMS, "1万位より下")]
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def probs(n, a):
    p = 1.0 / np.arange(1, n + 1) ** a
    return p / p.sum()


def stream(rng, p, n):
    cdf = np.cumsum(p)
    cdf[-1] = 1.0
    return np.searchsorted(cdf, rng.random(n), side="right") + 1   # 人気の順位（1始まり）


def recent_flags(seq, cap):
    """1件ずつ当たったかどうか（いちばん長く使われていないものを捨てる）"""
    c = OrderedDict()
    out = np.zeros(len(seq), dtype=bool)
    for i, x in enumerate(seq.tolist()):
        if x in c:
            c.move_to_end(x)
            out[i] = True
        else:
            c[x] = None
            if len(c) > cap:
                c.popitem(last=False)
    return out


def two_level(seq, cap1, cap2, l1_hit=None):
    """1段目で外れたものだけが2段目に来る。戻り値：level（1=1段目で当たり、2=2段目で当たり、0=元のデータ）"""
    if l1_hit is None:
        l1_hit = recent_flags(seq, cap1)
    idx = np.where(~l1_hit)[0]
    l2_hit = recent_flags(seq[idx], cap2)
    level = np.zeros(len(seq), dtype=np.int8)
    level[l1_hit] = 1
    level[idx[l2_hit]] = 2
    return level


def summarize(level, alone_hit):
    m = level[WARM:]
    n = len(m)
    h1 = (m == 1).sum() / n
    to2 = (m != 1).sum()
    h2_local = (m == 2).sum() / to2
    h2_global = (m == 2).sum() / n
    total = (m != 0).sum() / n
    return {"l1_hit_pct": r(h1 * 100, 2), "l2_local_hit_pct": r(h2_local * 100, 2),
            "l2_share_of_all_pct": r(h2_global * 100, 2), "total_hit_pct": r(total * 100, 2),
            "alone_hit_pct": r(alone_hit * 100, 2),
            "total_miss_pct": r((1 - total) * 100, 2),
            "miss_product_pct": r((1 - h1) * (1 - h2_local) * 100, 2),
            "to_l2_share_pct": r(to2 / n * 100, 2)}


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"items": N_ITEMS, "warm": WARM, "measure": MEAS, "alphas": ALPHAS,
                       "l1_pct": L1_PCT, "l2_pct": L2_PCT, "base": {"alpha": BASE[0], "l1_pct": BASE[1], "l2_pct": BASE[2]}}}
    rows, keep = [], {}
    for a in ALPHAS:
        p = probs(N_ITEMS, a)
        seq = stream(rng, p, WARM + MEAS)
        alone = {}
        for s2 in L2_PCT:
            alone[s2] = recent_flags(seq, int(N_ITEMS * s2 / 100))[WARM:].mean()
        for s1 in L1_PCT:
            cap1 = int(N_ITEMS * s1 / 100)
            l1 = recent_flags(seq, cap1)
            for s2 in L2_PCT:
                lev = two_level(seq, cap1, int(N_ITEMS * s2 / 100), l1)
                d = {"alpha": a, "l1_pct": s1, "l2_pct": s2}
                d.update(summarize(lev, alone[s2]))
                rows.append(d)
                if (a, s1, s2) == BASE:
                    keep["seq"], keep["lev"] = seq, lev
        print(a, round(time.time() - T0, 1), flush=True)
    g = pd.DataFrame(rows)
    g["total_minus_alone_pt"] = (g.total_hit_pct - g.alone_hit_pct).round(2)
    g["alone_minus_local_pt"] = (g.alone_hit_pct - g.l2_local_hit_pct).round(2)
    g.to_csv(RES / "grid.csv", index=False)

    b = g[(g.alpha == BASE[0]) & (g.l1_pct == BASE[1]) & (g.l2_pct == BASE[2])].iloc[0].to_dict()
    b["l1_only_hit_pct"] = b["l1_hit_pct"]
    b["gain_by_l2_pt"] = r(b["total_hit_pct"] - b["l1_hit_pct"], 2)
    out["base"] = {k: (float(v) if not isinstance(v, str) else v) for k, v in b.items()}
    out["identity_check_max_abs_diff_pt"] = r((g.total_miss_pct - g.miss_product_pct).abs().max(), 2)

    # (2) 帯ごと（基本の置き方、測る区間）
    seq, lev = keep["seq"][WARM:], keep["lev"][WARM:]
    br = []
    n_all, n_to2 = len(seq), (lev != 1).sum()
    for lo, hi, name in BANDS:
        inb = (seq >= lo) & (seq <= hi)
        to2 = inb & (lev != 1)
        br.append({"band": name, "rank_from": lo, "rank_to": hi,
                   "share_of_all_pct": r(inb.sum() / n_all * 100, 2),
                   "share_of_l2_requests_pct": r(to2.sum() / n_to2 * 100, 2),
                   "l1_hit_in_band_pct": r((inb & (lev == 1)).sum() / inb.sum() * 100, 2),
                   "l2_local_hit_in_band_pct": r((to2 & (lev == 2)).sum() / max(to2.sum(), 1) * 100, 2)})
    br = pd.DataFrame(br)
    br.to_csv(RES / "bands_base.csv", index=False)
    out["bands_base"] = br.to_dict("records")

    # (3) 確かめのまとめ
    out["grid"] = {
        "n": len(g),
        "local_below_alone_count": int((g.l2_local_hit_pct < g.alone_hit_pct).sum()),
        "alone_minus_local_range_pt": [float(g.alone_minus_local_pt.min()), float(g.alone_minus_local_pt.max())],
        "l2_local_range_pct": [float(g.l2_local_hit_pct.min()), float(g.l2_local_hit_pct.max())],
        "total_minus_alone_range_pt": [float(g.total_minus_alone_pt.min()), float(g.total_minus_alone_pt.max())],
        "total_ge_alone_count": int((g.total_minus_alone_pt >= 0).sum()),
    }
    # 1段目を大きくすると：2段目の当たり率は下がり、全体は上がるか
    down, n_pair, ch_local, ch_total, ch_l1 = 0, 0, [], [], []
    for (a, s2), gg in g.groupby(["alpha", "l2_pct"]):
        gg = gg.sort_values("l1_pct")
        n_pair += 1
        down += int(np.all(np.diff(gg.l2_local_hit_pct.values) < 0))
        ch_local.append(gg.l2_local_hit_pct.values[-1] - gg.l2_local_hit_pct.values[0])
        ch_total.append(gg.total_hit_pct.values[-1] - gg.total_hit_pct.values[0])
        ch_l1.append(gg.l1_hit_pct.values[-1] - gg.l1_hit_pct.values[0])
    out["grid"]["l1_bigger_local_down_count"] = down
    out["grid"]["pairs"] = n_pair
    out["grid"]["l1_025_to_4_local_change_range_pt"] = [r(min(ch_local), 2), r(max(ch_local), 2)]
    out["grid"]["l1_025_to_4_total_change_range_pt"] = [r(min(ch_total), 2), r(max(ch_total), 2)]
    out["grid"]["l1_025_to_4_l1_change_range_pt"] = [r(min(ch_l1), 2), r(max(ch_l1), 2)]
    base_line = g[(g.alpha == 0.8) & (g.l2_pct == 8)].sort_values("l1_pct")
    out["grid"]["a08_l2_8_by_l1"] = base_line[["l1_pct", "l1_hit_pct", "l2_local_hit_pct", "total_hit_pct"]].to_dict("records")

    # データ：基本の置き方の先頭2万件（測る区間）
    pd.DataFrame({"request_id": np.arange(1, 20001), "item_rank": keep["seq"][WARM:WARM + 20000],
                  "served_by": keep["lev"][WARM:WARM + 20000]}).to_csv(DATA / "requests_base.csv", index=False)

    # 図1：基本の置き方の5つの値
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    names = ["1段目の\n当たり率", "2段目に来た\nうちの当たり率", "全体に対する\n2段目の当たり", "2段を合わせた\n当たり率", "2段目と同じ大きさを\n1段だけ置いたとき"]
    vals = [b["l1_hit_pct"], b["l2_local_hit_pct"], b["l2_share_of_all_pct"], b["total_hit_pct"], b["alone_hit_pct"]]
    cols = [GRAY, ORANGE, GRAY, BLUE, LIGHT]
    ax.bar(range(5), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.8, f"{v:.2f}%", ha="center", fontsize=9)
    ax.set_xticks(range(5), names, fontsize=8.5)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_ylabel("当たり率（%）")
    ax.set_title("1段目1%・2段目8%（偏り a=0.8、測った30万件）")
    save(fig, "a1158_base.png", SRC)

    # 図2：帯ごとの中身
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
    x = np.arange(len(br))
    w = 0.38
    axs[0].bar(x - w / 2, br.share_of_all_pct, w, color=GRAY, label="全体の問い合わせ")
    axs[0].bar(x + w / 2, br.share_of_l2_requests_pct, w, color=ORANGE, label="2段目に来た問い合わせ")
    for i in range(len(br)):
        axs[0].text(i - w / 2, br.share_of_all_pct[i] + 0.8, f"{br.share_of_all_pct[i]:.1f}", ha="center", fontsize=7.5)
        axs[0].text(i + w / 2, br.share_of_l2_requests_pct[i] + 0.8, f"{br.share_of_l2_requests_pct[i]:.1f}", ha="center", fontsize=7.5)
    axs[0].set_xticks(x, br.band, fontsize=8)
    axs[0].set_ylim(0, max(br.share_of_all_pct.max(), br.share_of_l2_requests_pct.max()) * 1.2)
    axs[0].set_ylabel("問い合わせの中の割合（%）")
    axs[0].set_title("人気の順位の帯ごとの割合", fontsize=11)
    axs[0].legend(frameon=False, fontsize=8)
    axs[1].bar(x, br.l2_local_hit_in_band_pct, color=ORANGE)
    for i, v in enumerate(br.l2_local_hit_in_band_pct):
        axs[1].text(i, v + 1.2, f"{v:.1f}%", ha="center", fontsize=8)
    axs[1].set_xticks(x, br.band, fontsize=8)
    axs[1].set_ylim(0, 105)
    axs[1].set_ylabel("2段目に来たうちの当たり率（%）")
    axs[1].set_title("帯ごとの2段目の当たり率", fontsize=11)
    fig.tight_layout()
    save(fig, "a1158_bands.png", SRC)

    # 図3：確かめ（2段目8%）
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True)
    cols = [GRAY, BLUE, ORANGE, INK]
    for a, col in zip(ALPHAS, cols):
        s = g[(g.alpha == a) & (g.l2_pct == 8)].sort_values("l1_pct")
        axs[0].plot(s.l1_pct, s.l2_local_hit_pct, marker="o", ms=4, color=col, label=f"偏り a={a:g}")
        axs[1].plot(s.l1_pct, s.total_hit_pct, marker="o", ms=4, color=col, label=f"偏り a={a:g}")
    for ax, t in zip(axs, ["2段目に来たうちの当たり率", "2段を合わせた当たり率"]):
        ax.set_xscale("log")
        ax.set_xticks(L1_PCT, [f"{v:g}%" for v in L1_PCT])
        ax.minorticks_off()
        ax.set_xlabel("1段目の大きさ（全体のデータの%）")
        ax.set_title(t, fontsize=11)
        ax.set_ylim(0, 100)
    axs[0].set_ylabel("当たり率（%）")
    axs[0].legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle("2段目は全体の8%（測った30万件）", fontsize=11)
    fig.tight_layout()
    save(fig, "a1158_grid.png", SRC)

    (RES / "a1158_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])
    print("sec", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
