"""1302 切るときの刃の幅（切りしろ）を入れずに計算すると、1本の棒から取れる部品の数の見込みはどれだけ多く出るのか？（架空のデータ）

作成者が置いた架空の通販の工房。長さ2,000mmの棒から、棚の部品を切り出して発送する。
1回切るごとに刃の幅（切りしろ）3mmが粉になって消えると置く。棒の両端はそろっていて、端を切りそろえる必要はないと置く。
n 個の部品が1本から取れるのは「部品の長さの合計＋（n−1）×切りしろ ≦ 棒の長さ」のとき（最後の部品は棒の端を使う）。
(1) 1種類の長さ（50〜1,000mm、1mm刻み）だけを切るとき、「棒の長さ÷部品の長さ」の切り捨てと、切りしろを入れた本当の個数を比べる（式どおり）
(2) 1日の注文（8種類の長さがまざる）を、長い順に並べてから入る最初の棒に割り当てる詰め方で、切りしろなしで計画し、
    その計画に切りしろを入れると何本が足りなくなるか、切りしろを入れて計画し直すと棒は何本要るかを、500日分数える
(3) 確かめ：切りしろ1・2・3・5mm×部品の長さのまざり方3通り（各300日）、棒の端を1回切りそろえる置き方
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1302
SRC = "架空の棒と部品の注文（作成者が置いた長さ・切りしろ・注文の数からの乱数、seed 1302）"
ROD = 2000
KERF = 3
DAYS = 500
GRID_DAYS = 300
MIXES = {
    "短め（80〜300mm）": [80, 110, 140, 170, 200, 230, 260, 300],
    "基本（150〜760mm）": [150, 240, 300, 380, 450, 520, 600, 760],
    "長め（400〜1,000mm）": [400, 480, 550, 620, 700, 780, 870, 1000],
}
BASE_MIX = "基本（150〜760mm）"
MEAN_QTY = 12   # 1種類あたりの1日の注文の数の平均（ポアソン）
KERFS = [1, 2, 3, 5]


def r(x, d=4):
    return round(float(x), d)


def single_counts(lengths, rod, kerf, trim=0):
    """1種類だけ切るときの見込み（切りしろなし）と本当の個数。trim は端を切りそろえる回数"""
    est = rod // lengths
    real = (rod - trim * kerf + kerf) // (lengths + kerf)
    return est, real


def pack_sorted_first(parts, cap):
    """長い順に並べてから、入る最初の棒に入れる。棒ごとの残りと、棒ごとの部品のリストを返す"""
    order = sorted(parts, reverse=True)
    rest, rods = [], []
    for p in order:
        for i, rr in enumerate(rest):
            if p <= rr:
                rest[i] = rr - p
                rods[i].append(p)
                break
        else:
            rest.append(cap - p)
            rods.append([p])
    return rods


def day_parts(rng, mix):
    q = rng.poisson(MEAN_QTY, len(mix))
    return [l for l, k in zip(mix, q) for _ in range(k)]


def one_day(parts, rod, kerf, trim=0):
    """切りしろなしの計画と、切りしろを入れた計画を比べる"""
    plan0 = pack_sorted_first(parts, rod)
    bad, dropped = 0, 0
    exact = sum(1 for rp in plan0 if sum(rp) == rod)
    room = rod - trim * kerf
    for rp in plan0:
        need = sum(rp) + (len(rp) - 1 + trim) * kerf
        if need > rod:
            bad += 1
            rp2 = sorted(rp)
            while sum(rp2) + (len(rp2) - 1 + trim) * kerf > rod:
                rp2.pop(0)   # 短い部品から1つずつあきらめる
                dropped += 1
    # 切りしろを入れた計画：部品は長さ＋切りしろ、棒は長さ−端の切りそろえ＋切りしろ
    plan1 = pack_sorted_first([p + kerf for p in parts], room + kerf)
    return {"parts": len(parts), "rods_no_kerf": len(plan0), "rods_with_kerf": len(plan1),
            "plan_rods_short": bad, "plan_parts_dropped": dropped, "plan_rods_exact": exact}


def main():
    t0 = time.time()
    out = {"setting": {"rod_mm": ROD, "kerf_mm": KERF, "days": DAYS, "grid_days": GRID_DAYS,
                       "mean_qty_per_type": MEAN_QTY, "mixes_mm": MIXES, "seed": SEED}}
    # (1) 1種類の長さ
    L = np.arange(50, 1001)
    est, real = single_counts(L, ROD, KERF)
    s = pd.DataFrame({"length_mm": L, "estimate_no_kerf": est, "real_with_kerf": real})
    s["over_pieces"] = s.estimate_no_kerf - s.real_with_kerf
    s["over_pct_of_real"] = np.round(s.over_pieces / s.real_with_kerf * 100, 2)
    s.to_csv(RES / "single_length.csv", index=False)
    bands = []
    for lo, hi in [(50, 99), (100, 199), (200, 499), (500, 1000)]:
        b = s[(s.length_mm >= lo) & (s.length_mm <= hi)]
        bands.append({"band_mm": f"{lo}〜{hi}", "lengths": len(b), "share_over_pct": r((b.over_pieces > 0).mean() * 100, 2),
                      "max_over_pieces": int(b.over_pieces.max()), "max_over_pct": r(b.over_pct_of_real.max(), 2),
                      "mean_over_pct": r(b.over_pct_of_real.mean(), 2)})
    out["single_bands"] = bands
    out["single_all"] = {"lengths": len(s), "share_over_pct": r((s.over_pieces > 0).mean() * 100, 2),
                         "max_over_pieces": int(s.over_pieces.max())}
    dv = s[ROD % s.length_mm == 0]
    out["single_divisors"] = {"lengths": dv.length_mm.tolist(), "share_over_pct": r((dv.over_pieces > 0).mean() * 100, 2),
                              "over_pieces": dv.over_pieces.tolist()}
    nd = s[ROD % s.length_mm != 0]
    out["single_non_divisors"] = {"lengths": len(nd), "share_over_pct": r((nd.over_pieces > 0).mean() * 100, 2)}
    picks = [50, 80, 100, 125, 200, 250, 400, 500, 664, 666, 1000]
    out["single_picks"] = s[s.length_mm.isin(picks)].to_dict("records")
    # 端を1回切りそろえる置き方
    _e, real_t = single_counts(L, ROD, KERF, trim=1)
    out["single_trim1"] = {"share_over_pct": r(((est - real_t) > 0).mean() * 100, 2),
                           "max_over_pieces": int((est - real_t).max()),
                           "picks": {int(l): {"estimate": int(e), "real": int(t)} for l, e, t in zip(L, est, real_t) if l in picks}}

    # (2) 1日の注文（基本のまざり方）
    rng = np.random.default_rng(SEED)
    rows = []
    for d in range(DAYS):
        parts = day_parts(rng, MIXES[BASE_MIX])
        o = one_day(parts, ROD, KERF)
        o["day"] = d + 1
        rows.append(o)
    days = pd.DataFrame(rows)[["day", "parts", "rods_no_kerf", "rods_with_kerf", "plan_rods_short", "plan_parts_dropped"]]
    days.to_csv(DATA / "days_base.csv", index=False)
    pp0 = days.parts / days.rods_no_kerf
    pp1 = days.parts / days.rods_with_kerf
    out["base_days"] = {
        "parts_mean": r(days.parts.mean(), 2),
        "rods_no_kerf_mean": r(days.rods_no_kerf.mean(), 3), "rods_with_kerf_mean": r(days.rods_with_kerf.mean(), 3),
        "extra_rods_mean": r((days.rods_with_kerf - days.rods_no_kerf).mean(), 3),
        "extra_rods_pct": r((days.rods_with_kerf.sum() / days.rods_no_kerf.sum() - 1) * 100, 2),
        "extra_rods_min": int((days.rods_with_kerf - days.rods_no_kerf).min()),
        "extra_rods_max": int((days.rods_with_kerf - days.rods_no_kerf).max()),
        "days_extra_ge1_pct": r(((days.rods_with_kerf - days.rods_no_kerf) >= 1).mean() * 100, 2),
        "pieces_per_rod_no_kerf": r(days.parts.sum() / days.rods_no_kerf.sum(), 3),
        "pieces_per_rod_with_kerf": r(days.parts.sum() / days.rods_with_kerf.sum(), 3),
        "pieces_per_rod_over_pct": r((days.parts.sum() / days.rods_no_kerf.sum()) / (days.parts.sum() / days.rods_with_kerf.sum()) * 100 - 100, 2),
        "plan_rods_short_mean": r(days.plan_rods_short.mean(), 3),
        "plan_rods_short_share_pct": r(days.plan_rods_short.sum() / days.rods_no_kerf.sum() * 100, 2),
        "plan_parts_dropped_mean": r(days.plan_parts_dropped.mean(), 3),
        "plan_parts_dropped_share_pct": r(days.plan_parts_dropped.sum() / days.parts.sum() * 100, 2),
        "pp_day_no_kerf_mean": r(pp0.mean(), 3), "pp_day_with_kerf_mean": r(pp1.mean(), 3),
    }
    # 端を1回切りそろえる置き方（同じ500日の注文で）
    rng_t = np.random.default_rng(SEED)
    tr = []
    for d in range(DAYS):
        parts = day_parts(rng_t, MIXES[BASE_MIX])
        tr.append(one_day(parts, ROD, KERF, trim=1))
    tr = pd.DataFrame(tr)
    out["base_days_trim1"] = {
        "extra_rods_pct": r((tr.rods_with_kerf.sum() / tr.rods_no_kerf.sum() - 1) * 100, 2),
        "plan_rods_short_share_pct": r(tr.plan_rods_short.sum() / tr.rods_no_kerf.sum() * 100, 2),
        "plan_parts_dropped_share_pct": r(tr.plan_parts_dropped.sum() / tr.parts.sum() * 100, 2)}

    # (3) 確かめ：切りしろ×まざり方
    g = []
    for mi, (mname, mix) in enumerate(MIXES.items()):
        for k in KERFS:
            g_rng = np.random.default_rng([SEED, mi, k])
            rr = [one_day(day_parts(g_rng, mix), ROD, k) for _ in range(GRID_DAYS)]
            rr = pd.DataFrame(rr)
            g.append({"mix": mname, "kerf_mm": k, "parts_mean": r(rr.parts.mean(), 2),
                      "rods_no_kerf_mean": r(rr.rods_no_kerf.mean(), 3), "rods_with_kerf_mean": r(rr.rods_with_kerf.mean(), 3),
                      "extra_rods_pct": r((rr.rods_with_kerf.sum() / rr.rods_no_kerf.sum() - 1) * 100, 2),
                      "days_extra_ge1_pct": r(((rr.rods_with_kerf - rr.rods_no_kerf) >= 1).mean() * 100, 2),
                      "plan_rods_short_share_pct": r(rr.plan_rods_short.sum() / rr.rods_no_kerf.sum() * 100, 2),
                      "plan_parts_dropped_share_pct": r(rr.plan_parts_dropped.sum() / rr.parts.sum() * 100, 2),
                      "plan_rods_exact_share_pct": r(rr.plan_rods_exact.sum() / rr.rods_no_kerf.sum() * 100, 2)})
    gr = pd.DataFrame(g)
    gr.to_csv(RES / "grid.csv", index=False)
    out["grid_summary"] = {"n": len(gr), "extra_rods_pct_min": r(gr.extra_rods_pct.min(), 2),
                           "extra_rods_pct_max": r(gr.extra_rods_pct.max(), 2),
                           "short_share_min": r(gr.plan_rods_short_share_pct.min(), 2),
                           "short_share_max": r(gr.plan_rods_short_share_pct.max(), 2)}

    # 図1：1種類の長さ
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.vlines(s.length_mm, 0, s.over_pct_of_real, color=BLUE, lw=1.0)   # 1mm刻みの長さごとに1本の線（0の長さは線なし）
    ax.set_xlim(40, 1010)
    ax.set_ylim(0, s.over_pct_of_real.max() * 1.1)
    ax.set_xlabel("部品の長さ（mm）")
    ax.set_ylabel("見込みが本当より多い分（%）")
    ax.set_title("1種類だけ切るとき、切りしろなしの見込みの多すぎ（棒2,000mm・切りしろ3mm）")
    ax.grid(axis="y", color="#e6e6e6")
    save(fig, "a1302_single.png", SRC)

    # 図2：切りしろなしの計画のうち、切りしろを入れると切り出せない棒の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cols = [ORANGE, BLUE, GREEN]
    w = 0.25
    for i, (mname, c) in enumerate(zip(MIXES, cols)):
        sub = gr[gr["mix"] == mname]
        x = np.arange(len(KERFS)) + (i - 1) * w
        ax.bar(x, sub.plan_rods_short_share_pct, width=w, color=c, label=mname)
    ax.set_xticks(np.arange(len(KERFS)), [f"切りしろ{k}mm" for k in KERFS])
    ax.set_ylim(0, 100)
    ax.set_ylabel("計画どおりに切れない棒（%）")
    ax.set_title("切りしろなしで立てた計画のうち、切りしろを入れると切れない棒")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1302_plan_short.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cols = [ORANGE, BLUE, GREEN]
    w = 0.25
    for i, (mname, c) in enumerate(zip(MIXES, cols)):
        sub = gr[gr["mix"] == mname]
        x = np.arange(len(KERFS)) + (i - 1) * w
        ax.bar(x, sub.extra_rods_pct, width=w, color=c, label=mname)
    ax.set_xticks(np.arange(len(KERFS)), [f"切りしろ{k}mm" for k in KERFS])
    ax.set_ylim(0, gr.extra_rods_pct.max() * 1.15)
    ax.set_ylabel("切りしろを入れると増える棒（%）")
    ax.set_title("切りしろと部品の長さで、増える棒の割合（各300日）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1302_grid.png", SRC)

    (RES / "a1302_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
