"""312 SQL の NULL は、集計をどれだけ黙ってずらすのか
架空の顧客・注文に NULL を一定の割合で入れ、NULL を気にせず書いた14本と、扱いを書いた14本を比べる"""
import json, re
import numpy as np, pandas as pd, duckdb
from common import SQL, RES, tsql_to_duckdb

SEED = 312
N_CUST, N_ORD, N_STORE = 20_000, 60_000, 40
REGIONS = ["関東", "関西", "中部", "九州"]


def make(rate, seed=SEED):
    """rate＝NULL の割合の倍率（1.0 が基本の置き方）"""
    rng = np.random.default_rng(seed)
    cust = pd.DataFrame({"customer_id": np.arange(1, N_CUST + 1),
                         "last_name": rng.choice(["佐藤", "鈴木", "高橋", "田中", "伊藤"], N_CUST),
                         "first_name": rng.choice(["太郎", "花子", "次郎", "美咲", "健"], N_CUST),
                         "region": rng.choice(REGIONS, N_CUST, p=[.4, .25, .2, .15]),
                         "birth_year": rng.integers(1950, 2006, N_CUST).astype(float)})
    # 注文：顧客の7割だけが注文する。金額と割引
    buyers = rng.choice(cust.customer_id.values, int(N_CUST * 0.7), replace=False)
    od = pd.DataFrame({"order_id": np.arange(1, N_ORD + 1), "customer_id": rng.choice(buyers, N_ORD).astype(float),
                       "store_code": [f"S{n:02d}" for n in rng.integers(1, N_STORE + 1, N_ORD)],
                       "amount": rng.lognormal(8.3, 0.6, N_ORD).round(-1).astype(int)})
    disc = np.where(rng.random(N_ORD) < 0.30, rng.choice([100, 300, 500, 1000], N_ORD), 0).astype(float)
    od["discount"] = disc
    # 返品：40店のうち一部の店にだけある
    rstores = [f"S{n:02d}" for n in range(1, N_STORE + 1) if n % 4 != 0]
    ret = od[od.store_code.isin(rstores)].sample(frac=0.03, random_state=seed)[["store_code", "amount"]].reset_index(drop=True)
    targets = pd.DataFrame({"region": REGIONS, "target": [300, 200, 150, 100]})
    # --- NULL を入れる（基本の割合 × rate）---
    u = lambda n: rng.random(n)
    cust.loc[u(N_CUST) < 0.05 * rate, "region"] = None          # 地域が未入力
    cust.loc[u(N_CUST) < 0.12 * rate, "birth_year"] = np.nan     # 生年が未入力
    cust.loc[u(N_CUST) < 0.04 * rate, "first_name"] = None       # 名が未入力（法人など）
    od.loc[(od.discount == 0) & (u(N_ORD) < 0.5 * rate), "discount"] = np.nan   # 割引なしを NULL で持つ行
    od.loc[u(N_ORD) < 0.06 * rate, "customer_id"] = np.nan      # 会員でない人の注文
    return cust, od, ret, targets


def blocks(path):
    out = {}
    for b in re.split(r"-- name: ", (SQL / path).read_text(encoding="utf-8"))[1:]:
        name, body = b.split("\n", 1); out[name.strip()] = body.strip()
    return out


def to_duck(q):
    q = tsql_to_duckdb(q).replace("dbo.", "")
    return q.replace("c.last_name + ' ' + c.first_name", "c.last_name || ' ' || c.first_name")   # T-SQL の + は DuckDB では ||


def truth(cust, od, ret, targets):
    """直した書き方が出すはずの値を、pandas で別に計算する"""
    d0 = od.discount.fillna(0)
    sales = od.groupby("store_code").amount.sum(); rt = ret.groupby("store_code").amount.sum().reindex(sales.index).fillna(0)
    return {"Q01": d0.mean(), "Q02": (od.amount - d0).sum(), "Q03": len(od),
            "Q04": (~cust.customer_id.isin(od.customer_id.dropna())).sum(), "Q05": (cust.region != "関東").sum(),
            "Q06": (d0 <= 100).sum(), "Q07": (2026 - cust.birth_year).mean(), "Q08": len(cust),
            "Q09": od.amount.sum(), "Q10": (sales - rt).sum(),
            "Q11": len(cust), "Q12": (od.discount > 0).sum(), "Q13": cust.region.isin(["関西", "中部"]).sum(), "Q14": cust.birth_year.max()}


