"""876 窓口を1列にするか、窓口ごとに並ぶかで、待ち時間は？（架空のデータ）

架空の店の窓口4つ。客はでたらめな間隔で来て（ポアソン到着）、1人の手続き時間は対数正規分布。
「1列に並び、空いた窓口に呼ばれる」と「窓口ごとに並ぶ（いちばん人数の少ない列を選ぶ／でたらめに選ぶ）」で、
同じ客・同じ手続き時間のときの待ち時間を比べる。
"""
import json, time, heapq
from collections import deque
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 876
SRC = "架空の店の窓口（作成者が乱数で作成、seed 876）"
OPEN_MIN = 480          # 1日8時間受け付ける
MEAN_SVC = 3.0          # 1人の手続き時間の平均（分）


def make_day(rng, c=4, rho=0.85, cv=1.0):
    lam = rho * c / MEAN_SVC
    n = rng.poisson(lam * OPEN_MIN)
    arr = np.sort(rng.uniform(0, OPEN_MIN, n))
    s2 = np.log(1 + cv ** 2)
    svc = rng.lognormal(np.log(MEAN_SVC) - s2 / 2, np.sqrt(s2), n)
    return arr, svc


def single_line(arr, svc, c, walk=0.0):
    """1列：空いた窓口に先頭から呼ぶ。呼ばれてから窓口に着くまで walk 分かかり、その間窓口はふさがる"""
    free = [0.0] * c
    wait = np.empty(len(arr))
    for i, (t, s) in enumerate(zip(arr, svc)):
        f = heapq.heappop(free)
        st = max(t, f)
        wait[i] = st + walk - t
        heapq.heappush(free, st + walk + s)
    return wait


def per_counter(arr, svc, c, rng, rule="shortest"):
    """窓口ごとに並ぶ。shortest：着いたときいちばん人数の少ない列（同じなら、でたらめ）。random：でたらめに選ぶ。列は替えない"""
    deps = [deque() for _ in range(c)]
    last = [0.0] * c
    wait = np.empty(len(arr)); line = np.empty(len(arr), dtype=int)
    tie = rng.random((len(arr), c))
    pick = rng.integers(0, c, len(arr))
    for i, (t, s) in enumerate(zip(arr, svc)):
        if rule == "shortest":
            best, bl = -1, None
            for k in range(c):
                d = deps[k]
                while d and d[0] <= t:
                    d.popleft()
                key = (len(d), tie[i, k])
                if bl is None or key < bl:
                    best, bl = k, key
            k = best
        else:
            k = pick[i]
            d = deps[k]
            while d and d[0] <= t:
                d.popleft()
        st = max(t, last[k])
        last[k] = st + s
        deps[k].append(last[k])
        wait[i] = st - t; line[i] = k
    return wait, line


def overtaken(arr, wait):
    """自分より後に着いた人が、自分より先に手続きを始めた割合"""
    st = arr + wait
    suf = np.minimum.accumulate(st[::-1])[::-1]
    later_min = np.append(suf[1:], np.inf)
    return later_min < st - 1e-9


def stats(w, ov=None):
    d = {"mean": float(w.mean()), "p_gt5": float((w > 5).mean()), "p_gt10": float((w > 10).mean()),
         "p95": float(np.quantile(w, .95)), "share_zero": float((w <= 1e-9).mean())}
    if ov is not None:
        d["overtaken"] = float(ov.mean())
    return d


def run(rng_seed, days, c=4, rho=0.85, cv=1.0, walks=(0.0,)):
    rng = np.random.default_rng(rng_seed)
    W = {k: [] for k in ["single", "shortest", "random"] + [f"single_walk{w}" for w in walks if w > 0]}
    O = {"shortest": [], "random": []}
    for _ in range(days):
        arr, svc = make_day(rng, c, rho, cv)
        W["single"].append(single_line(arr, svc, c))
        for w in walks:
            if w > 0:
                W[f"single_walk{w}"].append(single_line(arr, svc, c, w))
        for rule in ["shortest", "random"]:
            w_, _ = per_counter(arr, svc, c, rng, rule)
            W[rule].append(w_); O[rule].append(overtaken(arr, w_))
    out = {}
    for k, v in W.items():
        w = np.concatenate(v)
        out[k] = stats(w, np.concatenate(O[k]) if k in O else None)
    out["n_customers"] = int(sum(len(x) for x in W["single"]))
    return out, W


