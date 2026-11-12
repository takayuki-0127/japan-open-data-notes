"""461 区分ごとのユニーク人数を足すと、全体の人数より何%多くなるのか（架空の購買ログ、seed 461）"""
import json
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, BLUE, ORANGE, GRAY, LIGHT, GREEN, save

SRC = "架空の購買ログ（作成者が乱数で作成、seed 461）"
N_CUST, N_DAY, N_STORE, N_DEPT = 20000, 30, 8, 6


def make_log(seed, multi_store=0.10, freq_mean=4.0, n_cust=N_CUST):
    """顧客×日×店×部門の購買ログを作る。multi_store＝ふだんの店以外で買う来店の割合"""
    rng = np.random.default_rng(seed)
    # 来店回数：人によって違う（ガンマ×ポアソン）。月に1回以上来た人だけがログに出る
    lam = rng.gamma(shape=0.8, scale=freq_mean / 0.8, size=n_cust)
    visits = rng.poisson(lam)
    cust = np.repeat(np.arange(n_cust), visits)
    n = cust.size
    day = rng.integers(1, N_DAY + 1, n)
    home = rng.integers(0, N_STORE, n_cust)
    other = (home[cust] + rng.integers(1, N_STORE, n)) % N_STORE
    store = np.where(rng.random(n) < multi_store, other, home[cust])
    # 1回の来店で買う部門の数：1〜3
    k = rng.choice([1, 2, 3], size=n, p=[0.55, 0.30, 0.15])
    rows = np.repeat(np.arange(n), k)
    pref = rng.dirichlet(np.ones(N_DEPT) * 1.5, n_cust)
    dept = np.empty(rows.size, dtype=int)
    # 部門は人ごとの好みで選ぶ（同じ来店の中では重ならないようにする）
    u = rng.random((n, N_DEPT))
    score = np.log(pref[cust] + 1e-12) - np.log(-np.log(u))          # Gumbel-top-k
    order = np.argsort(-score, axis=1)
    pos = np.concatenate([np.arange(x) for x in k])
    dept = order[rows, pos]
    amount = np.round(rng.lognormal(np.log(1200), 0.6, rows.size)).astype(int)
    return pd.DataFrame({"cust_id": cust[rows], "day": day[rows], "store": store[rows] + 1,
                         "dept": dept + 1, "amount": amount})


def ratios(df):
    """足した数÷本当の人数。pandas で出す"""
    total = df.cust_id.nunique()
    week = (df.day - 1) // 7 + 1
    out = {"本当の人数": int(total),
           "日ごとを足す": df.groupby("day").cust_id.nunique().sum() / total,
           "週ごとを足す": df.assign(w=week).groupby("w").cust_id.nunique().sum() / total,
           "店ごとを足す": df.groupby("store").cust_id.nunique().sum() / total,
           "部門ごとを足す": df.groupby("dept").cust_id.nunique().sum() / total,
           "店×部門ごとを足す": df.groupby(["store", "dept"]).cust_id.nunique().sum() / total}
    return out


