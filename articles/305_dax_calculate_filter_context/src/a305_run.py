"""305 DAX の CALCULATE は何をしているか。
架空の売上表で、12本のメジャーを「DAX の決まりどおりの読み」と「素朴な読み（WHERE を足すだけ）」の2通りで計算する。
DAX そのものは実行していない。決まりどおりの読みは (1) フィルターの入れ替えを模した小さな関数 と (2) 1本ずつ手で書いた SQL の2通りで出し、一致を確かめる。
"""
import json
import duckdb, numpy as np, pandas as pd
from common import DATA, RES

rng = np.random.default_rng(305)
REG = {"関東": 6, "関西": 4, "九州": 2}
stores = pd.DataFrame([(f"S{i:02d}", r) for i, r in enumerate([r for r, n in REG.items() for _ in range(n)], 1)],
                      columns=["store", "region"])
CATS = ["食品", "飲料", "日用品", "衣料"]
base = {"食品": 9000, "飲料": 4000, "日用品": 6000, "衣料": 12000}
rows = []
for y in (2024, 2025):
    for m in range(1, 13):
        for s, r in stores.itertuples(index=False):
            for c in CATS:
                n = rng.poisson(14 if r == "関東" else 10)
                amt = np.round(rng.lognormal(np.log(base[c]), 0.6, n) * (1.06 if y == 2025 else 1.0), -1).astype(int)
                rows += [(y, m, s, c, int(a)) for a in amt]
sales = pd.DataFrame(rows, columns=["year", "month", "store", "category", "amount"])
sales.to_csv(DATA / "sales.csv", index=False); stores.to_csv(DATA / "stores.csv", index=False)
f = sales.merge(stores, on="store")  # 事実表に店の地域をつないだ形（DAX では関係でつながる）

# ---- いまのセル（評価する場所）：スライサー 年=2025・地域=関東、行=日用品 ----
SLICER = {"year": {2025}, "region": {"関東"}}
CELL = {**SLICER, "category": {"日用品"}}
DOM = {c: set(f[c].unique()) for c in ["year", "region", "category", "store"]}


def rows_of(ctx, extra=None):
    m = np.ones(len(f), bool)
    for col, vals in ctx.items():
        m &= f[col].isin(vals).to_numpy()
    if extra is not None:
        m &= extra
    return f[m]


def total(ctx, extra=None):
    return int(rows_of(ctx, extra)["amount"].sum())


# 決まりどおりの読み：CALCULATE の条件は「同じ列の絞り込みを入れ替える」。KEEPFILTERS は重ねる。ALL は外す。
def replace(ctx, **new):  # T[col] = v  →  FILTER(ALL(T[col]), …) と同じ。その列の絞り込みを上書き
    return {**ctx, **{k: set(v) for k, v in new.items()}}


def keep(ctx, **new):  # KEEPFILTERS：いまの絞り込みと重ねる
    out = dict(ctx)
    for k, v in new.items():
        out[k] = out.get(k, DOM[k]) & set(v)
    return out


def remove(ctx, *cols):  # ALL(T[col]) / REMOVEFILTERS：その列の絞り込みを外す
    return {k: v for k, v in ctx.items() if k not in cols}


def avg_per_store(ctx, transition):
    st = rows_of(remove(ctx, "category", "year"))["store"].unique()  # 店の表は地域のスライサーだけで絞られる
    if transition:  # メジャー参照 → 行ごとに CALCULATE がかかる（行が絞り込みに変わる）
        v = [total(replace(ctx, store=[s])) for s in st]
        v = [x for x in v if x != 0]
    else:  # SUM をそのまま書く → 行ごとに絞られず、どの行でも同じ合計
        v = [total(ctx) for _ in st]
    return int(round(float(np.mean(v))))


big = (f["amount"] > 20000).to_numpy()
one_store = {**CELL, "store": {"S02"}}  # スライサーで関東の1店だけを選んだ場合（M10 用）

M = [  # (番号, DAX, 決まりどおり, 素朴な読み, ひとこと)
 ("M01", "SUM ( Sales[amount] )", total(CELL), total(CELL), "何も変えない"),
 ("M02", 'CALCULATE ( [売上], Product[category] = "食品" )', total(replace(CELL, category=["食品"])), total(keep(CELL, category=["食品"])), "同じ列：行の「日用品」を「食品」に入れ替える"),
 ("M03", 'CALCULATE ( [売上], KEEPFILTERS ( Product[category] = "食品" ) )', total(keep(CELL, category=["食品"])), total(keep(CELL, category=["食品"])), "KEEPFILTERS：重ねる（日用品かつ食品＝空）"),
 ("M04", 'CALCULATE ( [売上], Store[region] = "関西" )', total(replace(CELL, region=["関西"])), total(keep(CELL, region=["関西"])), "同じ列：スライサーの「関東」を「関西」に入れ替える"),
 ("M05", "CALCULATE ( [売上], 'Date'[year] = 2024 )", total(replace(CELL, year=[2024])), total(keep(CELL, year=[2024])), "同じ列：スライサーの2025年を2024年に入れ替える"),
 ("M06", "CALCULATE ( [売上], ALL ( Product[category] ) )", total(remove(CELL, "category")), total(CELL), "行の絞り込みを外す（全カテゴリ）"),
 ("M07", "DIVIDE ( [売上], CALCULATE ( [売上], ALL ( Product[category] ) ) )", round(total(CELL) / total(remove(CELL, "category")), 4), 1.0, "構成比の分母"),
 ("M08", "CALCULATE ( [売上], ALL ( Sales ) )", total({}), total(CELL), "スライサーも含めて全部外す"),
 ("M09", "CALCULATE ( [売上], FILTER ( Sales, Sales[amount] > 20000 ) )", total(CELL, big), total(CELL, big), "表の FILTER：いまの絞り込みの中で絞る"),
 ("M10", 'CALCULATE ( [売上], Store[region] = "関西" )　※スライサーが店（S02）のとき', total(replace(one_store, region=["関西"])), total(keep(one_store, region=["関西"])), "違う列：店の絞り込みは残るので、関東の店かつ関西＝空"),
 ("M11", "AVERAGEX ( Store, [売上] )", avg_per_store(CELL, True), avg_per_store(CELL, True), "メジャー参照：行ごとに絞られて店の平均になる"),
 ("M12", "AVERAGEX ( Store, SUM ( Sales[amount] ) )", avg_per_store(CELL, False), avg_per_store(CELL, True), "SUM を直接書く：行ごとに絞られず、全店の合計のまま"),
]
df = pd.DataFrame(M, columns=["id", "dax", "correct", "naive", "note"])
# もう1つの単純な読み：「CALCULATE の条件は、いつも前の絞り込みを入れ替える」
NB = {"M03": total(replace(CELL, category=["食品"])),            # KEEPFILTERS を無視して入れ替えると読む
      "M09": total(remove(CELL, "category", "year", "region"), big),  # 表の FILTER も全部入れ替えると読む
      "M10": total(replace(remove(one_store, "store"), region=["関西"]))}  # 店の絞り込みも入れ替わると読む
