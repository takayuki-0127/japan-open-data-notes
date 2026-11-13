"""504 取消された注文を残したまま「初回購入月」を決めると、新規顧客の数は何%多く出るのか（実務の型）

架空の会員と注文（取消・返品・テスト用の会員を含む）を作り、初回購入月を3通りで決めて、
月ごとの新規顧客数と、その後の購入の続き方（継続率の表）を比べる。数字は置いた取消の割合で決まる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 504
SRC = "架空の会員・注文データ（作成者が乱数で作成、seed 504）"
END = pd.Timestamp("2026-03-31")


def make(seed=SEED, n=20000, n_test=60):
    rng = np.random.default_rng(seed)
    rows = []; oid = 0
    join = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 731, n), "D")
    for m, j in enumerate(join):
        t = j + pd.Timedelta(days=int(rng.integers(0, 20)))
        first = True; confirmed_any = False
        loyal = rng.random()
        while t <= END:
            if first:
                st = "取消" if rng.random() < 0.12 else ("返品" if rng.random() < 0.03 else "確定")
            else:
                st = "取消" if rng.random() < 0.05 else ("返品" if rng.random() < 0.03 else "確定")
            rows.append((oid, m, t, st, round(float(rng.lognormal(8.3, 0.6)), -1))); oid += 1
            if first and st == "取消":
                if rng.random() < 0.4:                      # 取消のあと二度と買わない
                    break
                t = t + pd.Timedelta(days=int(rng.integers(1, 60)))   # 1〜60日後に買い直す
                continue
            first = False
            if rng.random() > 0.55 + 0.35 * loyal:          # 買うのをやめる
                break
            t = t + pd.Timedelta(days=int(rng.exponential(45)) + 1)
    for k in range(n_test):                                 # テスト用の会員（社内の確認用）
        m = n + k
        for d in pd.date_range("2024-01-01", END, freq=f"{int(rng.integers(10, 60))}D"):
            rows.append((oid, m, d, "確定", 1000.0)); oid += 1
    o = pd.DataFrame(rows, columns=["order_id", "member", "ordered_at", "status", "amount"])
    o["is_test"] = o["member"] >= n
    return o


RULES = {"all": "全部の注文で決める", "no_cancel": "取消だけ除く", "confirmed": "確定だけ（取消・返品・テストを除く）"}


def first_month(o, rule):
    if rule == "all":
        x = o
    elif rule == "no_cancel":
        x = o[o["status"] != "取消"]
    else:
        x = o[(o["status"] == "確定") & ~o["is_test"]]
    return x.groupby("member")["ordered_at"].min().dt.to_period("M")


def retention(o, fm, k=3):
    """初回月の会員のうち、その後 k か月以内に確定の注文がある割合（購入の続き方）"""
    c = o[(o["status"] == "確定") & ~o["is_test"]].copy()
    c["ym"] = c["ordered_at"].dt.to_period("M")
    c = c.merge(fm.rename("fm"), left_on="member", right_index=True)
    c["age"] = (c["ym"] - c["fm"]).apply(lambda x: x.n)
    rep = c[(c["age"] >= 1) & (c["age"] <= k)].groupby("member").size()
    base = fm.to_frame("fm"); base["rep"] = base.index.isin(rep.index)
    return base.groupby("fm")["rep"].mean()


def main():
    o = make()
    o.to_csv(DATA / "fictional_orders.csv", index=False, date_format="%Y-%m-%d")
    fms = {r: first_month(o, r) for r in RULES}
    new = pd.DataFrame({r: fms[r].value_counts().sort_index() for r in RULES}).fillna(0).astype(int)
    new = new.loc["2024-02":"2025-12"]
    new.to_csv(RES / "new_customers_by_month.csv")
    # DuckDB でも同じ新規数になるか
    con = duckdb.connect(); con.register("orders", o)
    q = open(SQL / "02_first_month_duckdb.sql", encoding="utf-8").read()
    dq = con.sql(q).df().set_index("ym")
    dq.index = pd.PeriodIndex(dq.index, freq="M")
    assert (dq.loc[new.index, "new_confirmed"].values == new["confirmed"].values).all()
    assert (dq.loc[new.index, "new_all"].values == new["all"].values).all()
    out = {"orders": len(o), "members": int(o["member"].nunique()), "status": o["status"].value_counts().to_dict(),
           "test_orders": int(o["is_test"].sum())}
    tot = new.sum()
    out["new_total_2024_02_2025_12"] = tot.to_dict()
    out["over_pct_all_vs_confirmed"] = round(float(tot["all"] / tot["confirmed"] - 1) * 100, 2)
    out["over_pct_nocancel_vs_confirmed"] = round(float(tot["no_cancel"] / tot["confirmed"] - 1) * 100, 2)
    mo = (new["all"] / new["confirmed"] - 1) * 100
    out["monthly_over_pct"] = {"mean": round(float(mo.mean()), 2), "min": round(float(mo.min()), 2), "max": round(float(mo.max()), 2)}
    a, c = fms["all"], fms["confirmed"]
    common = a.index.intersection(c.index)
    out["never_confirmed_counted_new"] = int(len(set(a.index) - set(c.index)) - 60)
    shift = (c.loc[common] != a.loc[common])
    out["first_month_moved_share"] = round(float(shift.mean()) * 100, 2)
    out["first_month_moved_n"] = int(shift.sum())
    lag = (c.loc[common][shift] - a.loc[common][shift]).apply(lambda x: x.n)
    out["moved_by_months"] = lag.value_counts().sort_index().to_dict()
    ret = pd.DataFrame({r: retention(o, fms[r]) for r in RULES}).loc["2024-02":"2025-12"]
    ret = ret.copy()
    fa = fms["all"]; fa2 = fa[fa.index.isin(fms["confirmed"].index)]
    ret["all_without_never_confirmed"] = retention(o, fa2).loc["2024-02":"2025-12"]
    ret.to_csv(RES / "repeat_within_3m.csv")
    out["repeat3m_all_without_never_confirmed"] = round(float(ret["all_without_never_confirmed"].mean()) * 100, 2)
    out["repeat3m_mean"] = {r: round(float(ret[r].mean()) * 100, 2) for r in RULES}
    out["repeat3m_gap_pt"] = {"mean": round(float((ret["confirmed"] - ret["all"]).mean()) * 100, 2),
                              "max": round(float((ret["confirmed"] - ret["all"]).max()) * 100, 2)}
    json.dump(out, open(RES / "a504_main.json", "w"), ensure_ascii=False, indent=1, default=str)
    figs(new, ret, lag)
    print(json.dumps(out, ensure_ascii=False, default=str))


def figs(new, ret, lag):
    x = new.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for r, c in zip(RULES, [ORANGE, GRAY, BLUE]):
        ax.plot(x, new[r], marker="o", ms=3, color=c, label=RULES[r])
    ax.set_ylabel("新規顧客の数（人）"); ax.legend(frameon=False, fontsize=9.5); ax.set_ylim(bottom=0)
    ax.set_title("初回購入月の決め方で、月の新規顧客の数が変わる")
    save(fig, "a504_new.png", SRC)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(x, ret["all"] * 100, marker="o", ms=3, color=ORANGE, label=RULES["all"])
    ax.plot(x, ret["confirmed"] * 100, marker="o", ms=3, color=BLUE, label=RULES["confirmed"])
    ax.plot(x, ret["all_without_never_confirmed"] * 100, ls="--", color=GRAY, label="全部の注文で決め、一度も確定しない会員を除く")
    ax.set_ylabel("3か月以内にもう一度買った割合（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("続いた割合は、2つのずれが打ち消し合って近く見える")
    save(fig, "a504_repeat.png", SRC)
    fig, ax = plt.subplots(figsize=(7.6, 4))
    v = lag.value_counts().sort_index()
    ax.bar(v.index.astype(str), v.values, color=BLUE)
    for i, (k, n) in enumerate(v.items()):
        ax.text(i, n, f"{n:,}", ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("確定だけで決めると、初回購入月が何か月うしろへ動くか"); ax.set_ylabel("会員の数（人）")
    ax.set_title("初回購入月が動いた会員")
    save(fig, "a504_moved.png", SRC)


if __name__ == "__main__":
    main()
