"""1288 部品を測って大きいものどうし・小さいものどうしを組み合わせて組むと、外れる組み立て品は減っても、相手がなくて余る部品はどれだけ出るのか？（架空のデータ）

架空の箱とふた。すきま＝ふたの内のり−箱の外のり。すきまの許容は0.10〜0.30mm。
箱の外のりの名目200.00mm、ふたの内のりの名目200.20mm（すきまの名目0.20mm）。
組み方：
  でたらめ：測らずに組む
  同じ幅の区分：箱・ふたをそれぞれ名目からのずれで、同じ幅（mm）の区分に分け、同じ番号の区分どうしで組む。
                区分の中の数が合わないと、相手がなくて余る
  ばらつきに合わせた幅の区分：ふたの区分の幅を、置いたばらつきの比（ふた÷箱）の倍にして、同じ番号どうしで組む
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1288
SRC = "架空の箱とふたの寸法（作成者が乱数で作成、seed 1288）"
NOM_GAP = 0.20
LO, HI = 0.10, 0.30
SD_BOX = 0.04
SD_LIDS = [0.04, 0.06, 0.08]
BASE_SD_LID = 0.06
OFFSETS = [0.0, 0.03]          # ふたの平均の名目からのずれ（mm）
GS = [2, 3, 4, 6, 8]
BASE_G = 4
W = 0.24                       # 区分を置く範囲（名目±0.12mm、外は端の区分に入れる）
LOTS = [100, 1000]
BASE_LOT = 1000
N_REP = 1000


def ncdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def bins(dev, g):
    return np.clip(np.floor((dev + W / 2) / (W / g)).astype(int), 0, g - 1)


def one_lot(rng, n, sd_lid, off, g):
    b = rng.normal(0, SD_BOX, n)
    l = rng.normal(off, sd_lid, n)
    # でたらめ
    gap_r = NOM_GAP + l - b
    # ばらつきに合わせた幅の区分（ふたの区分の幅を、ばらつきの比 sd_lid÷SD_BOX 倍に広げる）
    pb_, pl_ = bins(b, g), bins(l * SD_BOX / sd_lid, g)
    gq_list, left_q = [], 0
    for k in range(g):
        xb, xl = b[pb_ == k], l[pl_ == k]
        m = min(len(xb), len(xl))
        if m:
            gq_list.append(NOM_GAP + xl[:m] - xb[:m])
    gap_q = np.concatenate(gq_list) if gq_list else np.zeros(0)
    # 同じ幅の区分
    bb, lb = bins(b, g), bins(l, g)
    gaps = []
    for k in range(g):
        xb, xl = b[bb == k], l[lb == k]
        m = min(len(xb), len(xl))
        if m:
            gaps.append(NOM_GAP + xl[:m] - xb[:m])
    gap_s = np.concatenate(gaps) if gaps else np.zeros(0)
    left_box = n - len(gap_s)
    return gap_r, gap_q, gap_s, left_box, n - len(gap_q), b, l, bb, lb


def out(x):
    return ((x < LO) | (x > HI))


def run_setting(rng, n, sd_lid, off, g, reps):
    rr, rq, rs, left, leftq, good_r, good_s, good_q = [], [], [], [], [], [], [], []
    for _ in range(reps):
        gr, gq, gs, lb_, lq_, *_ = one_lot(rng, n, sd_lid, off, g)
        rr.append(out(gr).mean()); rq.append(out(gq).mean()); leftq.append(lq_ / n)
        rs.append(out(gs).mean() if len(gs) else np.nan)
        left.append(lb_ / n)
        good_r.append((~out(gr)).sum() / n); good_s.append((~out(gs)).sum() / n); good_q.append((~out(gq)).sum() / n)
    f = lambda a: round(float(np.nanmean(a) * 100), 2)
    return {"n_per_lot": n, "sd_lid": sd_lid, "lid_offset": off, "groups": g,
            "random_out_pct": f(rr), "random_out_formula_pct": round(
                (ncdf((LO - NOM_GAP - off) / math.hypot(SD_BOX, sd_lid))
                 + 1 - ncdf((HI - NOM_GAP - off) / math.hypot(SD_BOX, sd_lid))) * 100, 2),
            "select_out_pct": f(rs), "select_leftover_pct": f(left),
            "select_leftover_p90_pct": round(float(np.quantile(left, 0.9) * 100), 2),
            "prop_out_pct": f(rq), "prop_leftover_pct": f(leftq),
            "good_per_100_random": f(good_r), "good_per_100_select": f(good_s), "good_per_100_prop": f(good_q)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    for n in LOTS:
        for sd_lid in SD_LIDS:
            for off in OFFSETS:
                for g in GS:
                    rows.append(run_setting(rng, n, sd_lid, off, g, N_REP if n == 100 else N_REP // 2))
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # 1回分の組（基本の置き方）を data に
    gr, gq, gs, lb_, lq_, b, l, bb, lb = one_lot(rng, BASE_LOT, BASE_SD_LID, 0.0, BASE_G)
    pd.DataFrame({"no": np.arange(1, BASE_LOT + 1), "box_mm": np.round(200.0 + b, 4), "box_group": bb + 1,
                  "lid_mm": np.round(200.0 + NOM_GAP + l, 4), "lid_group": lb + 1}).to_csv(
        DATA / "parts_base_one_lot.csv", index=False)
    cnt = pd.DataFrame({"group": np.arange(1, BASE_G + 1),
                        "box_count": np.bincount(bb, minlength=BASE_G),
                        "lid_count": np.bincount(lb, minlength=BASE_G)})
    cnt["paired"] = np.minimum(cnt.box_count, cnt.lid_count)
    cnt["left_box"] = cnt.box_count - cnt.paired
    cnt["left_lid"] = cnt.lid_count - cnt.paired
    # 式：正規分布での区分ごとの割合
    edges = [-np.inf] + [-W / 2 + k * W / BASE_G for k in range(1, BASE_G)] + [np.inf]
    pb = [ncdf(edges[k + 1] / SD_BOX) - ncdf(edges[k] / SD_BOX) for k in range(BASE_G)]
    pl = [ncdf(edges[k + 1] / BASE_SD_LID) - ncdf(edges[k] / BASE_SD_LID) for k in range(BASE_G)]
    cnt["box_share_formula_pct"] = np.round(np.array(pb) * 100, 2)
    cnt["lid_share_formula_pct"] = np.round(np.array(pl) * 100, 2)
    cnt.to_csv(RES / "groups_base_one_lot.csv", index=False)
    left_formula = sum(abs(a - c) for a, c in zip(pb, pl)) / 2 * 100   # 箱1個あたりの余る割合（式）

    def pick(n=BASE_LOT, sd=BASE_SD_LID, off=0.0, g=BASE_G):
        r = grid[(grid.n_per_lot == n) & (grid.sd_lid == sd) & (grid.lid_offset == off) & (grid.groups == g)]
        return r.iloc[0].to_dict()

    base = pick()
    eq = pick(sd=0.04)
    g = grid
    main_json = {
        "setting": {"sd_box": SD_BOX, "sd_lid_base": BASE_SD_LID, "gap_spec": [LO, HI], "nominal_gap": NOM_GAP,
                    "group_range_mm": W, "base_groups": BASE_G, "base_lot": BASE_LOT,
                    "reps_lot100": N_REP, "reps_lot1000": N_REP // 2},
        "base": base,
        "base_leftover_formula_pct": round(left_formula, 2),
        "equal_sd_base": eq,
        "base_by_groups": [pick(g=k) for k in GS],
        "range": {
            "n_settings": int(len(g)),
            "select_out_lt_random_count": int((g.select_out_pct < g.random_out_pct).sum()),
            "select_leftover_min": float(g.select_leftover_pct.min()), "select_leftover_max": float(g.select_leftover_pct.max()),
            "select_good_lt_random_count": int((g.good_per_100_select < g.good_per_100_random).sum()),
            "prop_out_lt_random_count": int((g.prop_out_pct < g.random_out_pct).sum()),
            "prop_good_gt_select_count": int((g.good_per_100_prop > g.good_per_100_select).sum()),
            "prop_leftover_min": float(g.prop_leftover_pct.min()), "prop_leftover_max": float(g.prop_leftover_pct.max()),
            "prop_out_min": float(g.prop_out_pct.min()), "prop_out_max": float(g.prop_out_pct.max()),
            "select_out_min": float(g.select_out_pct.min()), "select_out_max": float(g.select_out_pct.max()),
            "unequal_select_leftover_min": float(g[g.sd_lid > SD_BOX].select_leftover_pct.min()),
            "unequal_select_leftover_max": float(g[g.sd_lid > SD_BOX].select_leftover_pct.max()),
            "equal_select_leftover_min": float(g[(g.sd_lid == SD_BOX) & (g.lid_offset == 0)].select_leftover_pct.min()),
            "equal_select_leftover_max": float(g[(g.sd_lid == SD_BOX) & (g.lid_offset == 0)].select_leftover_pct.max()),
            "random_out_minus_formula_maxabs": round(float((g.random_out_pct - g.random_out_formula_pct).abs().max()), 2),
        },
    }
    with open(RES / "a1288_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)

    # 図1：区分の数ごと（基本：ふた0.06mm・ずれなし・1,000組）外れの割合と余る割合
    d = pd.DataFrame(main_json["base_by_groups"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    x = np.arange(len(d))
    ax = axes[0]
    ax.bar(x - 0.27, d.random_out_pct, 0.27, color=GRAY, label="でたらめに組む")
    ax.bar(x, d.select_out_pct, 0.27, color=BLUE, label="同じ幅の区分どうし")
    ax.bar(x + 0.27, d.prop_out_pct, 0.27, color=GREEN, label="ばらつきに合わせた幅の区分どうし")
    for i, (a, v, w) in enumerate(zip(d.random_out_pct, d.select_out_pct, d.prop_out_pct)):
        ax.text(i - 0.27, a + 0.3, f"{a:.2f}", ha="center", fontsize=7.5)
        ax.text(i, v + 0.3, f"{v:.2f}", ha="center", fontsize=7.5, color=BLUE)
        ax.text(i + 0.27, w + 1.3, f"{w:.2f}", ha="center", fontsize=7.5, color=GREEN)
    ax.set_xticks(x); ax.set_xticklabels([f"{int(k)}区分" for k in d.groups])
    ax.set_ylabel("組んだもののうち、すきまが外れる割合（%）")
    ax.set_title("外れる割合", fontsize=12)
    ax.set_ylim(0, d.random_out_pct.max() * 1.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax = axes[1]
    ax.bar(x - 0.2, d.select_leftover_pct, 0.4, color=BLUE, label="同じ幅の区分どうし")
    ax.bar(x + 0.2, d.prop_leftover_pct, 0.4, color=GREEN, label="ばらつきに合わせた幅の区分どうし")
    for i, (v, w) in enumerate(zip(d.select_leftover_pct, d.prop_leftover_pct)):
        ax.text(i - 0.2, v + 0.3, f"{v:.2f}", ha="center", fontsize=8.5)
        ax.text(i + 0.2, w + 0.3, f"{w:.2f}", ha="center", fontsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_xticks(x); ax.set_xticklabels([f"{int(k)}区分" for k in d.groups])
    ax.set_ylabel("相手がなくて余る箱の割合（%）")
    ax.set_title("相手がなくて余る箱", fontsize=12)
    ax.set_ylim(0, d.select_leftover_pct.max() * 1.3)
    fig.suptitle("箱0.04mm・ふた0.06mm（ばらつきが違う）、1,000組ずつ", fontsize=12)
    save(fig, "a1288_groups.png", SRC, y=-0.03)

    # 図2：1回分の区分ごとの数（基本の4区分）
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    x = np.arange(BASE_G)
    ax.bar(x - 0.2, cnt.box_count, 0.4, color=BLUE, label="箱")
    ax.bar(x + 0.2, cnt.lid_count, 0.4, color=ORANGE, label="ふた")
    for i, (a, c) in enumerate(zip(cnt.box_count, cnt.lid_count)):
        ax.text(i - 0.2, a + 5, str(a), ha="center", fontsize=9)
        ax.text(i + 0.2, c + 5, str(c), ha="center", fontsize=9)
    labs = ["〜−0.06mm", "−0.06〜0mm", "0〜+0.06mm", "+0.06mm〜"]
    ax.set_xticks(x); ax.set_xticklabels([f"区分{k + 1}\n{labs[k]}" for k in range(BASE_G)])
    ax.set_ylabel("個数（1,000個のうち）")
    ax.set_xlabel("名目からのずれで分けた区分")
    ax.set_ylim(0, max(cnt.box_count.max(), cnt.lid_count.max()) * 1.2)
    ax.legend(frameon=False)
    ax.set_title("ばらつきの大きいふたは端の区分に多く、箱は真ん中に多い（1回分）", fontsize=11)
    save(fig, "a1288_group_counts.png", SRC, y=-0.04)

    # 図3：置き方ごと（1,000組、4区分）の外れと余り
    d = g[(g.n_per_lot == BASE_LOT) & (g.groups == BASE_G)].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(d))
    ax.bar(x - 0.27, d.random_out_pct, 0.27, color=GRAY, label="でたらめ：外れる割合")
    ax.bar(x, d.select_out_pct, 0.27, color=BLUE, label="同じ幅の区分：外れる割合")
    ax.bar(x + 0.27, d.select_leftover_pct, 0.27, color=ORANGE, label="同じ幅の区分：余る箱の割合")
    for i in range(len(d)):
        for dx, v in [(-0.27, d.random_out_pct[i]), (0, d.select_out_pct[i]), (0.27, d.select_leftover_pct[i])]:
            ax.text(i + dx, v + 0.3, f"{v:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"ふた{s:.2f}mm\n平均ずれ{o:+.2f}" for s, o in zip(d.sd_lid, d.lid_offset)], fontsize=9)
    ax.set_ylabel("割合（%）")
    ax.set_ylim(0, max(d.random_out_pct.max(), d.select_leftover_pct.max()) * 1.2)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("ふたのばらつき・平均のずれを変えると（4区分、1,000組ずつ）", fontsize=12)
    save(fig, "a1288_settings.png", SRC, y=-0.04)

    print(json.dumps(main_json, ensure_ascii=False, indent=1)[:4000])
    print(f"{time.time() - t0:.1f} 秒")


if __name__ == "__main__":
    main()
