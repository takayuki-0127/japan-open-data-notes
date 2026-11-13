"""532 NPS は、回答が50件や200件のとき、本当は同じ店どうしでも何ポイント差が出てしまうのか（実務の型）

本当の回答の分布（0〜10点）がまったく同じ店を考え、回答の件数を変えて NPS（推奨者の割合 − 批判者の割合）を繰り返し計算する。
同じ店どうしの NPS の差の分布と、差が10ポイント以上になる割合を、シミュレーションと式（多項分布の分散）の両方で出す。
20店の架空の回答から店別の NPS を SQL（DuckDB）でも出し、Python と一致するか確かめる。
"""
import json, math
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 532
SRC = "架空の0〜10点の回答（作成者が乱数で作成、seed 532）"
# 本当の分布（0〜10点）：推奨者（9〜10）40%、中立者（7〜8）35%、批判者（0〜6）25% → 本当の NPS = +15
P = np.array([1, 1, 1, 2, 2, 6, 12, 17, 18, 22, 18], float); P /= P.sum()
PP, PD = P[9:].sum(), P[:7].sum()
TRUE_NPS = (PP - PD) * 100
NS = [30, 50, 100, 200, 500, 1000]
REPS = 20000


def nps(scores):
    s = np.asarray(scores)
    return ((s >= 9).mean() - (s <= 6).mean()) * 100


def sim_counts(rng, n, reps):
    """reps 店ぶんの、推奨者・批判者の件数（多項分布）"""
    c = rng.multinomial(n, [PP, 1 - PP - PD, PD], size=reps)
    return (c[:, 0] - c[:, 2]) / n * 100


def sd_formula(n):
    """NPS の標準偏差（ポイント）：分散 = (p+ + p- − (p+ − p-)^2) / n"""
    return math.sqrt((PP + PD - (PP - PD) ** 2) / n) * 100


def main():
    rng = np.random.default_rng(SEED)
    rows, diffs = [], {}
    for n in NS:
        a, b = sim_counts(rng, n, REPS), sim_counts(rng, n, REPS)
        d = a - b; diffs[n] = d
        sdd = sd_formula(n) * math.sqrt(2)
        p10_formula = 2 * (1 - 0.5 * (1 + math.erf(10 / sdd / math.sqrt(2))))
        rows.append({"回答件数": n, "1店のNPSの標準偏差(式,pt)": round(sd_formula(n), 2), "1店のNPSの標準偏差(シミュ,pt)": round(float(a.std()), 2),
                     "差の中央値の絶対値(pt)": round(float(np.median(np.abs(d))), 1), "差の90%点の絶対値(pt)": round(float(np.quantile(np.abs(d), 0.9)), 1),
                     "差が10pt以上の割合(シミュ,%)": round(float((np.abs(d) >= 10).mean() * 100), 1), "差が10pt以上の割合(正規近似,%)": round(p10_formula * 100, 1)})
    tb = pd.DataFrame(rows); tb.to_csv(RES / "gap_by_n.csv", index=False)
    # 差を10ポイント未満に収めたい（9割の確率で）なら何件いるか：正規近似
    need = None
    for n in range(10, 5001):
        if 1.6449 * sd_formula(n) * math.sqrt(2) < 10:
            need = n; break
    # 20店（本当は全部同じ）の架空の回答：50件ずつと200件ずつ
    recs = []
    for n in [50, 200]:
        for st in range(1, 21):
            sc = rng.choice(11, n, p=P)
            recs += [{"n_per_store": n, "store": f"S{st:02d}", "score": int(x)} for x in sc]
    resp = pd.DataFrame(recs); resp.to_csv(DATA / "fictional_responses_20stores.csv", index=False)
    py = resp.groupby(["n_per_store", "store"]).score.apply(nps).rename("nps").reset_index()
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("resp", resp)
    s = con.execute(open(SQL / "02_nps_by_store_duckdb.sql", encoding="utf-8").read()).df()
    m = py.merge(s, on=["n_per_store", "store"], suffixes=("_py", "_sql"))
    sql_ok = bool(len(m) == 40 and np.allclose(m.nps_py, m.nps_sql, atol=1e-9))
    py.round(1).to_csv(RES / "nps_20_identical_stores.csv", index=False)
    rng20 = {int(n): {"min": round(float(g.nps.min()), 1), "max": round(float(g.nps.max()), 1), "range": round(float(g.nps.max() - g.nps.min()), 1)} for n, g in py.groupby("n_per_store")}
    res = {"true_dist_pct": {"推奨者": round(PP * 100, 1), "中立者": round((1 - PP - PD) * 100, 1), "批判者": round(PD * 100, 1)}, "true_nps": round(TRUE_NPS, 1),
           "reps_per_n": REPS, "by_n": rows, "n_needed_90pct_within_10pt": need, "20stores": rng20, "sql_matches_python": sql_ok}
    json.dump(res, open(RES / "a532_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：差の分布（50件と200件）
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    bins = np.arange(-60, 61, 2)
    for n, c in [(50, ORANGE), (200, BLUE)]:
        ax.hist(diffs[n], bins=bins, histtype="stepfilled", alpha=0.45, color=c, density=True, label=f"回答{n}件ずつ")
    for x in (-10, 10):
        ax.axvline(x, color=GRAY, ls="--", lw=1)
    ax.set_xlabel("同じ店どうしの NPS の差（ポイント）"); ax.set_yticks([]); ax.legend(frameon=False)
    ax.set_title("本当は同じ2店でも、NPS はこれだけ離れる")
    save(fig, "a532_diff_hist.png", SRC + "。各20,000組")
    # 図2：件数と、差が10pt以上になる割合
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(tb["回答件数"], tb["差が10pt以上の割合(シミュ,%)"], "o-", color=ORANGE, label="シミュレーション")
    ax.plot(tb["回答件数"], tb["差が10pt以上の割合(正規近似,%)"], "--", color=GRAY, label="式（正規近似）")
    for x, y in zip(tb["回答件数"], tb["差が10pt以上の割合(シミュ,%)"]):
        ax.text(x, y + 2.5, f"{y:.0f}%", ha="center", fontsize=9, color=INK)
    ax.set_xscale("log"); ax.set_xticks(NS, [str(n) for n in NS]); ax.set_ylim(0, 85)
    ax.set_xlabel("1店あたりの回答件数"); ax.set_ylabel("差が10ポイント以上の割合（%）"); ax.legend(frameon=False)
    ax.set_title("同じ店どうしで「10ポイント以上の差」が出る割合")
    save(fig, "a532_share_ge10_by_n.png", SRC)
    # 図3：同じ20店を並べる
    fig, axs = plt.subplots(1, 2, figsize=(8, 4.6), sharex=True)
    for ax, n, c in [(axs[0], 50, ORANGE), (axs[1], 200, BLUE)]:
        g = py[py.n_per_store == n].sort_values("nps")
        ax.hlines(range(20), TRUE_NPS, g.nps, color=LIGHT); ax.plot(g.nps, range(20), "o", color=c)
        ax.axvline(TRUE_NPS, color=INK, lw=1); ax.set_yticks(range(20), g.store, fontsize=7)
        ax.set_title(f"回答{n}件ずつ（幅 {rng20[n]['range']:.0f}pt）", fontsize=11); ax.set_xlabel("NPS")
    fig.suptitle("本当は全部 NPS +15 の20店を、順位表にすると")
    save(fig, "a532_20stores.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
