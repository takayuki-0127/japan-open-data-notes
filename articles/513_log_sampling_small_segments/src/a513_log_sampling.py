"""513 ログを10件に1件だけ残して10倍すると、小さな区分の件数はどれだけ振れるのか（実務の型）

架空のイベントログ（約100万件、利用者10万人、区分1,000）を作り、
①イベントごとに 1/k の確率で残す ②利用者ごとに 1/k を選び、その人のイベントをすべて残す
の2通りで間引いて k 倍し、区分ごとの件数とユニーク利用者数を本当の値と比べる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 513
SRC = "架空のイベントログ（作成者が乱数で作成、seed 513）"
KS = [2, 10, 100]
R = 200


def make_log(n_users=100_000, n_cat=1000, n_events=1_000_000, seed=SEED):
    rng = np.random.default_rng(seed)
    act = rng.lognormal(0, 1.2, n_users); act /= act.sum()
    pop = 1 / np.arange(1, n_cat + 1) ** 1.2; pop /= pop.sum()          # 区分の大きさに大小（ジップ型）
    u = rng.choice(n_users, n_events, p=act)
    c = rng.choice(n_cat, n_events, p=pop)
    pairs = pd.DataFrame({"user": u, "cat": c}).value_counts().rename("m").reset_index()
    return pairs, u, c


def run(pairs, n_cat, n_users, seed=SEED + 1):
    rng = np.random.default_rng(seed)
    cat = pairs["cat"].to_numpy(); m = pairs["m"].to_numpy(); usr = pairs["user"].to_numpy()
    true_n = np.bincount(cat, weights=m, minlength=n_cat)
    true_u = np.bincount(cat, minlength=n_cat).astype(float)
    out = {}
    for k in KS:
        en, eu, un, uu = (np.zeros((R, n_cat)) for _ in range(4))
        for r in range(R):
            kept = rng.binomial(m, 1 / k)                                    # ①イベントごと
            en[r] = np.bincount(cat, weights=kept, minlength=n_cat) * k
            eu[r] = np.bincount(cat, weights=(kept > 0), minlength=n_cat) * k
            sel = rng.random(n_users) < 1 / k                                # ②利用者ごと
            s = sel[usr]
            un[r] = np.bincount(cat, weights=m * s, minlength=n_cat) * k
            uu[r] = np.bincount(cat, weights=s.astype(float), minlength=n_cat) * k
        out[k] = {"ev_n": en, "ev_u": eu, "us_n": un, "us_u": uu}
    return true_n, true_u, out


def rel_rmse(est, true):
    return np.sqrt(((est - true) ** 2).mean(axis=0)) / true


def main():
    pairs, u, c = make_log()
    n_cat, n_users = 1000, 100_000
    true_n, true_u, out = run(pairs, n_cat, n_users)
    size_bins = [0, 100, 1000, 10000, 10 ** 7]
    size_lab = ["100件未満", "100〜1,000件", "1,000〜1万件", "1万件以上"]
    grp = pd.cut(true_n, size_bins, labels=size_lab, right=False)
    rows = []
    for k in KS:
        o = out[k]
        for meth, kn, ku in [("イベントごと", "ev_n", "ev_u"), ("利用者ごと", "us_n", "us_u")]:
            rr = rel_rmse(o[kn], true_n); bias_u = (o[ku].mean(axis=0) / true_u - 1)
            zero = (o[kn] == 0).mean(axis=0)
            for g in size_lab:
                ix = (grp == g)
                rows.append({"k": k, "間引き方": meth, "区分の大きさ": g, "区分の数": int(ix.sum()),
                             "件数の相対誤差_中央値": float(np.median(rr[ix])),
                             "0件になる割合": float(zero[ix].mean()),
                             "ユニーク利用者の偏り_中央値": float(np.median(bias_u[ix]))})
    tab = pd.DataFrame(rows); tab.to_csv(RES / "by_size.csv", index=False)
    # 理屈の式：イベントごとの相対誤差 ≒ √((k−1)/n)
    theo = {k: float(np.median(np.sqrt((k - 1) / true_n[(grp == "100〜1,000件")]))) for k in KS}
    # SQL：DuckDB の抜き取り2通り（1回ずつ）
    con = duckdb.connect(); con.execute("SET threads TO 1")   # 抜き取りの seed を毎回同じ結果にするため
    con.register("ev", pd.DataFrame({"user_id": u, "cat": c}))
    sq = con.execute(open(SQL / "02_sampling_duckdb.sql").read()).df()
    sq.to_csv(RES / "duckdb_once.csv", index=False)
    out_j = {"seed": SEED, "イベント": int(true_n.sum()), "利用者": int(pairs["user"].nunique()), "区分": n_cat,
             "区分の件数_最大": int(true_n.max()), "区分の件数_最小": int(true_n.min()),
             "区分の大きさの内訳": grp.value_counts().reindex(size_lab).astype(int).to_dict(),
             "くり返し": R, "式による相対誤差_100〜1000件の中央値": theo, "表": rows,
             "DuckDB_10%抜き取り_合計_イベントごと×10": int(sq["ev_x10"].sum()), "DuckDB_合計_利用者ごと×10": int(sq["user_x10"].sum())}
    json.dump(out_j, open(RES / "a513_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：区分の大きさ × k の相対誤差（イベントごと／利用者ごと）
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=True)
    for ax, meth in zip(axs, ["イベントごと", "利用者ごと"]):
        for k, col, mk in [(2, GRAY, "^"), (10, BLUE, "o"), (100, ORANGE, "s")]:
            t = tab[(tab.k == k) & (tab["間引き方"] == meth)]
            ax.plot(range(4), t["件数の相対誤差_中央値"] * 100, marker=mk, color=col, label=f"{k}件に1件")
            for xi, v in enumerate(t["件数の相対誤差_中央値"] * 100):
                ax.text(xi, v * 1.12, f"{v:.0f}" if v >= 10 else f"{v:.1f}", ha="center", fontsize=7.5, color=col)
        ax.set_yscale("log"); ax.set_xticks(range(4), size_lab, fontsize=8.5)
        ax.set_title(f"{meth}に間引く", fontsize=11)
    axs[0].set_ylabel("件数の相対誤差（%、対数目盛）"); axs[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("小さな区分ほど、間引いて戻した件数は大きく振れる", fontsize=13)
    save(fig, "a513_rel_error.png", SRC + f"。{R}回くり返した相対誤差（二乗平均）の中央値")
    # 図2：0件になる割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xx = np.arange(4); wd = 0.26
    for j, (k, col) in enumerate([(2, GRAY), (10, BLUE), (100, ORANGE)]):
        t = tab[(tab.k == k) & (tab["間引き方"] == "イベントごと")]["0件になる割合"].to_numpy() * 100
        ax.bar(xx + (j - 1) * wd, t, wd, color=col, label=f"{k}件に1件")
        for a, b in zip(xx, t): ax.text(a + (j - 1) * wd, b + 1, f"{b:.0f}", ha="center", fontsize=8)
    ax.set_xticks(xx, size_lab); ax.set_ylabel("間引いたあと0件になる割合（%）")
    ax.set_title("100件に1件にすると、100件未満の区分は半分近くが0件になる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a513_zero.png", SRC + "。イベントごとに間引いた場合")
    # 図3：ユニーク利用者の偏り
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for j, (meth, col) in enumerate([("イベントごと", ORANGE), ("利用者ごと", BLUE)]):
        t = tab[(tab.k == 10) & (tab["間引き方"] == meth)]["ユニーク利用者の偏り_中央値"].to_numpy() * 100
        ax.bar(xx + (j - 0.5) * 0.36, t, 0.36, color=col, label=f"{meth}に間引いて10倍")
        for a, b in zip(xx, t): ax.text(a + (j - 0.5) * 0.36, b + (2 if b >= 0 else -6), f"{b:+.0f}", ha="center", fontsize=8.5)
    ax.axhline(0, color=INK, lw=0.8); ax.set_ylim(-3, 36)
    ax.set_xticks(xx, size_lab); ax.set_ylabel("ユニーク利用者の偏り（%）")
    ax.set_title("イベントごとに間引いて10倍すると、ユニーク利用者は多く出る")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a513_unique_bias.png", SRC + "。10件に1件、200回の平均の偏りの中央値")
    print(tab.to_string()); print(theo); print(sq.head())


if __name__ == "__main__":
    main()
