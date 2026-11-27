"""1313 置く台を乱数で2つ選んで、空いている方へ入れる決まりにすると、いちばん多い1台は1つだけ選ぶときよりどれだけ減るのか？（架空のデータ）

作成者が置いた架空のアプリの記録。1万件を1件ずつ、100台のどれかに置く（平均は1台100件）。置いたら動かさない。
置き方：
  ① 乱数で1台選んで置く
  ② 乱数で2台選び、そのときの件数が少ない方に置く（同じなら1つ目）
  ③ 乱数で3台選び、いちばん少ない台に置く
  ④ 全部の台を見て、いちばん少ない台に置く（参考）
  ⑤ ②と同じだが、台ごとの件数を知るのが遅れる（B件置くごとにしか件数を数え直さない）
いちばん多い1台が平均より何件多いか、平均の何倍かを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1313
SRC = "架空のアプリの記録（作成者が置いた置き方の決まりからの乱数、seed 1313）"


def place(rng, R, N, M, d, refresh=1):
    """d 台を乱数で選び、件数の少ない台に置く。d=0 は全部の台を見る。refresh 件ごとにしか件数を数え直さない"""
    load = np.zeros((R, M), dtype=np.int64)
    rr = np.arange(R)
    if d == 1:
        ch = rng.integers(0, M, (R, N))
        idx = (rr[:, None] * M + ch).ravel()
        return np.bincount(idx, minlength=R * M).reshape(R, M)
    if d == 0:
        for i in range(N):
            k = np.argmin(load, 1)
            load[rr, k] += 1
        return load
    seen = load.copy()
    CH = 4096
    for s in range(0, N, CH):
        n = min(CH, N - s)
        ch = rng.integers(0, M, (n, R, d))
        for i in range(n):
            if refresh > 1 and (s + i) % refresh == 0:
                seen = load.copy()
            c = ch[i]
            v = np.take_along_axis(seen if refresh > 1 else load, c, 1)
            load[rr, c[rr, np.argmin(v, 1)]] += 1
    return load


def summ(load, N, M):
    mean = N / M
    mx = load.max(1)
    return {"max_mean": round(float(mx.mean()), 3), "excess_mean": round(float(mx.mean() - mean), 3),
            "excess_p10": round(float(np.quantile(mx, 0.1) - mean), 3), "excess_p90": round(float(np.quantile(mx, 0.9) - mean), 3),
            "max_vs_average": round(float(mx.mean() / mean), 4),
            "min_mean": round(float(load.min(1).mean()), 3)}


def main():
    t0 = time.time()
    R, N, M = 1000, 10_000, 100

    base = {}
    loads = {}
    names = [("d1", 1, "①1台選ぶ"), ("d2", 2, "②2台選んで少ない方"), ("d3", 3, "③3台選んで少ない方"), ("all", 0, "④全部の台を見る")]
    for key, d, lab in names:
        rg = np.random.default_rng([SEED, 1, d])
        Rk = R if d != 0 else 50
        ld = place(rg, Rk, N, M, d)
        loads[key] = ld
        base[key] = {"label": lab, "reps": Rk, **summ(ld, N, M)}
    base["reduction_d1_to_d2_excess_pct"] = round((1 - base["d2"]["excess_mean"] / base["d1"]["excess_mean"]) * 100, 2)
    base["reduction_d2_to_d3_excess_pct"] = round((1 - base["d3"]["excess_mean"] / base["d2"]["excess_mean"]) * 100, 2)
    base["d1_formula_guide_excess"] = round(float(np.sqrt(2 * (N / M) * np.log(M))), 3)   # 1台選ぶときの目安（式）
    rows = [{"method": base[k]["label"], **{kk: v for kk, v in base[k].items() if kk != "label"}} for k, _, _ in names]
    pd.DataFrame(rows).to_csv(RES / "base_by_method.csv", index=False)

    # 台ごとの件数の分かれ方（①と②、1,000回×100台）
    bins = np.arange(0, 161)
    hist = pd.DataFrame({"records_on_machine": bins,
                         "d1_share": np.bincount(loads["d1"].ravel(), minlength=161)[:161] / loads["d1"].size,
                         "d2_share": np.bincount(loads["d2"].ravel(), minlength=161)[:161] / loads["d2"].size})
    hist["d1_share"] = hist.d1_share.round(6); hist["d2_share"] = hist.d2_share.round(6)
    hist.to_csv(RES / "machine_load_hist.csv", index=False)
    spread = {k: {"over_110_pct": round(float((loads[k] > 110).mean()) * 100, 2), "under_90_pct": round(float((loads[k] < 90).mean()) * 100, 2)} for k in ["d1", "d2"]}

    # 1回分（data に置く）
    pd.DataFrame({"machine": np.arange(M), "d1_records": loads["d1"][0], "d2_records": loads["d2"][0],
                  "d3_records": loads["d3"][0]}).to_csv(DATA / "machines_one_set.csv", index=False)

    # 件数を知るのが遅れる（②、B件ごとに数え直す。各300回）
    srows = []
    for B in [1, 10, 100, 1000, 10000]:
        rg = np.random.default_rng([SEED, 2, B])
        ld = place(rg, 300, N, M, 2, refresh=B)
        srows.append({"refresh_every": B, **summ(ld, N, M)})
    st = pd.DataFrame(srows)
    st.to_csv(RES / "by_refresh.csv", index=False)

    # 確かめ：台数×1台の平均の件数の12通り（①と②）
    grid = []
    for mm in [10, 100, 1000]:
        for avg in [1, 10, 100, 1000]:
            n = mm * avg
            rk = int(max(20, min(500, 2_000_000 // n)))
            g1 = place(np.random.default_rng([SEED, 3, mm, avg, 1]), rk, n, mm, 1)
            g2 = place(np.random.default_rng([SEED, 3, mm, avg, 2]), rk, n, mm, 2)
            s1, s2 = summ(g1, n, mm), summ(g2, n, mm)
            grid.append({"machines": mm, "average_records": avg, "records": n, "reps": rk,
                         "d1_excess_mean": s1["excess_mean"], "d2_excess_mean": s2["excess_mean"],
                         "d1_max_vs_average": s1["max_vs_average"], "d2_max_vs_average": s2["max_vs_average"],
                         "d1_formula_guide_excess": round(float(np.sqrt(2 * avg * np.log(mm))), 3),
                         "excess_reduction_pct": round((1 - s2["excess_mean"] / s1["excess_mean"]) * 100, 2)})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    robust = {"settings": int(len(gr)),
              "d1_excess_range": [float(gr.d1_excess_mean.min()), float(gr.d1_excess_mean.max())],
              "d2_excess_range": [float(gr.d2_excess_mean.min()), float(gr.d2_excess_mean.max())],
              "reduction_range_pct": [float(gr.excess_reduction_pct.min()), float(gr.excess_reduction_pct.max())],
              "d2_lt_d1_count": int((gr.d2_excess_mean < gr.d1_excess_mean).sum()),
              "d1_max_vs_average_range": [float(gr.d1_max_vs_average.min()), float(gr.d1_max_vs_average.max())],
              "d2_max_vs_average_range": [float(gr.d2_max_vs_average.min()), float(gr.d2_max_vs_average.max())]}

    out_json = {"base": base, "spread": spread, "by_refresh": srows, "robust": robust,
                "setup": {"records": N, "machines": M, "average": N / M, "reps": R, "reps_all": 50, "reps_refresh": 300}}
    json.dump(out_json, open(RES / "a1313_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：台ごとの件数の分かれ方
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    ax.bar(hist.records_on_machine, hist.d1_share * 100, 1.0, color=ORANGE, alpha=0.75, label="①1台選ぶ")
    ax.bar(hist.records_on_machine, hist.d2_share * 100, 1.0, color=BLUE, alpha=0.75, label="②2台選んで少ない方")
    ax.axvline(100, color=GRAY, lw=0.8, ls="--")
    ax.text(101, float(hist.d2_share.max()) * 100 * 0.95, "平均100件", fontsize=8.5)
    ax.set_xlim(55, 150); ax.set_ylim(0, float(hist.d2_share.max()) * 100 * 1.1)
    ax.set_xlabel("1台に置かれた記録の数（件）"); ax.set_ylabel("台の割合（%、1,000回×100台）", fontsize=9.5)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("1万件を100台に置いたとき、台ごとの件数の分かれ方", fontsize=12)
    save(fig, "a1313_hist.png", SRC)

    # 図2：選ぶ台の数と、数え直しの遅れ
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.0), sharey=True)
    ks = ["d1", "d2", "d3", "all"]
    v = [base[k]["excess_mean"] for k in ks]
    axs[0].bar(np.arange(4), v, 0.6, color=[ORANGE, BLUE, GREEN, GRAY])
    for i, val in enumerate(v):
        axs[0].text(i, val + 0.5, f"{val:.2f}", ha="center", fontsize=8.5)
    axs[0].set_xticks(np.arange(4)); axs[0].set_xticklabels(["①1台", "②2台", "③3台", "④全部"], fontsize=9)
    axs[0].set_xlabel("選ぶ台の数", fontsize=9.5)
    axs[0].set_ylabel("いちばん多い1台が平均より多い件数（平均）", fontsize=9)
    axs[0].set_title("選ぶ台の数", fontsize=11)
    xb = np.arange(len(st))
    axs[1].bar(xb, st.excess_mean, 0.6, color=BLUE)
    for i, val in enumerate(st.excess_mean):
        axs[1].text(i, val + 0.5, f"{val:.2f}", ha="center", fontsize=8.5)
    axs[1].axhline(base["d1"]["excess_mean"], color=ORANGE, lw=0.9, ls="--")
    axs[1].text(-0.4, base["d1"]["excess_mean"] + 0.6, "①1台選ぶ", color=ORANGE, fontsize=8.5)
    axs[1].set_xticks(xb); axs[1].set_xticklabels([f"{b:,}件" for b in st.refresh_every], fontsize=8.5)
    axs[1].set_xlabel("②で台ごとの件数を数え直す間隔", fontsize=9.5)
    axs[1].set_title("②の件数を知るのが遅れると", fontsize=11)
    axs[0].set_ylim(0, max(v + list(st.excess_mean)) * 1.15)
    fig.suptitle("1万件・100台（平均100件）。2台選ぶだけで、平均より多い分は大きく減る", fontsize=12, y=1.03)
    save(fig, "a1313_choices_refresh.png", SRC)

    # 図3：12通り
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    gx = np.arange(len(gr))
    for kk in range(3):  # 台数の組ごとに線を切る（組をまたいで線を結ばない）
        sl = slice(kk * 4, kk * 4 + 4)
        ax.plot(gx[sl], gr.d1_excess_mean.values[sl], "o-", color=ORANGE, ms=4, lw=0.9, label="①1台選ぶ" if kk == 0 else None)
        ax.plot(gx[sl], gr.d2_excess_mean.values[sl], "o-", color=BLUE, ms=4, lw=0.9, label="②2台選んで少ない方" if kk == 0 else None)
    ax.set_yscale("log")
    for kk in [4, 8]:
        ax.axvline(kk - 0.5, color=GRAY, lw=0.8, ls=":")
    for kk, mm in enumerate([10, 100, 1000]):
        ax.text(kk * 4 + 1.5, float(gr.d1_excess_mean.max()) * 1.6, f"{mm:,}台", ha="center", fontsize=9)
    ax.set_ylim(0.3, float(gr.d1_excess_mean.max()) * 3)
    ax.set_xticks(gx); ax.set_xticklabels([f"平均{a:,}件" for a in gr.average_records], fontsize=7.5, rotation=45, ha="right")
    ax.set_ylabel("いちばん多い1台が平均より多い件数（対数の目盛り）", fontsize=8.5)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.24))
    ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50, 100, 200]); ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50", "100", "200"]); ax.minorticks_off()
    ax.set_title("①は件数が増えるほど差が開き、②は数件にとどまる（12通り）", fontsize=12)
    save(fig, "a1313_grid.png", SRC, y=-0.3)

    print(json.dumps(out_json, ensure_ascii=False, indent=1))
    print(st.to_string()); print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
