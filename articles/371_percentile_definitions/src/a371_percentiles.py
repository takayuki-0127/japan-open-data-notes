"""371 中央値や90%点は、計算の定義でどれだけ違うのか
架空の処理時間（対数正規）と金額（ガンマ）で、分位点の9つの定義（Hyndman & Fan の型1〜9）を比べる。
乱数の種は 371。SQL（PERCENTILE_CONT／PERCENTILE_DISC）は DuckDB で動かして型7・型1と一致することを確かめる。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, FIG, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 371
METHODS = [("型1", "inverted_cdf", "SQL の PERCENTILE_DISC"),
           ("型2", "averaged_inverted_cdf", "SAS の既定"),
           ("型3", "closest_observation", "いちばん近い順位の値"),
           ("型4", "interpolated_inverted_cdf", "順位 n×p で内分"),
           ("型5", "hazen", "ヘイズン"),
           ("型6", "weibull", "Excel の PERCENTILE.EXC"),
           ("型7", "linear", "SQL の PERCENTILE_CONT、Excel の PERCENTILE.INC、NumPy・pandas の既定"),
           ("型8", "median_unbiased", "Hyndman & Fan が勧める型"),
           ("型9", "normal_unbiased", "正規分布向け")]
NS = [5, 10, 20, 50, 100, 200, 500, 1000]
PS = [0.5, 0.9, 0.95, 0.99]
REP = 2000
SRC = "架空のデータ（作成者が乱数で作成、seed 371）"

DISTS = {"処理時間（対数正規、中央値30秒・σ=1.0）": (lambda r, n: r.lognormal(np.log(30), 1.0, n),
                                          lambda p: float(stats.lognorm(s=1.0, scale=30).ppf(p))),
         "金額（ガンマ、形2・平均5,000円）": (lambda r, n: r.gamma(2.0, 2500, n),
                                    lambda p: float(stats.gamma(a=2.0, scale=2500).ppf(p)))}


def all_defs(x, p):
    return np.array([np.quantile(x, p, method=m) for _, m, _ in METHODS])


def main():
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "rep": REP}

    # --- 1) 例：10件の処理時間 ---
    x10 = np.sort(np.round(rng.lognormal(np.log(30), 1.0, 10), 1))
    ex = pd.DataFrame({"定義": [m[0] for m in METHODS], "使われ方": [m[2] for m in METHODS],
                       "中央値": all_defs(x10, 0.5), "90%点": all_defs(x10, 0.9), "95%点": all_defs(x10, 0.95)})
    ex.to_csv(RES / "example_n10.csv", index=False)
    out["example_values"] = x10.tolist()
    out["example_p90_min_max"] = [float(ex["90%点"].min()), float(ex["90%点"].max())]

    # --- 2) SQL との一致（DuckDB） ---
    con = duckdb.connect()
    big = rng.lognormal(np.log(30), 1.0, 1000)
    con.register("t", pd.DataFrame({"x": big}))
    chk = []
    for p in PS:
        c, d = con.execute(f"SELECT PERCENTILE_CONT({p}) WITHIN GROUP (ORDER BY x), "
                           f"PERCENTILE_DISC({p}) WITHIN GROUP (ORDER BY x) FROM t").fetchone()
        t7, t1 = np.quantile(big, p, method="linear"), np.quantile(big, p, method="inverted_cdf")
        assert abs(c - t7) < 1e-9 and abs(d - t1) < 1e-9, (p, c, t7, d, t1)
        chk.append({"p": p, "PERCENTILE_CONT": c, "型7": t7, "PERCENTILE_DISC": d, "型1": t1})
    pd.DataFrame(chk).to_csv(RES / "sql_check_duckdb.csv", index=False)
    # Excel の2つの関数の式（型7・型6）を素朴に書いて NumPy と比べる
    def inc(x, p):
        x = np.sort(x); h = (len(x) - 1) * p; k = int(np.floor(h)); return x[k] + (h - k) * (x[min(k + 1, len(x) - 1)] - x[k])
    def exc(x, p):
        x = np.sort(x); h = (len(x) + 1) * p
        if h < 1 or h > len(x): return np.nan       # Excel は #NUM! を返す範囲
        k = int(np.floor(h)); return x[k - 1] + (h - k) * (x[min(k, len(x) - 1)] - x[k - 1])
    for p in PS:
        assert abs(inc(big, p) - np.quantile(big, p, method="linear")) < 1e-9
        assert abs(exc(big, p) - np.quantile(big, p, method="weibull")) < 1e-9
    # PERCENTILE.EXC が値を返せない（#NUM!）件数の境目
    out["exc_min_n"] = {str(p): int(np.ceil(round(max(p, 1 - p) / (1 - max(p, 1 - p)), 9))) for p in PS}

    # --- 3) 件数ごとの定義の差 ---
    rows, err = [], []
    for dname, (gen, true_q) in DISTS.items():
        for n in NS:
            v = np.empty((REP, len(PS), len(METHODS)))
            for i in range(REP):
                x = gen(rng, n)
                for j, p in enumerate(PS):
                    v[i, j] = all_defs(x, p)
            for j, p in enumerate(PS):
                spread = (v[:, j].max(1) - v[:, j].min(1)) / np.median(v[:, j], axis=1) * 100
                contdisc = np.abs(v[:, j, 6] - v[:, j, 0]) / v[:, j, 6] * 100
                incexc = np.abs(v[:, j, 6] - v[:, j, 5]) / v[:, j, 6] * 100
                rows.append({"データ": dname, "件数": n, "p": p, "9定義の幅_中央値%": np.median(spread),
                             "9定義の幅_90%点%": np.quantile(spread, 0.9), "幅が1%未満の割合%": (spread < 1).mean() * 100,
                             "CONTとDISCの差_中央値%": np.median(contdisc), "INCとEXCの差_中央値%": np.median(incexc)})
                tq = true_q(p)
                for k, m in enumerate(METHODS):
                    e = v[:, j, k] / tq - 1
                    err.append({"データ": dname, "件数": n, "p": p, "定義": m[0], "偏り%": e.mean() * 100,
                                "RMSE%": np.sqrt((e ** 2).mean()) * 100})
    R = pd.DataFrame(rows); E = pd.DataFrame(err)
    R.round(3).to_csv(RES / "spread_by_n.csv", index=False); E.round(3).to_csv(RES / "error_vs_truth.csv", index=False)

    main_d = list(DISTS)[0]
    need = {}
    for dname in DISTS:
        need[dname] = {}
        for p in PS:
            s = R[(R["データ"] == dname) & (R.p == p)].set_index("件数")["9定義の幅_中央値%"]
            ok = [n for n in NS if s[n] < 1 and all(s[m] < 1 for m in NS if m >= n)]
            need[dname][str(p)] = ok[0] if ok else None
    out["n_for_spread_under_1pct"] = need
    m = R[R["データ"] == main_d]
    out["spread_median_pct_main"] = {str(p): {str(n): round(float(m[(m.p == p) & (m["件数"] == n)]["9定義の幅_中央値%"].iloc[0]), 2)
                                              for n in NS} for p in PS}
    out["cont_vs_disc_median_pct_main"] = {str(p): {str(n): round(float(m[(m.p == p) & (m["件数"] == n)]["CONTとDISCの差_中央値%"].iloc[0]), 2)
                                                    for n in NS} for p in PS}
    out["inc_vs_exc_median_pct_main"] = {str(p): {str(n): round(float(m[(m.p == p) & (m["件数"] == n)]["INCとEXCの差_中央値%"].iloc[0]), 2)
                                                  for n in NS} for p in PS}
    e = E[(E["データ"] == main_d)]
    out["bias_pct_main_p90"] = {str(n): {r["定義"]: round(r["偏り%"], 1) for _, r in e[(e.p == 0.9) & (e["件数"] == n)].iterrows()} for n in [10, 20, 100]}
    out["rmse_pct_main_p90"] = {str(n): {r["定義"]: round(r["RMSE%"], 1) for _, r in e[(e.p == 0.9) & (e["件数"] == n)].iterrows()} for n in [10, 20, 100]}
    out["spread_median_pct_gamma"] = {str(p): {str(n): round(float(R[(R["データ"] == list(DISTS)[1]) & (R.p == p) & (R["件数"] == n)]["9定義の幅_中央値%"].iloc[0]), 2)
                                               for n in NS} for p in PS}
    json.dump(out, open(RES / "a371_main.json", "w"), ensure_ascii=False, indent=1)

    # --- 図1：10件の例 ---
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.barh(range(9), ex["90%点"][::-1], color=[ORANGE if t in ("型1", "型7") else LIGHT for t in ex["定義"][::-1]])
    ax.set_yticks(range(9)); ax.set_yticklabels([f"{a}（{b.split('、')[0]}）" for a, b in zip(ex["定義"][::-1], ex["使われ方"][::-1])], fontsize=9)
    for i, vv in enumerate(ex["90%点"][::-1]): ax.text(vv, i, f" {vv:.1f}", va="center", fontsize=9)
    ax.set_xlabel("90%点（秒）"); ax.set_xlim(0, ex["90%点"].max() * 1.15)
    ax.set_title("同じ10件でも、90%点は定義で変わる")
    save(fig, "a371_example_n10.png", "出典：" + SRC + "。10件の処理時間の90%点を9つの定義で計算。橙は SQL の2つの関数")
    # --- 図2：件数と幅 ---
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    for p, c in zip(PS, [GRAY, BLUE, GREEN, ORANGE]):
        s = m[m.p == p]; ax.plot(s["件数"], s["9定義の幅_中央値%"], "-o", color=c, label={0.5: "中央値", 0.9: "90%点", 0.95: "95%点", 0.99: "99%点"}[p])
    ax.axhline(1, color=INK, lw=0.8, ls="--"); ax.text(NS[-1], 1.05, "1%", ha="right", va="bottom", fontsize=9)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
    ax.set_xlabel("件数"); ax.set_ylabel("9つの定義の幅（最大−最小、値に対する%）"); ax.legend(frameon=False)
    ax.set_title("定義による差は、件数が少なく、端の分位点ほど大きい")
    save(fig, "a371_spread_by_n.png", "出典：" + SRC + "。処理時間（対数正規）を件数ごとに2,000回作り、幅の中央値を示した。縦軸・横軸は対数")
    # --- 図3：真の値との偏り ---
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    w = 0.27
    for i, (n, c) in enumerate(zip([10, 20, 100], [ORANGE, BLUE, GRAY])):
        s = e[(e.p == 0.9) & (e["件数"] == n)]
        ax.bar(np.arange(9) + (i - 1) * w, s["偏り%"], w, color=c, label=f"{n}件")
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(range(9)); ax.set_xticklabels([mm[0] for mm in METHODS])
    ax.set_ylabel("本当の90%点からの偏り（%）"); ax.legend(frameon=False)
    ax.set_title("少ない件数では、どの定義を選ぶかで偏りの向きが変わる")
    save(fig, "a371_bias_p90.png", "出典：" + SRC + "。処理時間（対数正規）の90%点。2,000回の平均を、分布から決まる本当の値と比べた")
    print(json.dumps(out, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
