"""1279 同時に動かす数を増やして1秒あたりの件数が増えたとき、1件が終わるまでの時間はどう動いているのか？（架空のデータ）

架空のアプリの処理を試す場面。処理する所は C か所（基本8）。試す側は K 本の流れを同時に動かし、
それぞれの流れは「1件を送る → 終わるのを待つ → 考える時間 Z だけ休む → 次の1件を送る」をくり返す。
1件の処理に要る量（平均0.1秒）は乱数で振れる。所の使い方は2つ：
  分け合う：動いている件が C 件より多いと、C か所の速さを全員で等しく分け合う
  順に待つ：C か所が埋まっていると、来た順に列に並んで待つ
1秒あたりの件数と、1件が送ってから終わるまでの時間を数える。すべてシミュレーションで、実機では測っていない。
"""
import json
import time
import heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1279
SRC = "架空のアプリの処理のシミュレーション（作成者が乱数で作成、seed 1279）"
BASE = {"c": 8, "mean_s": 0.1, "sigma": 1.0, "think": 0.4}
KS = [1, 4, 8, 16, 24, 32, 40, 48, 64, 96, 128]
DONE = 30000
WARM = 3000
GRID_DONE = 12000
GRID_WARM = 1500


def sizes(rng, n, mean_s, sigma):
    return rng.lognormal(np.log(mean_s) - sigma ** 2 / 2, sigma, n)


def sim_share(k, c, mean_s, sigma, think, done, warm, rng):
    """分け合う：動いている n 件が C か所の速さを等しく分け合う（1件あたり最大1か所分）"""
    need = 2 * (done + warm + k) + 10
    sz = sizes(rng, need, mean_s, sigma)
    th = rng.exponential(think, need) if think > 0 else np.zeros(need)
    t = 0.0
    v = 0.0                    # 1件あたりに配られた処理の量の累計
    act = []                   # (終わる v, 送った時刻)
    thinking = []              # (送る時刻)
    for i in range(k):
        heapq.heappush(thinking, th[i])
    idx = k
    lat, cnt = [], 0
    while cnt < done + warm:
        n = len(act)
        r = min(1.0, c / n) if n else 0.0
        t_fin = t + (act[0][0] - v) / r if n else np.inf
        t_arr = thinking[0] if thinking else np.inf
        if t_arr <= t_fin:
            v += r * (t_arr - t)
            t = t_arr
            heapq.heappop(thinking)
            heapq.heappush(act, (v + sz[idx], t))
            idx += 1
        else:
            v = act[0][0]
            t = t_fin
            _, t0 = heapq.heappop(act)
            cnt += 1
            if cnt == warm:
                t_start = t
            if cnt > warm:
                lat.append(t - t0)
            heapq.heappush(thinking, t + th[idx])
            idx += 1
    return np.array(lat), done / (t - t_start)


def sim_queue(k, c, mean_s, sigma, think, done, warm, rng):
    """順に待つ：C か所が埋まっていれば、来た順に列に並ぶ"""
    need = 2 * (done + warm + k) + 10
    sz = sizes(rng, need, mean_s, sigma)
    th = rng.exponential(think, need) if think > 0 else np.zeros(need)
    ev = []                    # (時刻, 種類 0=送る 1=終わる, 送った時刻, 大きさ)
    for i in range(k):
        heapq.heappush(ev, (th[i], 0, th[i], sz[i]))
    idx = k
    busy = 0
    line = []
    li = 0
    lat, cnt = [], 0
    while cnt < done + warm:
        t, kind, t0, s = heapq.heappop(ev)
        if kind == 0:
            if busy < c:
                busy += 1
                heapq.heappush(ev, (t + s, 1, t0, s))
            else:
                line.append((t0, s))
        else:
            cnt += 1
            if cnt == warm:
                t_start = t
            if cnt > warm:
                lat.append(t - t0)
            nt = t + th[idx]
            heapq.heappush(ev, (nt, 0, nt, sz[idx]))
            idx += 1
            if li < len(line):
                q0, qs = line[li]
                li += 1
                heapq.heappush(ev, (t + qs, 1, q0, qs))
            else:
                busy -= 1
    return np.array(lat), done / (t - t_start)