df["naive_b"] = [NB.get(i, c) for i, c in zip(df["id"], df["correct"])]

# ---- 同じ数字を、1本ずつ手で書いた SQL で出す（決まりどおりの読みの照合） ----
con = duckdb.connect(); con.register("f", f)
S = "SELECT COALESCE(SUM(amount),0) FROM f WHERE "
SQL = {
 "M01": S + "year=2025 AND region='関東' AND category='日用品'",
 "M02": S + "year=2025 AND region='関東' AND category='食品'",
 "M03": S + "year=2025 AND region='関東' AND category='日用品' AND category='食品'",
 "M04": S + "year=2025 AND region='関西' AND category='日用品'",
 "M05": S + "year=2024 AND region='関東' AND category='日用品'",
 "M06": S + "year=2025 AND region='関東'",
 "M07": "SELECT ROUND(SUM(CASE WHEN category='日用品' THEN amount END)*1.0/SUM(amount),4) FROM f WHERE year=2025 AND region='関東'",
 "M08": "SELECT SUM(amount) FROM f",
 "M09": S + "year=2025 AND region='関東' AND category='日用品' AND amount>20000",
 "M10": S + "year=2025 AND store='S02' AND region='関西' AND category='日用品'",
 "M11": "SELECT CAST(ROUND(AVG(s)) AS BIGINT) FROM (SELECT store, SUM(amount) s FROM f WHERE year=2025 AND region='関東' AND category='日用品' GROUP BY store)",
 "M12": S + "year=2025 AND region='関東' AND category='日用品'",
}
df["sql_value"] = [con.execute(SQL[i]).fetchone()[0] for i in df["id"]]
df["sql_matches"] = [abs(float(a) - float(b)) < 1e-9 for a, b in zip(df["correct"], df["sql_value"])]
df["naive_wrong"] = [abs(float(a) - float(b)) > 1e-9 for a, b in zip(df["correct"], df["naive"])]
df["naive_b_wrong"] = [abs(float(a) - float(b)) > 1e-9 for a, b in zip(df["correct"], df["naive_b"])]
df["sql"] = [SQL[i] for i in df["id"]]
df.to_csv(RES / "measures.csv", index=False)
(RES.parent / "sql" / "measures.sql").write_text("\n".join(f"-- {i}\n{q};" for i, q in SQL.items()) + "\n", encoding="utf-8")
(RES.parent / "dax" / "measures.dax").write_text(
    "// 実行していない（Power BI がないため未検証）。[売上] = SUM ( Sales[amount] )\n" +
    "\n".join(f"// {r.id}：{r.note}\n{r.id} = {r.dax.split('　')[0]}" for r in df.itertuples()) + "\n", encoding="utf-8")

# 構成比（M07）を4カテゴリで：ALL と ALLSELECTED の違いは、行の外（スライサー）を残すかどうか
share = []
for c in CATS:
    cell = {**SLICER, "category": {c}}
    share.append((c, total(cell), total(remove(cell, "category")), total({}), round(total(cell) / total(remove(cell, "category")), 4), round(total(cell) / total({}), 4)))
pd.DataFrame(share, columns=["category", "sales", "den_all_category", "den_all_sales", "share_all_category", "share_all_sales"]).to_csv(RES / "share_by_category.csv", index=False)

summ = {"rows": len(sales), "stores": len(stores), "cell": "年=2025・地域=関東・行=日用品",
        "n_measures": len(df), "n_naive_wrong": int(df["naive_wrong"].sum()), "wrong_ids": df.loc[df["naive_wrong"], "id"].tolist(),
        "n_naive_b_wrong": int(df["naive_b_wrong"].sum()), "wrong_b_ids": df.loc[df["naive_b_wrong"], "id"].tolist(),
        "sql_all_match": bool(df["sql_matches"].all()),
        "values": {r.id: {"correct": r.correct, "naive": r.naive, "naive_b": r.naive_b} for r in df.itertuples()}}
json.dump(summ, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(summ, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
