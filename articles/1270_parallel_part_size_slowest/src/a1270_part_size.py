"""1270 分けた仕事の大きさがばらつくと、全体の時間はいちばん遅い1つでどれだけ延びるのか？（架空のデータ）

作成者が置いた架空のアプリの毎晩の集計。記録10万件が、2,000の店に分かれている。
店ごとの件数は右に長い乱数（対数のばらつき sg）で置き、合計を10万件にそろえる。
1件の処理は平均1ms・ばらつき（標準偏差÷平均）0.5。
店の処理時間＝件数×1ms＋記録ごとの散らばりの分（標準偏差0.5×√件数 ms の正規の乱数）と置く。
決まった量（10万件）を k 個（基本8個）に分けて同時に動かし、全部終わる時刻＝いちばん遅い1つの時間。
理想＝合計の時間÷k。延びた割合＝いちばん遅い1つ÷理想−1。
分け方：
  ① 件数で k 等分（店をまたいで切ってよい処理のとき）
  ② 店をまたがないように、店の番号順に件数がほぼ k 等分になる所で切る
  ③ 店をでたらめに k 組に分ける（店の数を同じにする）
  ④ 店の件数を見て、大きい店から順に、それまでの件数の合計がいちばん少ない組に入れる
  ⑤ ④と同じだが、使う件数が見込み（本当の件数に、対数で標準偏差0.3の外れを掛けたもの）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1270
SRC = "架空のアプリの毎晩の集計（作成者が置いた店ごとの件数と1件の処理時間からの乱数、seed 1270）"
NREC = 100000
REC_CV = 0.5
EMAX8 = 1.4236          # 8つの標準正規の乱数のいちばん大きい値の平均（式の目安に使う）
METHODS = ["m1_equal_records", "m2_cut_in_order", "m3_random_stores", "m4_largest_first", "m5_largest_first_est"]
LABELS = ["①件数で等分", "②店の順に切る", "③店をでたらめに", "④大きい店から", "⑤大きい店から（見込みの件数）"]


def make_sets(rng, R, G, sg):
    w = rng.lognormal(0, sg, (R, G))
    n = np.zeros((R, G), int)
    for r in range(R):
        n[r] = rng.multinomial(NREC, w[r] / w[r].sum())
    t = n * 1.0 + REC_CV * np.sqrt(n) * rng.standard_normal((R, G))
    t = np.maximum(t, 0)
    est = n * rng.lognormal(0, 0.3, (R, G))
    return n, t, est


def greedy(order_key, t, k):
    """大きい順に、それまでの合計（order_key の値で数える）がいちばん少ない組へ。t は実際の時間"""
    R, G = t.shape
    order = np.argsort(-order_key, 1)
    load_key = np.zeros((R, k)); load_t = np.zeros((R, k))
    assign = np.zeros((R, G), int)
    rr = np.arange(R)
    for g in range(G):
        idx = order[:, g]
        p = np.argmin(load_key, 1)
        load_key[rr, p] += order_key[rr, idx]
        load_t[rr, p] += t[rr, idx]
        assign[rr, idx] = p
    return load_t, assign


def part_times(rng, n, t, est, k):
    R, G = n.shape
    out, assign = {}, {}
    # ① 件数で等分：どの組も NREC/k 件。時間は件数×1ms＋散らばり
    m = NREC / k
    out["m1_equal_records"] = m + REC_CV * np.sqrt(m) * rng.standard_normal((R, k))
    # ② 店の番号順に切る（店の真ん中の位置で、どの組に入るか決める）
    cum = np.cumsum(n, 1) - n / 2
    a2 = np.minimum((cum / (NREC / k)).astype(int), k - 1)
    out["m2_cut_in_order"] = np.stack([np.where(a2 == p, t, 0).sum(1) for p in range(k)], 1)
    assign["m2_cut_in_order"] = a2
    # ③ 店をでたらめに k 組（店の数をそろえる）
    a3 = np.argsort(rng.random((R, G)), 1) % k
    out["m3_random_stores"] = np.stack([np.where(a3 == p, t, 0).sum(1) for p in range(k)], 1)
    assign["m3_random_stores"] = a3
    # ④ 本当の件数で大きい店から　⑤ 見込みの件数で大きい店から
    out["m4_largest_first"], assign["m4_largest_first"] = greedy(n.astype(float), t, k)
    out["m5_largest_first_est"], assign["m5_largest_first_est"] = greedy(est, t, k)
    return out, assign


def summarize(n, t, out, k):
    ideal = t.sum(1) / k
    lb = np.maximum(ideal, t.max(1)) / ideal - 1                     # いちばん大きい店1つでも延びる分
    res = {"lower_bound_ext_mean_pct": round(float(lb.mean()) * 100, 2),
           "largest_store_share_mean_pct": round(float((n.max(1) / NREC).mean()) * 100, 2)}
    for mth in METHODS:
        ext = out[mth].max(1) / ideal - 1
        idle = 1 - out[mth].mean(1) / out[mth].max(1)
        res[mth] = {"ext_mean_pct": round(float(ext.mean()) * 100, 2),
                    "ext_p10_pct": round(float(np.quantile(ext, 0.1)) * 100, 2),
                    "ext_p90_pct": round(float(np.quantile(ext, 0.9)) * 100, 2),
                    "idle_share_mean_pct": round(float(idle.mean()) * 100, 2),
                    "part_cv_mean": round(float((out[mth].std(1) / out[mth].mean(1)).mean()), 4)}
    return res


def main():
    t0 = time.time()
    R = 200

    # 基本：店2,000・件数の対数のばらつき1.0・8つに分ける（200回）
    n, t, est = make_sets(np.random.default_rng([SEED, 1]), R, 2000, 1.0)
    out, assign = part_times(np.random.default_rng([SEED, 2]), n, t, est, 8)
    base = summarize(n, t, out, 8)
    base["ideal_sec_mean"] = round(float((t.sum(1) / 8).mean()) / 1000, 3)
    base["total_sec_mean"] = round(float(t.sum(1).mean()) / 1000, 3)
    # ③の式の目安：組の時間のばらつき（標準偏差÷平均）×1.4236
    cv3 = out["m3_random_stores"].std(1, ddof=1) / out["m3_random_stores"].mean(1)
    base["m3_formula_guide_pct"] = round(float(np.sqrt((cv3 ** 2).mean())) * EMAX8 * 100, 2)
    cv1 = REC_CV / np.sqrt(NREC / 8)
    base["m1_formula_pct"] = round(cv1 * EMAX8 * 100, 2)

    # 1回分（data に置く）
    r0 = 0
    df = pd.DataFrame({"store": np.arange(2000), "records": n[r0], "time_ms": t[r0].round(2), "est_records": est[r0].round(1),
                       "part_m2": assign["m2_cut_in_order"][r0], "part_m3": assign["m3_random_stores"][r0],
                       "part_m4": assign["m4_largest_first"][r0], "part_m5": assign["m5_largest_first_est"][r0]})
    df.to_csv(DATA / "stores_one_set.csv", index=False)
    one = pd.DataFrame({mth: out[mth][r0] / 1000 for mth in METHODS})
    one.insert(0, "part", np.arange(1, 9))
    one.round(4).to_csv(RES / "one_set_part_times_sec.csv", index=False)
    base["one_set_ideal_sec"] = round(float(t[r0].sum() / 8 / 1000), 4)
    base["one_set_largest_store_sec"] = round(float(t[r0].max() / 1000), 4)
    base["one_set_max_sec"] = {mth: round(float(out[mth][r0].max() / 1000), 4) for mth in METHODS}

    rows = [{"method": LABELS[i], **{kk: v for kk, v in base[m].items()}} for i, m in enumerate(METHODS)]
    pd.DataFrame(rows).to_csv(RES / "base_by_method.csv", index=False)

    # 確かめ：件数のばらつき×店の数×分ける数（27通り、各200回）
    grid = []
    for sg in [0.5, 1.0, 1.5]:
        for G in [200, 2000, 20000]:
            if sg == 1.0 and G == 2000:          # 基本と同じ乱数（8つの行は基本の値と同じになる）
                ng, tg, eg = n, t, est
            else:
                ng, tg, eg = make_sets(np.random.default_rng([SEED, 3, int(sg * 10), G]), R, G, sg)
            for k in [4, 8, 16]:
                rs = [SEED, 2] if (sg == 1.0 and G == 2000 and k == 8) else [SEED, 4, int(sg * 10), G, k]
                og, _ = part_times(np.random.default_rng(rs), ng, tg, eg, k)
                sm = summarize(ng, tg, og, k)
                row = {"store_size_sd_log": sg, "stores": G, "parts": k,
                       "largest_store_share_pct": sm["largest_store_share_mean_pct"], "lower_bound_ext_pct": sm["lower_bound_ext_mean_pct"]}
                for mth in METHODS:
                    row[f"{mth}_ext_pct"] = sm[mth]["ext_mean_pct"]
                grid.append(row)
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    robust = {"settings": int(len(gr))}
    for mth in METHODS:
        robust[f"{mth}_range"] = [float(gr[f"{mth}_ext_pct"].min()), float(gr[f"{mth}_ext_pct"].max())]
    robust["m4_minus_lower_bound_max"] = round(float((gr.m4_largest_first_ext_pct - gr.lower_bound_ext_pct).max()), 3)
    robust["m5_ge_m4_count"] = int((gr.m5_largest_first_est_ext_pct >= gr.m4_largest_first_ext_pct).sum())
    robust["m4_lt_m3_count"] = int((gr.m4_largest_first_ext_pct < gr.m3_random_stores_ext_pct).sum())
    robust["m2_lt_m3_count"] = int((gr.m2_cut_in_order_ext_pct < gr.m3_random_stores_ext_pct).sum())
    robust["lower_bound_gt_10pct"] = gr[gr.lower_bound_ext_pct > 10][["store_size_sd_log", "stores", "parts", "lower_bound_ext_pct", "m4_largest_first_ext_pct"]].to_dict("records")
    robust["m3_by_stores"] = {str(G): [float(gr[gr.stores == G].m3_random_stores_ext_pct.min()), float(gr[gr.stores == G].m3_random_stores_ext_pct.max())] for G in [200, 2000, 20000]}
    robust["m2_by_stores"] = {str(G): [float(gr[gr.stores == G].m2_cut_in_order_ext_pct.min()), float(gr[gr.stores == G].m2_cut_in_order_ext_pct.max())] for G in [200, 2000, 20000]}
    robust["m3_by_parts"] = {str(k): [float(gr[gr.parts == k].m3_random_stores_ext_pct.min()), float(gr[gr.parts == k].m3_random_stores_ext_pct.max())] for k in [4, 8, 16]}

    out_json = {"base": base, "robust": robust,
                "setup": {"records": NREC, "stores": 2000, "store_size_sd_log": 1.0, "record_ms_mean": 1.0, "record_cv": REC_CV,
                          "parts": 8, "est_error_sd_log": 0.3, "reps": R, "emax8_normal": EMAX8}}
    json.dump(out_json, open(RES / "a1270_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の8つの組の時間（秒）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    x = np.arange(8)
    cols = [LIGHT, ORANGE, INK, BLUE, GREEN]
    for i, mth in enumerate(METHODS[:4]):
        ax.bar(x + (i - 1.5) * 0.2, one[mth], 0.2, color=cols[i], label=LABELS[i])
    ax.axhline(base["one_set_ideal_sec"], color=GRAY, lw=1, ls="--")
    ax.text(7.6, base["one_set_ideal_sec"] + 0.25, f"理想（合計÷8）{base['one_set_ideal_sec']:.2f}秒", ha="right", fontsize=8.5, color=INK,
            bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xticks(x); ax.set_xticklabels([f"{i+1}つ目" for i in x])
    ax.set_ylim(0, float(one[METHODS[:4]].max().max()) * 1.25); ax.set_ylabel("組の処理時間（秒）")
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax.set_title("同じ10万件でも、分け方で8つの組の時間がそろわない（1回分）", fontsize=12)
    save(fig, "a1270_one_set.png", SRC, y=-0.16)

    # 図2：基本の置き方で、分け方ごとの延びた割合（200回の平均と10〜90%）
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    xm = np.arange(len(METHODS))
    means = [base[m]["ext_mean_pct"] for m in METHODS]
    lo = [base[m]["ext_mean_pct"] - base[m]["ext_p10_pct"] for m in METHODS]
    hi = [base[m]["ext_p90_pct"] - base[m]["ext_mean_pct"] for m in METHODS]
    ax.bar(xm, means, 0.6, color=BLUE)
    ax.errorbar(xm, means, yerr=[lo, hi], fmt="none", ecolor=INK, capsize=4, lw=1)
    for i, v in enumerate(means):
        ax.text(i + 0.33, v, f"{v:.2f}%", va="center", fontsize=9)
    ax.set_xticks(xm); ax.set_xticklabels([l.replace("（", "\n（") for l in LABELS], fontsize=9.5)
    ax.set_ylim(0, max(base[m]["ext_p90_pct"] for m in METHODS) * 1.15)
    ax.set_ylabel("理想より延びた割合（%、平均と10〜90%）")
    ax.set_title("8つに分けたとき、いちばん遅い1つで延びた割合（店2,000・200回）", fontsize=12)
    save(fig, "a1270_by_method.png", SRC)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    gx = np.arange(len(gr))
    for i, mth in enumerate(METHODS):
        ax.plot(gx, gr[f"{mth}_ext_pct"], marker="o", ms=3.5, lw=0.9, color=cols[i], label=LABELS[i])
    ax.plot(gx, gr.lower_bound_ext_pct, ls="none", marker="_", ms=9, color=GRAY, label="いちばん大きい店1つで決まる下限")
    for kk in [9, 18]:
        ax.axvline(kk - 0.5, color=GRAY, lw=0.8, ls=":")
    ax.set_yscale("symlog", linthresh=1)
    ymax = float(gr[[f"{m}_ext_pct" for m in METHODS]].max().max())
    for kk, sg in enumerate([0.5, 1.0, 1.5]):
        ax.text(kk * 9 + 4, ymax * 1.6, f"店の件数のばらつき{sg}", ha="center", fontsize=8.5)
    ax.set_ylim(0, ymax * 3)
    tk = [0, 0.5, 1, 2, 5, 10, 20, 50, 100, 200]
    ax.set_yticks(tk); ax.set_yticklabels([f"{v:g}" for v in tk]); ax.minorticks_off()
    ax.set_xticks(gx); ax.set_xticklabels([f"{g}" for g in gr.stores], fontsize=6, rotation=90)
    ax.set_xlabel("27通り（下の数字は店の数。同じ店の数の中は4・8・16に分ける順）", fontsize=8.5)
    ax.set_ylabel("理想より延びた割合（%、各200回の平均、0〜1は等間隔・その上は対数）", fontsize=8)
    ax.legend(frameon=False, fontsize=7.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.24))
    ax.set_title("店が少なく、分ける数が多いほど延び、大きい店1つが下限を決める", fontsize=11.5)
    save(fig, "a1270_grid.png", SRC, y=-0.3)
    print(json.dumps(out_json, ensure_ascii=False, indent=1))
    print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