def r3(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 1回分（data）
    arr, svc = make_day(rng)
    ws = single_line(arr, svc, 4)
    wsh, lsh = per_counter(arr, svc, 4, rng, "shortest")
    wr, lr = per_counter(arr, svc, 4, rng, "random")
    pd.DataFrame({"cust_id": np.arange(1, len(arr) + 1), "arrival_min": arr, "service_min": svc,
                  "wait_single": ws, "wait_shortest": wsh, "line_shortest": lsh + 1,
                  "wait_random": wr, "line_random": lr + 1}).to_csv(DATA / "customers_one_day.csv", index=False,
                                                                     float_format="%.3f")
    one = {"n": int(len(arr)), "single": r3(stats(ws)), "shortest": r3(stats(wsh, overtaken(arr, wsh))),
           "random": r3(stats(wr, overtaken(arr, wr)))}

    # 2) 基本：窓口4・利用85%・ばらつき（変動係数）1.0、1,000日
    WALKS = tuple(x / 60 for x in (0, 2, 4, 6, 8, 10, 15, 20, 30))   # 秒→分
    base, Wb = run(SEED * 10, 1000, walks=WALKS)
    rows = []
    names = {"single": "1列（空いた窓口に呼ぶ）", "shortest": "窓口ごと（いちばん人数の少ない列）",
             "random": "窓口ごと（でたらめに選ぶ）"}
    for k in ["single", "shortest", "random"]:
        rows.append({"method": names[k], **r3(base[k])})
    pd.DataFrame(rows).to_csv(RES / "base_methods.csv", index=False)
    walk_rows = [{"walk_sec": 0, "mean": round(base["single"]["mean"], 4), "p_gt10": round(base["single"]["p_gt10"], 4)}]
    for w in WALKS[1:]:
        walk_rows.append({"walk_sec": int(round(w * 60)), "mean": round(base[f"single_walk{w}"]["mean"], 4),
                          "p_gt10": round(base[f"single_walk{w}"]["p_gt10"], 4)})
    walk_df = pd.DataFrame(walk_rows)
    walk_df["shortest_mean"] = round(base["shortest"]["mean"], 4)
    walk_df["shortest_p_gt10"] = round(base["shortest"]["p_gt10"], 4)
    walk_df.to_csv(RES / "walk_time.csv", index=False)

    # 3) 確かめ：利用の割合×手続き時間のばらつき、窓口の数（各200日）
    sens = []
    for i, (c, rho, cv) in enumerate([(4, r, v) for r in (0.7, 0.85, 0.95) for v in (0.5, 1.0, 1.5)] +
                                     [(2, 0.85, 1.0), (8, 0.85, 1.0)]):
        o, _ = run(SEED * 100 + i, 200, c, rho, cv)
        sens.append({"counters": c, "rho": rho, "cv": cv, "n_customers": o["n_customers"],
                     "single_mean": round(o["single"]["mean"], 3), "shortest_mean": round(o["shortest"]["mean"], 3),
                     "random_mean": round(o["random"]["mean"], 3),
                     "ratio_shortest_single": round(o["shortest"]["mean"] / o["single"]["mean"], 3),
                     "single_p_gt10": round(o["single"]["p_gt10"], 4), "shortest_p_gt10": round(o["shortest"]["p_gt10"], 4),
                     "random_p_gt10": round(o["random"]["p_gt10"], 4),
                     "single_p95": round(o["single"]["p95"], 3), "shortest_p95": round(o["shortest"]["p95"], 3),
                     "shortest_overtaken": round(o["shortest"]["overtaken"], 4)})
    sens_df = pd.DataFrame(sens)
    sens_df.to_csv(RES / "sensitivity.csv", index=False)

    # 1列の歩く時間が何秒で、窓口ごと（短い列）の平均と並ぶか（線で結んだ読み取り）
    def breakeven(x, y, yb):
        for j in range(len(x) - 1):
            if (y[j] - yb) * (y[j + 1] - yb) <= 0 and y[j] != y[j + 1]:
                return float(x[j] + (yb - y[j]) * (x[j + 1] - x[j]) / (y[j + 1] - y[j]))
        return None
    yb = base["shortest"]["mean"]
    be = breakeven(walk_df.walk_sec.values, walk_df["mean"].values, yb)
    be10 = breakeven(walk_df.walk_sec.values, walk_df["p_gt10"].values, base["shortest"]["p_gt10"])
    # 確かめ：利用の割合を変えたときの、並ぶ歩く時間（各200日）
    be_rows = []
    for i, rho in enumerate((0.7, 0.85, 0.95)):
        o, _ = run(SEED * 1000 + i, 200, 4, rho, 1.0, walks=WALKS)
        xs_ = [int(round(w * 60)) for w in WALKS]
        ys_ = [o["single"]["mean"]] + [o[f"single_walk{w}"]["mean"] for w in WALKS[1:]]
        b_ = breakeven(np.array(xs_), np.array(ys_), o["shortest"]["mean"])
        be_rows.append({"rho": rho, "single_mean_walk0": round(ys_[0], 3), "shortest_mean": round(o["shortest"]["mean"], 3),
                        "breakeven_sec": None if b_ is None else round(b_, 1),
                        "rho_effective_at_breakeven": None if b_ is None else round(rho * (MEAN_SVC + b_ / 60) / MEAN_SVC, 3)})
    pd.DataFrame(be_rows).to_csv(RES / "walk_breakeven_by_rho.csv", index=False)
    out = {"setting": {"counters": 4, "rho": 0.85, "cv": 1.0, "mean_service_min": MEAN_SVC, "open_min": OPEN_MIN,
                       "days": 1000},
           "base": {k: r3(base[k]) for k in ["single", "shortest", "random"]}, "n_customers_base": base["n_customers"],
           "ratio_mean_shortest_over_single": round(base["shortest"]["mean"] / base["single"]["mean"], 3),
           "ratio_mean_random_over_single": round(base["random"]["mean"] / base["single"]["mean"], 3),
           "walk_breakeven_sec": None if be is None else round(be, 1),
           "walk_breakeven_sec_p_gt10": None if be10 is None else round(be10, 1),
           "walk_breakeven_by_rho": be_rows,
           "sens_ratio_range": [float(sens_df.ratio_shortest_single.min()), float(sens_df.ratio_shortest_single.max())],
           "sens_overtaken_range": [float(sens_df.shortest_overtaken.min()), float(sens_df.shortest_overtaken.max())],
           "one_day": one}
    json.dump(out, open(RES / "a876_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：x分より長く待った人の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xs = np.linspace(0, 25, 251)
    for k, col, lab in [("single", BLUE, "1列（空いた窓口に呼ぶ）"), ("shortest", ORANGE, "窓口ごと（いちばん人数の少ない列）"),
                        ("random", GRAY, "窓口ごと（でたらめに選ぶ）")]:
        w = np.sort(np.concatenate(Wb[k]))
        ccdf = 1 - np.searchsorted(w, xs, side="right") / len(w)
        ax.plot(xs, ccdf * 100, color=col, lw=2, label=f"{lab}　平均{base[k]['mean']:.1f}分")
    ax.set_xlabel("待ち時間（分）"); ax.set_ylabel("この時間より長く待った人の割合（%）")
    ax.set_ylim(0, 90); ax.set_xlim(0, 25); ax.legend(frameon=False, fontsize=9)
    ax.set_title("窓口4つ・利用85%：1列にすると、長く待つ人が減る（1,000日）")
    save(fig, "a876_ccdf.png", SRC)

    # 図2：確かめ（窓口4つ、利用×ばらつき）の平均待ちの比
    s4 = sens_df[sens_df.counters == 4]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xpos = np.arange(3); wbar = 0.26
    for j, (cv, col) in enumerate([(0.5, LIGHT), (1.0, BLUE), (1.5, INK)]):
        v = s4[s4.cv == cv].sort_values("rho").ratio_shortest_single.values
        ax.bar(xpos + (j - 1) * wbar, v, wbar, color=col, label=f"手続き時間のばらつき {cv}")
        for xi, vi in zip(xpos + (j - 1) * wbar, v):
            ax.text(xi, vi + 0.03, f"{vi:.2f}", ha="center", fontsize=8.5)
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.set_xticks(xpos); ax.set_xticklabels(["利用70%", "利用85%", "利用95%"])
    ax.set_ylabel("平均の待ち時間の比（窓口ごと÷1列）"); ax.set_ylim(0, max(2.0, s4.ratio_shortest_single.max() + 0.3))
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("いちばん短い列を選んでも、平均の待ちは1列より長い（歩く時間0、各200日）")
    save(fig, "a876_sensitivity.png", SRC)

    # 図3：1列で呼ばれてから窓口まで歩く時間
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(walk_df.walk_sec, walk_df["mean"], "o-", color=BLUE, lw=2, label="1列（歩く時間の分、窓口がふさがる）")
    ax.axhline(yb, color=ORANGE, lw=2, ls="--", label=f"窓口ごと（いちばん人数の少ない列）{yb:.1f}分")
    ax.set_xlabel("呼ばれてから窓口に着くまでの時間（秒、1人あたり）"); ax.set_ylabel("平均の待ち時間（分）")
    ax.set_xticks(walk_df.walk_sec); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_ylim(0, max(walk_df["mean"].max(), yb) * 1.25)
    ttl = f"歩く時間が1人{be:.0f}秒ほどで、1列の利点は消える（利用85%）" if be else "歩く時間と1列の平均の待ち"
    ax.set_title(ttl)
    save(fig, "a876_walk.png", SRC)
    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