def run_all(rate, seed=SEED):
    cust, od, ret, targets = make(rate, seed)
    con = duckdb.connect()
    for n, df in [("customers", cust), ("orders", od), ("returns", ret), ("region_targets", targets)]:
        con.register(n + "_df", df); con.execute(f"CREATE TABLE {n} AS SELECT * FROM {n}_df")
    nv, fx, tr = blocks("naive.sql"), blocks("fixed.sql"), truth(cust, od, ret, targets)
    rows = []
    for name in nv:
        a = con.execute(to_duck(nv[name])).fetchone()[0]; b = con.execute(to_duck(fx[name])).fetchone()[0]
        t = float(tr[name[:3]])
        assert b is not None and abs(float(b) - t) <= 1e-6 * max(1, abs(t)), (name, b, t)
        a_ = float("nan") if a is None else float(a)
        rows.append({"書き方": name, "NULLを気にしない": a_, "扱いを書いた": float(b),
                     "差(%)": round((a_ / float(b) - 1) * 100, 2) if b else float("nan"), "ずれた": int(a is None or abs(a_ - float(b)) > 1e-9 * max(1, abs(float(b))))})
    info = {"地域がNULLの顧客(%)": round(cust.region.isna().mean() * 100, 2), "生年がNULLの顧客(%)": round(cust.birth_year.isna().mean() * 100, 2),
            "名がNULLの顧客(%)": round(cust.first_name.isna().mean() * 100, 2), "割引がNULLの注文(%)": round(od.discount.isna().mean() * 100, 2),
            "顧客番号がNULLの注文(%)": round(od.customer_id.isna().mean() * 100, 2),
            "返品のない店": int(od.store_code.nunique() - ret.store_code.nunique())}
    return pd.DataFrame(rows), info


def main():
    base, info = run_all(1.0)
    base.to_csv(RES / "ten_queries.csv", index=False)
    sweep = []
    for rate in [0, 0.02, 0.1, 0.25, 0.5, 1.0, 1.5]:
        df, inf = run_all(rate)
        for _, r in df.iterrows():
            sweep.append({"NULLの倍率": rate, "書き方": r["書き方"], "差(%)": r["差(%)"], "ずれた": r["ずれた"]})
    sweep = pd.DataFrame(sweep); sweep.to_csv(RES / "null_rate_sweep.csv", index=False)
    # seed を変えても、ずれる本数は同じか
    seeds = [int(run_all(1.0, s)[0]["ずれた"].sum()) for s in range(312, 322)]
    # 顧客番号が NULL の注文が1件だけのとき、NOT IN はどうなるか
    cust, od, ret, targets = make(0.0); od.loc[0, "customer_id"] = np.nan
    con = duckdb.connect(); con.register("c_df", cust); con.register("o_df", od)
    con.execute("CREATE TABLE customers AS SELECT * FROM c_df"); con.execute("CREATE TABLE orders AS SELECT * FROM o_df")
    nv, fx = blocks("naive.sql"), blocks("fixed.sql"); k = "Q04_一度も注文していない顧客の数（NOT IN）"
    one = {"NOT IN": int(con.execute(to_duck(nv[k])).fetchone()[0]), "NOT EXISTS": int(con.execute(to_duck(fx[k])).fetchone()[0])}
    summary = {"seed": SEED, "顧客": N_CUST, "注文": N_ORD, "店": N_STORE, "NULLの割合（基本）": info,
               "ずれた本数(14本中)": int(base["ずれた"].sum()),
               "倍率ごとのずれた本数": {str(k): int(v) for k, v in sweep.groupby("NULLの倍率")["ずれた"].sum().items()},
               "seedを10通りに変えたときのずれた本数": seeds,
               "NULLが1件だけのときのQ04": one}
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.set_option("display.width", 200); print(base.to_string()); print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(sweep.pivot(index="書き方", columns="NULLの倍率", values="差(%)").to_string())


if __name__ == "__main__":
    main()