def summarize(lat, x):
    return {"per_sec": float(x), "mean_ms": float(lat.mean() * 1000), "p50_ms": float(np.quantile(lat, .5) * 1000),
            "p99_ms": float(np.quantile(lat, .99) * 1000)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    c, ms, sg, z = BASE["c"], BASE["mean_s"], BASE["sigma"], BASE["think"]
    rows = []
    keep = {}
    for rule, fn in [("share", sim_share), ("queue", sim_queue)]:
        for k in KS:
            lat, x = fn(k, c, ms, sg, z, DONE, WARM, rng)
            s = summarize(lat, x)
            s.update({"rule": rule, "k": k, "k_check": float(x * (lat.mean() + z))})
            rows.append(s)
            if k in (8, 64):
                keep[(rule, k)] = lat
    base = pd.DataFrame(rows)
    for rule in ["share", "queue"]:
        m = base.rule == rule
        b1 = base[m & (base.k == 1)].iloc[0]
        base.loc[m, "per_sec_vs_k1"] = base.loc[m, "per_sec"] / b1.per_sec
        base.loc[m, "mean_vs_k1"] = base.loc[m, "mean_ms"] / b1.mean_ms
        base.loc[m, "p99_vs_k1"] = base.loc[m, "p99_ms"] / b1.p99_ms
        base.loc[m, "per_sec_vs_max"] = base.loc[m, "per_sec"] / base.loc[m, "per_sec"].max()
    base = base[["rule", "k", "per_sec", "mean_ms", "p50_ms", "p99_ms", "per_sec_vs_k1", "mean_vs_k1", "p99_vs_k1",
                 "per_sec_vs_max", "k_check"]].round(4)
    base.to_csv(RES / "base_by_k.csv", index=False)

    cap = c / ms                               # 所が全部働いたときの1秒あたりの件数（式）
    k_star = c * (ms + z) / ms                 # 件数が頭打ちになり始める流れの数の目安（式）

    def pick(rule, k, col):
        return float(base[(base.rule == rule) & (base.k == k)][col].iloc[0])

    steps = []
    for rule in ["share", "queue"]:
        d = base[base.rule == rule].reset_index(drop=True)
        for i in range(1, len(d)):
            steps.append({"rule": rule, "k_from": int(d.k[i - 1]), "k_to": int(d.k[i]),
                          "per_sec_ratio": d.per_sec[i] / d.per_sec[i - 1],
                          "mean_ratio": d.mean_ms[i] / d.mean_ms[i - 1],
                          "p99_ratio": d.p99_ms[i] / d.p99_ms[i - 1]})
    steps = pd.DataFrame(steps).round(4)
    steps.to_csv(RES / "step_ratios.csv", index=False)

    # 1回分の例（分け合う・K=64 の1件ごとの時間、先頭2,000件）
    pd.DataFrame({"latency_ms": (keep[("share", 64)][:2000] * 1000).round(3)}).to_csv(DATA / "example_latency_share_k64.csv", index=False)

    # 確かめ：C×大きさの散らばり×考える時間の27通り。K は頭打ちの目安 K* の 1/2・1・2・4倍
    grng = np.random.default_rng(SEED + 1)
    grows = []
    for gc in [4, 8, 16]:
        for gsg in [0.25, 1.0, 1.5]:
            for gz in [0.0, 0.4, 1.6]:
                ks = c_k = gc * (ms + gz) / ms
                klist = sorted(set([1] + [max(1, int(round(c_k * f))) for f in [0.5, 1, 2, 4]]))
                for rule, fn in [("share", sim_share), ("queue", sim_queue)]:
                    res = {}
                    for k in klist:
                        lat, x = fn(k, gc, ms, gsg, gz, GRID_DONE, GRID_WARM, grng)
                        res[k] = summarize(lat, x)
                    k1 = res[1]
                    for f, k in zip([0.5, 1, 2, 4], [max(1, int(round(c_k * f))) for f in [0.5, 1, 2, 4]]):
                        grows.append({"c": gc, "sigma": gsg, "think": gz, "rule": rule, "k_over_kstar": f, "k": k,
                                      "per_sec_vs_max_cap": res[k]["per_sec"] / (gc / ms),
                                      "per_sec_vs_k1": res[k]["per_sec"] / k1["per_sec"],
                                      "mean_vs_k1": res[k]["mean_ms"] / k1["mean_ms"],
                                      "p99_vs_k1": res[k]["p99_ms"] / k1["p99_ms"],
                                      "p99_ms": res[k]["p99_ms"], "mean_ms": res[k]["mean_ms"]})
    grid = pd.DataFrame(grows).round(4)
    grid.to_csv(RES / "grid.csv", index=False)

    # 頭打ちの目安から2倍・4倍に増やしたとき（27通り×2）
    pv = grid.pivot_table(index=["c", "sigma", "think", "rule"], columns="k_over_kstar",
                          values=["per_sec_vs_k1", "mean_vs_k1", "p99_vs_k1"]).reset_index()
    pv2 = grid.pivot_table(index=["c", "sigma", "think", "rule"], columns="k_over_kstar", values="per_sec_vs_max_cap")
    gain_x_1to2 = pv2[2.0].to_numpy() / pv2[1.0].to_numpy()
    gain_r_1to2 = pv[("mean_vs_k1", 2.0)] / pv[("mean_vs_k1", 1.0)]
    gain_x_half = pv2[1.0].to_numpy() / pv2[0.5].to_numpy()
    gain_r_half = pv[("mean_vs_k1", 1.0)] / pv[("mean_vs_k1", 0.5)]
    sh = grid[grid.rule == "share"].set_index(["c", "sigma", "think", "k_over_kstar"])
    qu = grid[grid.rule == "queue"].set_index(["c", "sigma", "think", "k_over_kstar"])
    p99_ratio_share_over_queue = (sh.p99_ms / qu.p99_ms)
    mean_ratio_share_over_queue = (sh.mean_ms / qu.mean_ms)

    main_json = {
        "setting": {**BASE, "ks": KS, "done": DONE, "warm": WARM},
        "formula": {"cap_per_sec": cap, "k_star": k_star},
        "headline": {
            "share_k1": base[(base.rule == "share") & (base.k == 1)].iloc[0].to_dict(),
            "share_k32": base[(base.rule == "share") & (base.k == 32)].iloc[0].to_dict(),
            "share_k40": base[(base.rule == "share") & (base.k == 40)].iloc[0].to_dict(),
            "share_k64": base[(base.rule == "share") & (base.k == 64)].iloc[0].to_dict(),
            "queue_k40": base[(base.rule == "queue") & (base.k == 40)].iloc[0].to_dict(),
            "queue_k64": base[(base.rule == "queue") & (base.k == 64)].iloc[0].to_dict(),
            "share_32_to_64": {"per_sec_ratio": round(pick("share", 64, "per_sec") / pick("share", 32, "per_sec"), 4),
                               "mean_ratio": round(pick("share", 64, "mean_ms") / pick("share", 32, "mean_ms"), 4),
                               "p99_ratio": round(pick("share", 64, "p99_ms") / pick("share", 32, "p99_ms"), 4)},
            "share_40_to_96": {"per_sec_ratio": round(pick("share", 96, "per_sec") / pick("share", 40, "per_sec"), 4),
                               "mean_ratio": round(pick("share", 96, "mean_ms") / pick("share", 40, "mean_ms"), 4)},
            "p99_share_over_queue_k64": round(pick("share", 64, "p99_ms") / pick("queue", 64, "p99_ms"), 4),
            "p50_share_over_queue_k64": round(pick("share", 64, "p50_ms") / pick("queue", 64, "p50_ms"), 4),
            "k_check_max_abs_err": round(float((base.k_check - base.k).abs().max()), 4),
            "share_k_max_per_sec": int(base[base.rule == "share"].sort_values("per_sec").k.iloc[-1]),
            "queue_k_max_per_sec": int(base[base.rule == "queue"].sort_values("per_sec").k.iloc[-1]),
        },
        "grid_range": {
            "per_sec_gain_kstar_to_2kstar": [round(float(gain_x_1to2.min()), 4), round(float(gain_x_1to2.max()), 4)],
            "mean_gain_kstar_to_2kstar": [round(float(gain_r_1to2.min()), 4), round(float(gain_r_1to2.max()), 4)],
            "per_sec_gain_half_to_kstar": [round(float(gain_x_half.min()), 4), round(float(gain_x_half.max()), 4)],
            "mean_gain_half_to_kstar": [round(float(gain_r_half.min()), 4), round(float(gain_r_half.max()), 4)],
            "per_sec_vs_cap_at_kstar": [float(grid[grid.k_over_kstar == 1].per_sec_vs_max_cap.min()),
                                        float(grid[grid.k_over_kstar == 1].per_sec_vs_max_cap.max())],
            "p99_share_over_queue_at_4kstar": [round(float(p99_ratio_share_over_queue.xs(4.0, level=3).min()), 4),
                                               round(float(p99_ratio_share_over_queue.xs(4.0, level=3).max()), 4)],
            "mean_share_over_queue_at_4kstar": [round(float(mean_ratio_share_over_queue.xs(4.0, level=3).min()), 4),
                                                round(float(mean_ratio_share_over_queue.xs(4.0, level=3).max()), 4)],
            "mean_gain_kstar_to_2kstar_by_think": {str(zz): [round(float(gain_r_1to2[pv.think == zz].min()), 4),
                                                            round(float(gain_r_1to2[pv.think == zz].max()), 4)]
                                                   for zz in [0.0, 0.4, 1.6]},
            "n_cases": int(len(pv)),
        },
    }

    # 図1：1秒あたりの件数と、1件の時間（平均・99%点）。分け合う
    d = base[base.rule == "share"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    ax = axes[0]
    ax.plot(d.k, d.per_sec, marker="o", color=BLUE)
    ax.axhline(cap, color=GRAY, ls="--", lw=1)
    ax.text(KS[-1], cap * 1.02, "所が全部働いたとき（式）", ha="right", va="bottom", color=GRAY, fontsize=9)
    ax.set_ylim(0, cap * 1.15)
    ax.set_xlabel("同時に動かす流れの数")
    ax.set_ylabel("1秒あたりの件数")
    ax.set_title("1秒あたりの件数")
    ax = axes[1]
    ax.plot(d.k, d.mean_ms, marker="o", color=BLUE, label="平均")
    ax.plot(d.k, d.p99_ms, marker="^", color=ORANGE, label="99%点")
    ax.set_ylim(0, None)
    ax.set_xlabel("同時に動かす流れの数")
    ax.set_ylabel("1件が終わるまでの時間（ミリ秒）")
    ax.set_title("1件が終わるまでの時間")
    ax.legend(frameon=False)
    fig.suptitle("所8か所・分け合う使い方：流れを増やしたときの件数と時間", y=1.03)
    save(fig, "a1279_per_sec_and_latency.png", SRC, y=-0.04)

    # 図2：件数（横）と1件の時間（縦）の関係。分け合う・順に待つ
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for rule, lab, col, mk in [("share", "分け合う：平均", BLUE, "o"), ("queue", "順に待つ：平均", GREEN, "s")]:
        dd = base[base.rule == rule]
        ax.plot(dd.per_sec, dd.mean_ms, marker=mk, color=col, label=lab)
    for rule, lab, col, mk in [("share", "分け合う：99%点", ORANGE, "^"), ("queue", "順に待つ：99%点", GRAY, "v")]:
        dd = base[base.rule == rule]
        ax.plot(dd.per_sec, dd.p99_ms, marker=mk, color=col, ls=":", label=lab)
    ax.set_xlim(0, cap * 1.05)
    ax.set_ylim(0, None)
    ax.set_xlabel("1秒あたりの件数")
    ax.set_ylabel("1件が終わるまでの時間（ミリ秒）")
    ax.set_title("流れを1→128本に増やしたときの、件数と1件の時間")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1279_per_sec_vs_latency.png", SRC)

    # 図3：64本のときの1件の時間の分布（分け合う・順に待つ）
    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.linspace(0, np.quantile(np.concatenate([keep[("share", 64)], keep[("queue", 64)]]), 0.995) * 1000, 60)
    ax.hist(keep[("queue", 64)] * 1000, bins=bins, color=GREEN, alpha=0.5, label="順に待つ")
    ax.hist(keep[("share", 64)] * 1000, bins=bins, histtype="step", color=BLUE, lw=1.6, label="分け合う")
    ax.set_xlabel("1件が終わるまでの時間（ミリ秒）")
    ax.set_ylabel("件数（30,000件のうち）")
    ax.set_title("流れ64本：1件の時間の分布")
    ax.legend(frameon=False)
    save(fig, "a1279_hist_k64.png", SRC)

    with open(RES / "a1279_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(base.to_string())
    print(steps.to_string())
    print(json.dumps(main_json, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
