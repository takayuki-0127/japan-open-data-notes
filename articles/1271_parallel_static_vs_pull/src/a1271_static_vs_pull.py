"""1271 仕事を初めに同じ数ずつ割り当てるか、終わった所が次を取りにいくかで、全体が終わる時刻はどれだけ違うのか？（架空のデータ）

作成者が置いた架空のアプリの一括の処理。はじめに仕事が N 個（基本800個）そろっていて、8つの所で同時に動かす。
1つの仕事の時間は平均1秒・ばらつき（標準偏差÷平均）cv の右に長い乱数（基本 cv=1.0）。
全体が終わる時刻＝最後の仕事が終わった時刻。理想＝仕事の時間の合計÷（8つの所の速さの合計）。
割り当て方：
  ① 初めに同じ数ずつ（並びの順に N/8 個ずつのかたまりで）
  ② 初めに同じ数ずつ（並びの順に1つずつ交互に配る）
  ③ 終わった所が、並びの次の仕事を1つずつ取りにいく（取りにいくたびに h 秒。基本 h=0.01秒）
  ④ ③と同じだが、はじめに仕事を見込みの大きさ（本当の時間に、対数で標準偏差0.3の外れを掛けたもの）の大きい順に並べておく
並びの置き方：
  A 並びに偏りなし
  B 並びの後ろほど大きい仕事（並びの位置に応じて、時間に0.2〜1.8倍を掛ける。合計の平均は同じ）
  C 偏りなし。ただし8つのうち1つの所だけ速さが0.6倍
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1271
SRC = "架空のアプリの一括の処理（作成者が置いた仕事の時間の分布と割り当ての決まりからの乱数、seed 1271）"
W = 8
EMAX8 = 1.4236          # 8つの標準正規の乱数のいちばん大きい値の平均（式の目安に使う）
METHODS = ["m1_blocks", "m2_alternate", "m3_pull", "m4_pull_largest_first"]
LABELS = ["①同じ数ずつ（かたまり）", "②同じ数ずつ（交互）", "③終わった所が取りにいく", "④取りにいく（大きい順に並べて）"]
SCEN = {"A": "並びに偏りなし", "B": "並びの後ろほど大きい", "C": "1つの所だけ0.6倍の速さ"}


def tasks(rng, R, N, cv, scen):
    sl = np.sqrt(np.log(1 + cv ** 2))
    t = rng.lognormal(-sl ** 2 / 2, sl, (R, N))
    if scen == "B":
        t = t * np.linspace(0.2, 1.8, N)[None, :]
    est = t * rng.lognormal(0, 0.3, (R, N))
    speed = np.ones(W)
    if scen == "C":
        speed[0] = 0.6
    return t, est, speed


def pull(t, speed, h):
    R, N = t.shape
    fin = np.zeros((R, W))
    rr = np.arange(R)
    for i in range(N):
        w = np.argmin(fin, 1)
        fin[rr, w] += h + t[:, i] / speed[w]
    return fin.max(1)


def run(t, est, speed, h):
    R, N = t.shape
    out = {}
    out["m1_blocks"] = (t.reshape(R, W, N // W).sum(2) / speed).max(1)
    out["m2_alternate"] = (t.reshape(R, N // W, W).sum(1) / speed).max(1)
    out["m3_pull"] = pull(t, speed, h)
    order = np.argsort(-est, 1)
    out["m4_pull_largest_first"] = pull(np.take_along_axis(t, order, 1), speed, h)
    ideal = t.sum(1) / speed.sum()
    return out, ideal


def summ(out, ideal, t, speed):
    lb = np.maximum(ideal, t.max(1) / speed.max())
    res = {"ideal_sec_mean": round(float(ideal.mean()), 3), "lower_bound_ext_mean_pct": round(float((lb / ideal - 1).mean()) * 100, 2)}
    for m in METHODS:
        e = out[m] / ideal - 1
        res[m] = {"finish_sec_mean": round(float(out[m].mean()), 3),
                  "ext_mean_pct": round(float(e.mean()) * 100, 2),
                  "ext_p10_pct": round(float(np.quantile(e, 0.1)) * 100, 2),
                  "ext_p90_pct": round(float(np.quantile(e, 0.9)) * 100, 2)}
    d = out["m1_blocks"] - out["m3_pull"]
    res["m1_minus_m3_sec_mean"] = round(float(d.mean()), 3)
    res["m1_minus_m3_sec_p10_p90"] = [round(float(np.quantile(d, 0.1)), 3), round(float(np.quantile(d, 0.9)), 3)]
    res["share_m3_earlier_than_m1"] = round(float((d > 0).mean()), 4)
    return res


def main():
    t0 = time.time()
    R, N, CV, H = 1000, 800, 1.0, 0.01

    base = {}
    for sc in "ABC":
        t, est, speed = tasks(np.random.default_rng([SEED, 1, ord(sc)]), R, N, CV, sc)
        out, ideal = run(t, est, speed, H)
        base[sc] = summ(out, ideal, t, speed)
        base[sc]["pull_cost_pct_of_ideal_if_equal_share"] = round(float((H * N / W / ideal).mean()) * 100, 2)   # 1つの所あたり N/8 回取りにいくとしたときの手間の分
        if sc == "A":
            # 1回分（data に置く）
            fin_rows = []
            for m in METHODS:
                fin_rows.append({"method": m, "finish_sec": round(float(out[m][0]), 3)})
            pd.DataFrame({"task": np.arange(N), "time_sec": t[0].round(4), "est_sec": est[0].round(4),
                          "worker_m1": np.arange(N) // (N // W), "worker_m2": np.arange(N) % W}).to_csv(DATA / "tasks_one_set.csv", index=False)
            base["A"]["one_set_finish_sec"] = {r["method"]: r["finish_sec"] for r in fin_rows}
            base["A"]["one_set_ideal_sec"] = round(float(ideal[0]), 3)
            # ①のかたまりごとの時間（1回分）
            base["A"]["one_set_m1_block_sec"] = [round(float(v), 3) for v in t[0].reshape(W, N // W).sum(1)]
    base["A"]["m1_formula_guide_pct"] = round(EMAX8 * CV / np.sqrt(N / W) * 100, 2)
    rows = []
    for sc in "ABC":
        for i, m in enumerate(METHODS):
            rows.append({"scenario": SCEN[sc], "method": LABELS[i], **base[sc][m]})
    pd.DataFrame(rows).to_csv(RES / "base_by_scenario.csv", index=False)

    # 1回分の、8つの所の仕事の進み（並びに偏りなし）：③の8つの所が終わる時刻
    t, est, speed = tasks(np.random.default_rng([SEED, 1, ord("A")]), 1, N, CV, "A")
    fin = np.zeros(W)
    for i in range(N):
        w = int(np.argmin(fin)); fin[w] += H + t[0, i]
    one_m1 = t[0].reshape(W, N // W).sum(1)
    pd.DataFrame({"worker": np.arange(1, W + 1), "m1_blocks_sec": one_m1.round(3), "m3_pull_sec": fin.round(3)}).to_csv(RES / "one_set_workers.csv", index=False)

    # 取りにいく手間 h を変える（並びに偏りなし・800個、各1,000回）
    hrows = []
    t, est, speed = tasks(np.random.default_rng([SEED, 1, ord("A")]), R, N, CV, "A")
    m1 = (t.reshape(R, W, N // W).sum(2)).max(1)
    ideal = t.sum(1) / W
    for h in [0, 0.01, 0.02, 0.05, 0.1, 0.2]:
        m3 = pull(t, speed, h)
        hrows.append({"h_sec": h, "m1_ext_mean_pct": round(float((m1 / ideal - 1).mean()) * 100, 2),
                      "m3_ext_mean_pct": round(float((m3 / ideal - 1).mean()) * 100, 2),
                      "share_m3_earlier": round(float((m3 < m1).mean()), 4)})
    hr = pd.DataFrame(hrows)
    hr.to_csv(RES / "by_pull_cost.csv", index=False)

    # 確かめ：ばらつき×仕事の数×取りにいく手間（27通り、並びに偏りなし、各200回）
    grid = []
    for cv in [0.3, 1.0, 2.0]:
        for n in [80, 800, 8000]:
            tg, eg, sp = tasks(np.random.default_rng([SEED, 2, int(cv * 10), n]), 200, n, cv, "A")
            idg = tg.sum(1) / W
            g1 = (tg.reshape(200, W, n // W).sum(2)).max(1)
            for h in [0, 0.01, 0.05]:
                g3 = pull(tg, sp, h)
                grid.append({"cv": cv, "tasks": n, "h_sec": h, "ideal_sec_mean": round(float(idg.mean()), 2),
                             "m1_ext_mean_pct": round(float((g1 / idg - 1).mean()) * 100, 2),
                             "m1_formula_guide_pct": round(EMAX8 * cv / np.sqrt(n / W) * 100, 2),
                             "m3_ext_mean_pct": round(float((g3 / idg - 1).mean()) * 100, 2),
                             "m1_minus_m3_sec_mean": round(float((g1 - g3).mean()), 3),
                             "share_m3_earlier": round(float((g3 < g1).mean()), 4)})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    robust = {"settings": int(len(gr)),
              "m1_ext_range": [float(gr.m1_ext_mean_pct.min()), float(gr.m1_ext_mean_pct.max())],
              "m3_ext_range": [float(gr.m3_ext_mean_pct.min()), float(gr.m3_ext_mean_pct.max())],
              "m3_better_count": int((gr.m3_ext_mean_pct < gr.m1_ext_mean_pct).sum()),
              "m3_worse_settings": gr[gr.m3_ext_mean_pct >= gr.m1_ext_mean_pct][["cv", "tasks", "h_sec", "m1_ext_mean_pct", "m3_ext_mean_pct"]].to_dict("records"),
              "m1_minus_formula_guide_range": [round(float((gr.m1_ext_mean_pct - gr.m1_formula_guide_pct).min()), 2), round(float((gr.m1_ext_mean_pct - gr.m1_formula_guide_pct).max()), 2)],
              "share_m3_earlier_range": [float(gr.share_m3_earlier.min()), float(gr.share_m3_earlier.max())]}

    out_json = {"base": base, "by_pull_cost": hrows, "robust": robust,
                "setup": {"tasks": N, "workers": W, "task_mean_sec": 1.0, "task_cv": CV, "pull_cost_sec": H, "reps": R,
                          "order_trend_B": [0.2, 1.8], "slow_worker_speed_C": 0.6, "est_error_sd_log": 0.3, "grid_reps": 200}}
    json.dump(out_json, open(RES / "a1271_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の8つの所が終わる時刻（①と③）
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(W)
    ax.bar(x - 0.2, one_m1, 0.4, color=LIGHT, label="①同じ数ずつ（かたまり）")
    ax.bar(x + 0.2, fin, 0.4, color=BLUE, label="③終わった所が取りにいく")
    idl = base["A"]["one_set_ideal_sec"]
    ax.axhline(idl, color=GRAY, lw=1, ls="--")
    ax.text(5.5, idl + 2, f"理想（合計÷8）{idl:.1f}秒", ha="center", fontsize=8.5, bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xticks(x); ax.set_xticklabels([f"{i+1}つ目" for i in x])
    ax.set_ylim(0, float(max(one_m1.max(), fin.max())) * 1.2); ax.set_ylabel("その所の仕事が全部終わる時刻（秒）")
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=2)
    ax.set_title("同じ800個でも、①は所ごとに終わる時刻がばらつく（1回分）", fontsize=12)
    save(fig, "a1271_one_set.png", SRC)

    # 図2：並びの置き方ごとの延びた割合（各1,000回の平均と10〜90%）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    cols = [LIGHT, ORANGE, BLUE, INK]
    for i, m in enumerate(METHODS):
        xs = np.arange(3) + (i - 1.5) * 0.2
        mean = [base[sc][m]["ext_mean_pct"] for sc in "ABC"]
        lo = [base[sc][m]["ext_mean_pct"] - base[sc][m]["ext_p10_pct"] for sc in "ABC"]
        hi = [base[sc][m]["ext_p90_pct"] - base[sc][m]["ext_mean_pct"] for sc in "ABC"]
        ax.bar(xs, mean, 0.2, color=cols[i], label=LABELS[i])
        ax.errorbar(xs, mean, yerr=[lo, hi], fmt="none", ecolor=GRAY, capsize=2, lw=0.8)
    ax.set_xticks(np.arange(3)); ax.set_xticklabels([f"{k}：{v}" for k, v in SCEN.items()])
    ymax = max(base[sc][m]["ext_p90_pct"] for sc in "ABC" for m in METHODS)
    ax.set_ylim(0, ymax * 1.1); ax.set_ylabel("理想より延びた割合（%、平均と10〜90%）")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax.set_title("全体が終わる時刻の延び（仕事800個・8つの所、各1,000回）", fontsize=12)
    save(fig, "a1271_by_scenario.png", SRC, y=-0.2)

    # 図3：27通り（①と③）
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    gx = np.arange(len(gr))
    ax.plot(gx, gr.m1_ext_mean_pct, "o-", color=LIGHT, ms=4, lw=0.9, label="①同じ数ずつ（かたまり）")
    ax.plot(gx, gr.m3_ext_mean_pct, "o-", color=BLUE, ms=4, lw=0.9, label="③終わった所が取りにいく")
    for kk in [9, 18]:
        ax.axvline(kk - 0.5, color=GRAY, lw=0.8, ls=":")
    ax.set_yscale("symlog", linthresh=1)
    tk = [0, 0.5, 1, 2, 5, 10, 20, 50, 100, 200]
    ym = float(max(gr.m1_ext_mean_pct.max(), gr.m3_ext_mean_pct.max()))
    ax.set_ylim(0, ym * 3)
    ax.set_yticks([v for v in tk if v <= ym * 3]); ax.set_yticklabels([f"{v:g}" for v in tk if v <= ym * 3]); ax.minorticks_off()
    for kk, cv in enumerate([0.3, 1.0, 2.0]):
        ax.text(kk * 9 + 4, ym * 1.7, f"仕事の時間のばらつき{cv}", ha="center", fontsize=8.5)
    ax.set_xticks(gx); ax.set_xticklabels([f"{n}・{h:g}" for n, h in zip(gr.tasks, gr.h_sec)], fontsize=6, rotation=90)
    ax.set_xlabel("27通り（下は「仕事の数・取りにいく手間（秒）」）", fontsize=8.5)
    ax.set_ylabel("理想より延びた割合（%、各200回の平均、0〜1は等間隔・その上は対数）", fontsize=8)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.27))
    ax.set_title("仕事が少なくばらつきが大きいほど①が延び、手間が大きいと③が延びる", fontsize=11.5)
    save(fig, "a1271_grid.png", SRC, y=-0.33)
    print(json.dumps(out_json, ensure_ascii=False, indent=1))
    print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