def main():
    res = {}
    df = make_log(461)
    DATA.mkdir(exist_ok=True)
    df.head(2000).to_csv(DATA / "purchase_log_sample.csv", index=False)
    con = duckdb.connect()
    con.register("log", df)

    # ---- A. 基本の場面：SQL で数える ----
    q = {
        "本当の人数": "SELECT COUNT(DISTINCT cust_id) FROM log",
        "日ごとを足す": "SELECT SUM(n) FROM (SELECT day, COUNT(DISTINCT cust_id) n FROM log GROUP BY day)",
        "週ごとを足す": "SELECT SUM(n) FROM (SELECT (day-1)//7 w, COUNT(DISTINCT cust_id) n FROM log GROUP BY 1)",
        "店ごとを足す": "SELECT SUM(n) FROM (SELECT store, COUNT(DISTINCT cust_id) n FROM log GROUP BY store)",
        "部門ごとを足す": "SELECT SUM(n) FROM (SELECT dept, COUNT(DISTINCT cust_id) n FROM log GROUP BY dept)",
        "店×部門ごとを足す": "SELECT SUM(n) FROM (SELECT store, dept, COUNT(DISTINCT cust_id) n FROM log GROUP BY store, dept)",
        # 先に「人×区分」の表を作ってから数える
        "人×店の表から全体": "SELECT COUNT(DISTINCT cust_id) FROM (SELECT DISTINCT cust_id, store FROM log)",
        "金額：店ごとを足す": "SELECT SUM(a) FROM (SELECT store, SUM(amount) a FROM log GROUP BY store)",
        "金額：全体": "SELECT SUM(amount) FROM log",
        "行数": "SELECT COUNT(*) FROM log",
    }
    sqlv = {k: int(con.execute(v).fetchone()[0]) for k, v in q.items()}
    pr = ratios(df)
    total = sqlv["本当の人数"]
    base = []
    for k in ["日ごとを足す", "週ごとを足す", "店ごとを足す", "部門ごとを足す", "店×部門ごとを足す"]:
        assert abs(sqlv[k] / total - pr[k]) < 1e-12, k                      # SQL と pandas が一致
        base.append({"数え方": k, "足した数": sqlv[k], "本当の人数": total, "倍率": sqlv[k] / total,
                     "上振れ%": (sqlv[k] / total - 1) * 100})
    assert sqlv["人×店の表から全体"] == total
    assert sqlv["金額：店ごとを足す"] == sqlv["金額：全体"]
    base = pd.DataFrame(base)
    base.to_csv(RES / "base_ratios.csv", index=False)
    res["base"] = {"行数": sqlv["行数"], "本当の人数": total, "金額の合計": sqlv["金額：全体"],
                   "金額は足して一致": True,
                   **{r["数え方"]: round(r["倍率"], 4) for _, r in base.iterrows()}}

    # 区分ごとの内訳：何か所使ったか
    ns = df.groupby("cust_id").store.nunique()
    nd = df.groupby("cust_id").dept.nunique()
    nday = df.groupby("cust_id").day.nunique()
    dist = pd.DataFrame({"店": ns.value_counts(normalize=True).sort_index(),
                         "部門": nd.value_counts(normalize=True).sort_index()}).fillna(0)
    dist.index.name = "使った数"
    dist.to_csv(RES / "how_many_used.csv")
    res["base"].update({"2店以上を使った人%": round((ns >= 2).mean() * 100, 1),
                        "2部門以上を使った人%": round((nd >= 2).mean() * 100, 1),
                        "2日以上来た人%": round((nday >= 2).mean() * 100, 1),
                        "1人あたりの店の数": round(ns.mean(), 3), "1人あたりの部門の数": round(nd.mean(), 3),
                        "1人あたりの日数": round(nday.mean(), 3)})
    # 倍率＝1人あたりの平均の区分数、になる
    assert abs(ns.mean() - pr["店ごとを足す"]) < 1e-12 and abs(nd.mean() - pr["部門ごとを足す"]) < 1e-12

    # ---- B. そこから作る指標のずれ（客単価・来店頻度・部門の利用率） ----
    sales = sqlv["金額：全体"]
    visits = int(con.execute("SELECT COUNT(*) FROM (SELECT DISTINCT cust_id, day, store FROM log)").fetchone()[0])
    kpi = []
    for label, denom in [("本当の人数", total), ("日ごとを足した数", sqlv["日ごとを足す"]),
                         ("店ごとを足した数", sqlv["店ごとを足す"]), ("部門ごとを足した数", sqlv["部門ごとを足す"])]:
        kpi.append({"分母": label, "人数": denom, "1人あたりの金額": sales / denom, "1人あたりの来店回数": visits / denom})
    kpi = pd.DataFrame(kpi)
    kpi["金額のずれ%"] = (kpi["1人あたりの金額"] / kpi["1人あたりの金額"].iloc[0] - 1) * 100
    kpi.to_csv(RES / "kpi_by_denominator.csv", index=False)
    res["kpi"] = {r["分母"]: {"1人あたりの金額": round(r["1人あたりの金額"]), "ずれ%": round(r["金額のずれ%"], 1)}
                  for _, r in kpi.iterrows()}
    # 部門の利用率を足すと100%を超える
    share = (df.groupby("dept").cust_id.nunique() / total * 100)
    res["dept_share_sum%"] = round(float(share.sum()), 1)

    # ---- C. 複数利用の割合を変える（各20回） ----
    rows = []
    for ms in [0.0, 0.05, 0.1, 0.25, 0.5, 0.875]:
        for rep in range(20):
            d = make_log(1000 + rep, multi_store=ms)
            r = ratios(d)
            n2 = (d.groupby("cust_id").store.nunique() >= 2).mean() * 100
            rows.append({"ふだんの店以外で買う割合": ms, "rep": rep, "2店以上を使った人%": n2, "店ごとを足す": r["店ごとを足す"]})
    sw = pd.DataFrame(rows)
    sw_m = sw.groupby("ふだんの店以外で買う割合")[["2店以上を使った人%", "店ごとを足す"]].agg(["mean", "std"]).reset_index()
    sw_m.columns = ["ふだんの店以外で買う割合", "2店以上を使った人%", "sd1", "店ごとを足す_倍率", "sd2"]
    sw_m.to_csv(RES / "sweep_multi_store.csv", index=False)
    res["sweep_multi_store"] = {str(r["ふだんの店以外で買う割合"]): {"2店以上%": round(r["2店以上を使った人%"], 1),
                                                           "倍率": round(r["店ごとを足す_倍率"], 3)} for _, r in sw_m.iterrows()}

    # ---- D. 来店の多さを変える（日ごと・週ごとを足す） ----
    rows = []
    for fm in [1.0, 2.0, 4.0, 8.0, 16.0]:
        for rep in range(20):
            r = ratios(make_log(2000 + rep, freq_mean=fm))
            rows.append({"月の来店回数の平均": fm, "日ごとを足す": r["日ごとを足す"], "週ごとを足す": r["週ごとを足す"]})
    fq = pd.DataFrame(rows).groupby("月の来店回数の平均").mean().reset_index()
    fq.to_csv(RES / "sweep_frequency.csv", index=False)
    res["sweep_frequency"] = {str(r["月の来店回数の平均"]): {"日": round(r["日ごとを足す"], 2), "週": round(r["週ごとを足す"], 2)}
                              for _, r in fq.iterrows()}

    # ---- E. 期間を足し上げる：日→週→月、前月との比べ ----
    # 2か月分を作り、来店の回数だけが1.3倍になった月を比べる（人数は同じ集まり）
    rows = []
    for rep in range(20):
        a = make_log(3000 + rep, freq_mean=4.0)
        b = make_log(4000 + rep, freq_mean=5.2)        # 同じ人数の集まりで、来店だけ3割多い月
        rows.append({"本当の人数の変化%": (b.cust_id.nunique() / a.cust_id.nunique() - 1) * 100,
                     "日ごとを足した数の変化%": (b.groupby("day").cust_id.nunique().sum() / a.groupby("day").cust_id.nunique().sum() - 1) * 100})
    mo = pd.DataFrame(rows).mean()
    res["month_change"] = {k: round(float(v), 1) for k, v in mo.items()}

    # ---- F. 合計の照合で気づけるか ----
    chk = {"行数：店ごとを足す＝全体": True, "金額：店ごとを足す＝全体": True,
           "人数：店ごとを足す＝全体": bool(sqlv["店ごとを足す"] == total),
           "人数：日ごとを足す＝全体": bool(sqlv["日ごとを足す"] == total)}
    res["checks"] = chk
    json.dump(res, open(RES / "a461_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))

    # ---- 図 ----
    fig, ax = plt.subplots(figsize=(8, 4.2))
    b = base.iloc[::-1]
    ax.barh(b["数え方"], b["倍率"], color=[ORANGE if v > 1.5 else BLUE for v in b["倍率"]])
    ax.axvline(1, color=GRAY, lw=1)
    for y, v in enumerate(b["倍率"]):
        ax.text(v + 0.05, y, f"{v:.2f}倍", va="center", fontsize=10)
    ax.set_xlabel("足した数 ÷ 本当の人数（1.00なら一致）")
    ax.set_title("区分ごとのユニーク人数を足した数は、本当の人数の何倍か")
    ax.set_xlim(0, base["倍率"].max() * 1.15)
    save(fig, "a461_sum_vs_true.png", SRC)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    ax.plot(sw_m["2店以上を使った人%"], (sw_m["店ごとを足す_倍率"] - 1) * 100, "o-", color=BLUE)
    for _, r in sw_m.iterrows():
        ax.annotate(f"+{(r['店ごとを足す_倍率']-1)*100:.0f}%", (r["2店以上を使った人%"], (r["店ごとを足す_倍率"] - 1) * 100),
                    textcoords="offset points", xytext=(4, 6), fontsize=9)
    ax.set_xlabel("2つ以上の店を使った人の割合（%）"); ax.set_ylabel("店ごとを足した数の上振れ（%）")
    ax.set_title("複数の店を使う人が多いほど")
    ax = axes[1]
    ax.plot(fq["月の来店回数の平均"], fq["日ごとを足す"], "o-", color=ORANGE, label="日ごとを足す")
    ax.plot(fq["月の来店回数の平均"], fq["週ごとを足す"], "s-", color=BLUE, label="週ごとを足す")
    ax.axhline(1, color=GRAY, lw=1); ax.set_xscale("log", base=2)
    ax.set_xticks(fq["月の来店回数の平均"]); ax.set_xticklabels([f"{v:g}" for v in fq["月の来店回数の平均"]])
    ax.set_xlabel("1人あたりの月の来店回数の平均（回）"); ax.set_ylabel("足した数 ÷ 本当の月の人数")
    ax.set_title("よく来る人が多いほど"); ax.legend(frameon=False)
    save(fig, "a461_sweeps.png", SRC)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    ax.bar(["本当の\n人数", "日ごとを\n足した数", "店ごとを\n足した数", "部門ごとを\n足した数"], kpi["1人あたりの金額"], color=[GREEN, ORANGE, BLUE, BLUE])
    for x, v, d in zip(range(4), kpi["1人あたりの金額"], kpi["金額のずれ%"]):
        ax.text(x, v + 100, f"{v:,.0f}円" + ("" if x == 0 else f"\n（{d:+.0f}%）"), ha="center", fontsize=9)
    ax.set_ylabel("1人あたりの金額（円）"); ax.set_title("分母の人数の取り方と、1人あたりの金額")
    ax.set_ylim(0, kpi["1人あたりの金額"].max() * 1.25); ax.tick_params(axis="x", labelsize=9)
    ax = axes[1]
    lab = ["行数", "金額", "人数\n（店ごと）", "人数\n（日ごと）"]
    v = [0, 0, (sqlv["店ごとを足す"] / total - 1) * 100, (sqlv["日ごとを足す"] / total - 1) * 100]
    ax.bar(lab, v, color=[GREEN, GREEN, ORANGE, ORANGE])
    for x, y in enumerate(v):
        ax.text(x, y + 3, "差0（一致）" if y == 0 else f"+{y:.0f}%", ha="center", fontsize=10)
    ax.set_ylabel("区分ごとを足した数と全体の差（%）"); ax.set_title("合計の照合：足して合う数、合わない数")
    ax.set_ylim(0, max(v) * 1.2)
    save(fig, "a461_kpi_and_checks.png", SRC)


if __name__ == "__main__":
    main()
