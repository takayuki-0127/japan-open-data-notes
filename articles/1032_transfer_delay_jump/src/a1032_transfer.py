"""1032 乗り換え1回で、全体の遅れはどう増えるのか？（架空のデータ）

架空の通勤。家の駅から路線1で乗り換え駅へ行き、路線2に乗りかえて会社の駅へ向かう。
路線2は決まった間隔（基本10分おき）で出る。計画では、路線1の時刻どおりの着から
歩く時間（3分）＋乗り換えの余裕（基本2分）のあとに出る路線2の便に乗る。
1本目が余裕より多く遅れると、計画の便に乗れず次の便になり、遅れが間隔の分だけ跳ぶ。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1032
SRC = "架空の通勤の遅れ（作成者が乱数で作成、seed 1032）"
BASE = dict(p1=0.35, m1=3.0, p2=0.25, m2=2.0, walk=3.0, buf=2.0, H=10.0, k=0.0)


def delays(rng, shape, p, m):
    """遅れ（分）：確率 p で遅れ、遅れる日は平均 m 分の指数分布。遅れない日は0分"""
    late = rng.random(shape) < p
    return np.where(late, rng.exponential(m, shape), 0.0)


def transfer(rng, arr, p, m, walk, buf, H, k=0.0):
    """乗り換え駅に arr 分遅れて着いた人が、次の路線で計画より何分遅れて出るか。
    次の路線の便は、計画の便を0として j*H 分おき（j=-3〜）。便の遅れは乱数＋k×arr（共通の遅れ）"""
    n = len(arr)
    J = int(np.ceil((arr.max() + 60) / H)) + 3
    js = np.arange(-3, J)
    sched = walk + buf + js * H                     # 1本目の時刻どおりの着からの、各便の時刻どおりの発
    dep = sched[None, :] + delays(rng, (n, len(js)), p, m) + k * arr[:, None]
    t = arr + walk                                  # ホームに着く時刻
    dep = np.where(dep >= t[:, None], dep, np.inf)
    taken = dep.min(1)
    jtaken = js[dep.argmin(1)]
    return taken - (walk + buf), jtaken


def simulate(rng, n, P, n_transfer=1):
    """n 日分。戻り値：着く遅れ（乗り換えあり）、同じ区間を乗り換えなしで足した遅れ、1本目の遅れ、乗った便"""
    d1 = delays(rng, n, P["p1"], P["m1"])
    total = d1.copy()
    jj = np.zeros(n, int)
    add = d1.copy()
    for i in range(n_transfer):
        total, j = transfer(rng, total, P["p2"], P["m2"], P["walk"], P["buf"], P["H"], P["k"])
        if i == 0:
            jj = j
        add = add + delays(rng, n, P["p2"], P["m2"])
    return total, add, d1, jj


def summ(x):
    return {"mean": round(float(x.mean()), 3), "median": round(float(np.median(x)), 3),
            "p90": round(float(np.quantile(x, .9)), 3), "p95": round(float(np.quantile(x, .95)), 3),
            "ge5": round(float((x >= 5).mean()) * 100, 2), "ge10": round(float((x >= 10).mean()) * 100, 2),
            "ge15": round(float((x >= 15).mean()) * 100, 2)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    N = 200000
    out = {"base_params": BASE, "n_days": N}

    # 1) 基本：乗り換え0・1・2回
    tot1, add1, d1, j1 = simulate(rng, N, BASE, 1)
    tot2, add2, _, _ = simulate(rng, N, BASE, 2)
    rows = [("1本目の遅れだけ（乗り換え駅に着く遅れ）", d1), ("乗り換えなし・2区間の遅れを足す", add1),
            ("乗り換え1回", tot1), ("乗り換えなし・3区間の遅れを足す", add2), ("乗り換え2回", tot2)]
    tab = pd.DataFrame([{"case": c, **summ(x)} for c, x in rows])
    tab.to_csv(RES / "base_cases.csv", index=False)
    out["base_cases"] = tab.to_dict("records")
    out["base_transfer1"] = {
        "miss_planned_share": round(float((j1 > 0).mean()) * 100, 2),
        "earlier_train_share": round(float((j1 < 0).mean()) * 100, 3),
        "miss2plus_share": round(float((j1 > 1).mean()) * 100, 3),
        "d1_gt_buf_share": round(float((d1 > BASE["buf"]).mean()) * 100, 2),
        "mean_ratio_vs_add": round(float(tot1.mean() / add1.mean()), 3),
        "mean_increase_vs_d1": round(float(tot1.mean() - d1.mean()), 3),
    }
    # 1本目の遅れの幅ごとの、着く遅れ
    bins = [(-0.01, 0.0, "遅れなし（0分）"), (0.0, 1.0, "0〜1分"), (1.0, 2.0, "1〜2分"), (2.0, 3.0, "2〜3分"),
            (3.0, 5.0, "3〜5分"), (5.0, 10.0, "5〜10分"), (10.0, 1e9, "10分より多い")]
    rb = []
    for lo, hi, lab in bins:
        s = (d1 > lo) & (d1 <= hi)
        rb.append({"d1_range": lab, "share_days": round(float(s.mean()) * 100, 2),
                   "d1_mean": round(float(d1[s].mean()), 3), "total_mean": round(float(tot1[s].mean()), 3),
                   "missed_share": round(float((j1[s] > 0).mean()) * 100, 2)})
    rb = pd.DataFrame(rb)
    rb.to_csv(RES / "by_first_delay.csv", index=False)
    out["by_first_delay"] = rb.to_dict("records")

    # 2) 式との照らし合わせ：路線2がいつも時刻どおり（p2=0）なら、
    #    乗りそこねる確率＝p1×exp(−余裕/m1)、乗った便の番号の平均＝p1×exp(−余裕/m1)÷(1−exp(−H/m1))
    P0 = dict(BASE, p2=0.0)
    t0x, _, _, j0 = simulate(np.random.default_rng(SEED + 1), N, P0, 1)
    f_miss = BASE["p1"] * np.exp(-BASE["buf"] / BASE["m1"])
    f_mean = BASE["H"] * f_miss / (1 - np.exp(-BASE["H"] / BASE["m1"]))
    out["formula_check_line2_on_time"] = {
        "miss_sim": round(float((j0 > 0).mean()) * 100, 3), "miss_formula": round(float(f_miss) * 100, 3),
        "mean_sim": round(float(t0x.mean()), 3), "mean_formula": round(float(f_mean), 3)}

    # 3) 確かめ：間隔 × 余裕 × 1本目の遅れやすさ（60通り、各4万日）
    grid = []
    gi = 0
    for p1 in [0.2, 0.35, 0.5]:
        for H in [5, 10, 15, 20]:
            for buf in [0, 1, 2, 4, 6]:
                if buf >= H:   # 余裕が間隔以上だと、ひとつ前の便が計画の便になるので除く
                    continue
                P = dict(BASE, p1=p1, H=float(H), buf=float(buf))
                tt, aa, dd, jj = simulate(np.random.default_rng(SEED * 100 + gi), 40000, P, 1)
                gi += 1
                grid.append({"p1": p1, "H": H, "buf": buf, "mean_transfer": round(float(tt.mean()), 3),
                             "mean_add": round(float(aa.mean()), 3),
                             "ratio": round(float(tt.mean() / aa.mean()), 3),
                             "ge10_transfer": round(float((tt >= 10).mean()) * 100, 2),
                             "ge10_add": round(float((aa >= 10).mean()) * 100, 2),
                             "ge5_transfer": round(float((tt >= 5).mean()) * 100, 2),
                             "ge5_add": round(float((aa >= 5).mean()) * 100, 2),
                             "miss": round(float((jj > 0).mean()) * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_headway_buffer.csv", index=False)
    out["grid_summary"] = {
        "n": int(len(grid)),
        "ratio_min": float(grid.ratio.min()), "ratio_max": float(grid.ratio.max()),
        "ge10_transfer_min": float(grid.ge10_transfer.min()), "ge10_transfer_max": float(grid.ge10_transfer.max()),
        "ge10_add_min": float(grid.ge10_add.min()), "ge10_add_max": float(grid.ge10_add.max()),
        "n_ratio_gt1": int((grid.ratio > 1).sum()), "n_ratio_lt1": int((grid.ratio < 1).sum()),
        "n_ge10_transfer_gt_add": int((grid.ge10_transfer > grid.ge10_add).sum()),
        "n_ge5_transfer_gt_add": int((grid.ge5_transfer > grid.ge5_add).sum()),
        "ge5_transfer_min": float(grid.ge5_transfer.min()), "ge5_transfer_max": float(grid.ge5_transfer.max()),
        "ge5_add_min": float(grid.ge5_add.min()), "ge5_add_max": float(grid.ge5_add.max()),
        "miss_min": float(grid.miss.min()), "miss_max": float(grid.miss.max()),
        "p35_mean_transfer_min": float(grid[grid.p1 == 0.35].mean_transfer.min()),
        "p35_mean_transfer_max": float(grid[grid.p1 == 0.35].mean_transfer.max()),
        "H10plus_ge10_transfer_min": float(grid[grid.H >= 10].ge10_transfer.min()),
        "H10plus_ge10_transfer_max": float(grid[grid.H >= 10].ge10_transfer.max()),
        "H10plus_n_ge10_transfer_gt_add": int((grid[grid.H >= 10].ge10_transfer > grid[grid.H >= 10].ge10_add).sum()),
        "H10plus_n": int((grid.H >= 10).sum()),
        "buf6_ratio_min": float(grid[grid.buf == 6].ratio.min()), "buf6_ratio_max": float(grid[grid.buf == 6].ratio.max()),
        "buf0_ratio_min": float(grid[grid.buf == 0].ratio.min()), "buf0_ratio_max": float(grid[grid.buf == 0].ratio.max()),
        "p35_buf2_by_H": grid[(grid.p1 == 0.35) & (grid.buf == 2)][["H", "mean_transfer", "ge10_transfer", "miss"]].to_dict("records"),
    }

    # 4) 確かめ：路線2の便にも同じ遅れが乗る度合い（共通の遅れ k）
    cr = []
    for k in [0.0, 0.5, 1.0]:
        P = dict(BASE, k=k)
        tt, aa, dd, jj = simulate(np.random.default_rng(SEED * 7 + int(k * 10)), N, P, 1)
        cr.append({"k": k, "mean_transfer": round(float(tt.mean()), 3), "mean_add": round(float(aa.mean()), 3),
                   "ge10_transfer": round(float((tt >= 10).mean()) * 100, 2), "ge10_add": round(float((aa >= 10).mean()) * 100, 2),
                   "miss": round(float((jj > 0).mean()) * 100, 2)})
    cr = pd.DataFrame(cr)
    cr.to_csv(RES / "common_delay.csv", index=False)
    out["common_delay"] = cr.to_dict("records")

    # 1年分（240日）の例のデータ
    r1 = np.random.default_rng(SEED + 5)
    n_ex = 240
    td, ad, dd, jd = simulate(r1, n_ex, BASE, 1)
    ex = pd.DataFrame({"day": np.arange(1, n_ex + 1), "first_delay": dd.round(3), "train_taken": jd,
                       "arrival_delay": td.round(3), "added_no_transfer": ad.round(3)})
    ex.to_csv(DATA / "days_one_year.csv", index=False)
    out["one_year"] = {"days": n_ex, "missed_days": int((jd > 0).sum()),
                       "mean_arrival_delay": round(float(td.mean()), 3), "mean_added": round(float(ad.mean()), 3),
                       "ge10_days": int((td >= 10).sum()), "ge10_days_added": int((ad >= 10).sum())}

    json.dump(out, open(RES / "a1032_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1本目の遅れと、着く遅れ（2,000日）
    sl = slice(0, 2000)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(d1[sl], add1[sl], s=8, color=GRAY, alpha=.45, lw=0, label="乗り換えなし（2区間の遅れを足す）")
    ax.scatter(d1[sl], tot1[sl], s=8, color=ORANGE, alpha=.6, lw=0, label="乗り換え1回（10分おき・余裕2分）")
    ax.axvline(BASE["buf"], color=BLUE, lw=1, ls="--")
    ax.text(BASE["buf"] + 0.2, 27, "余裕2分", color=BLUE, fontsize=9)
    ax.set_xlim(-0.3, 15); ax.set_ylim(-1, 30)
    ax.set_xlabel("1本目（路線1）の遅れ（分）"); ax.set_ylabel("会社の駅に着く遅れ（分）")
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(0.30, 1.0))
    ax.set_title("1本目が余裕を超えて遅れると、着く遅れは便の間隔ぶん跳ぶ（2,000日）")
    save(fig, "a1032_steps.png", SRC)

    # 図2：X分以上遅れる日の割合
    xs = np.arange(0, 31)
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (lab, x), c, ls in zip(rows[1:], [GRAY, ORANGE, LIGHT, BLUE], ["--", "-", ":", "-"]):
        ax.plot(xs, [(x >= v).mean() * 100 for v in xs], color=c, ls=ls, lw=2, label=lab)
    ax.set_yscale("log"); ax.set_ylim(0.01, 100)
    ax.set_xlabel("遅れ（分）"); ax.set_ylabel("この分数以上遅れる日の割合（%、対数の目盛り）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("乗り換えがあると、10分以上の遅れがまとまって出る（20万日）")
    save(fig, "a1032_tail.png", SRC)

    # 図3：間隔×余裕の、乗り換え1回の遅れの平均（p1=0.35）
    g = grid[grid.p1 == 0.35].pivot(index="H", columns="buf", values="mean_transfer")
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    vmax = np.nanmax(g.values)
    im = ax.imshow(np.ma.masked_invalid(g.values), cmap="Oranges", aspect="auto", vmin=0, vmax=vmax)
    ax.set_xticks(range(len(g.columns))); ax.set_xticklabels([f"{c}分" for c in g.columns])
    ax.set_yticks(range(len(g.index))); ax.set_yticklabels([f"{i}分おき" for i in g.index])
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            v = g.values[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=9, color=GRAY)
                continue
            ax.text(j, i, f"{v:.2f}分", ha="center", va="center", fontsize=9,
                    color="white" if v > vmax * 0.6 else INK)
    ax.set_xlabel("乗り換えの余裕（歩く3分のほか）"); ax.set_ylabel("路線2の間隔")
    ax.set_title(f"乗り換え1回の遅れの平均（乗り換えなしの足し算は{tab.loc[1, 'mean']:.2f}分）")
    save(fig, "a1032_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
