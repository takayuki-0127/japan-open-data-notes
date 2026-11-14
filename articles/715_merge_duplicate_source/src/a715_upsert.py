"""715 取り込み元に同じキーが2行ある状態で MERGE（UPSERT）すると、何件の値が意図と違う行で上書きされるのか

架空の顧客表5,000人（会員ランク）と、更新ファイル1,500行。うち250人は2行ある（古い変更と新しい変更）。
ファイルの行の並びを 1) ばらばら 2) 時刻の古い順 3) 時刻の新しい順 の3通りにして、
  A そのまま INSERT … ON CONFLICT DO UPDATE（DuckDB）
  B 最新の1行に絞ってから同じ更新
  C MERGE INTO
を比べ、最新でない値が残った顧客の数を数える。DuckDB（1スレッド）で動かし、結果を pandas で確かめる。seed 715。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の顧客表と更新ファイル（作成者が乱数で作成、seed 715）"
rng = np.random.default_rng(715)
NC, NU, ND = 5000, 1500, 250
RANKS = ["一般", "シルバー", "ゴールド", "プラチナ"]
cust = pd.DataFrame({"customer_id": np.arange(1, NC + 1), "rank_code": rng.choice(RANKS, NC, p=[0.6, 0.25, 0.12, 0.03]),
                     "updated_at": pd.Timestamp("2025-04-01")})
ids = rng.choice(np.arange(1, NC + 301), NU - ND, replace=False)  # 300人は新規
dups = rng.choice(ids, ND, replace=False)
t0 = pd.Timestamp("2025-10-01")
rows = [(i, rng.choice(RANKS), t0 + pd.Timedelta(minutes=int(rng.integers(0, 60 * 24 * 10)))) for i in ids]
for i in dups:  # 同じ顧客の2行目：もう一方より後の時刻・違うランク
    first = [r for r in rows if r[0] == i][0]
    rows.append((i, rng.choice([r for r in RANKS if r != first[1]]), first[2] + pd.Timedelta(minutes=int(rng.integers(5, 60 * 24 * 3)))))
U = pd.DataFrame(rows, columns=["customer_id", "rank_code", "updated_at"])
latest = U.sort_values(["customer_id", "updated_at"]).groupby("customer_id").tail(1).set_index("customer_id").rank_code
orders = {"ばらばら": U.sample(frac=1, random_state=715).reset_index(drop=True),
          "時刻の古い順": U.sort_values(["updated_at", "customer_id"]).reset_index(drop=True),
          "時刻の新しい順": U.sort_values(["updated_at", "customer_id"], ascending=False).reset_index(drop=True)}
orders["ばらばら"].assign(file_row=np.arange(1, NU + 1)).to_csv(DATA / "updates.csv", index=False, date_format="%Y-%m-%d %H:%M")
cust.to_csv(DATA / "customers.csv", index=False, date_format="%Y-%m-%d %H:%M")
parts = (SQL / "02_upsert_duckdb.sql").read_text(encoding="utf-8").split(";")
Q0, QA, QB, QC = [p for p in parts if "SELECT" in p or "MERGE" in p][:4]
res = []
dup_found = None
for name, Uo in orders.items():
    Uo = Uo.assign(file_row=np.arange(1, NU + 1))
    out_row = {"file_order": name}
    for meth, qq in [("A", QA), ("B", QB), ("C", QC)]:
        con = duckdb.connect(); con.execute("SET threads=1")
        con.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, rank_code VARCHAR, updated_at TIMESTAMP)")
        con.register("c0", cust); con.execute("INSERT INTO customers SELECT * FROM c0")
        con.register("updates", Uo)
        if dup_found is None:
            dup_found = int(con.execute(Q0).fetchone()[0])
        try:
            con.execute(qq)
            R = con.execute("SELECT * FROM customers").df().set_index("customer_id").rank_code
            wrong = int((R.loc[latest.index] != latest).sum())
            out_row[meth] = wrong
            if meth == "A":  # ファイルで先に出た行が残る（DuckDB 2.0 で見た動き。決まりとして保証はされていない）
                first = Uo.groupby("customer_id").head(1).set_index("customer_id").rank_code
                assert (R.loc[first.index] == first).all()
            if meth == "B":
                assert wrong == 0 and len(R) == len(set(cust.customer_id) | set(U.customer_id))
        except duckdb.Error as e:
            out_row[meth] = "エラー"; out_row["C_error"] = str(e).split("\n")[0][:120]
    res.append(out_row)
T = pd.DataFrame(res); T.to_csv(RES / "summary.csv", index=False)
assert dup_found == ND
out = {"customers": NC, "update_rows": NU, "duplicated_customers": ND, "duplicates_found_by_sql": dup_found,
       "new_customers_in_file": int((~U.customer_id.isin(cust.customer_id)).groupby(U.customer_id).first().sum()),
       "wrong_values": {r["file_order"]: {"A_on_conflict": r["A"], "B_dedup_latest": r["B"], "C_merge": r["C"]} for r in res},
       "merge_error": res[0].get("C_error"), "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a715_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：ファイルの並びごとの、最新でない値の件数
fig, ax = plt.subplots(figsize=(8, 3.8)); x = np.arange(3)
a = [r["A"] for r in res]; b = [r["B"] for r in res]
ax.bar(x - 0.2, a, 0.4, color=ORANGE, label="そのまま ON CONFLICT DO UPDATE")
ax.bar(x + 0.2, b, 0.4, color=BLUE, label="最新の1行に絞ってから")
for i in range(3):
    ax.text(i - 0.2, a[i] + 3, f"{a[i]}人", ha="center"); ax.text(i + 0.2, b[i] + 3, f"{b[i]}人", ha="center")
ax.set_xticks(x); ax.set_xticklabels(list(orders.keys())); ax.set_ylabel("最新でないランクが残った顧客（人）"); ax.set_ylim(0, ND * 1.15)
ax.legend(frameon=False, fontsize=9); ax.set_title(f"2行ある{ND}人のうち、ファイルの並びしだいで0人〜全員が古い値になる")
save(fig, "a715_wrong.png", SRC)
# 図2：3つの方法の結果（ばらばらの並び）
fig, ax = plt.subplots(figsize=(8, 3.4)); ax.axis("off")
cells = [["そのまま ON CONFLICT DO UPDATE", "エラーなしで終わる", f"{res[0]['A']}人が古い値"],
         ["最新の1行に絞ってから", "エラーなしで終わる", f"{res[0]['B']}人（正しい）"],
         ["MERGE INTO（そのまま）", "エラーで止まる", "更新されない"]]
tb = ax.table(cellText=cells, colLabels=["方法", "動き", "2行ある250人の結果"], loc="center", cellLoc="left")
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 1.8)
ax.set_title("ばらばらの並びのファイル：いちばん困るのは、エラーなしで古い値が残ること", fontsize=11)
save(fig, "a715_methods.png", SRC)
# 図3：2行の時刻の差
d = U[U.customer_id.isin(dups)].sort_values(["customer_id", "updated_at"]).groupby("customer_id").updated_at.agg(lambda s: (s.iloc[-1] - s.iloc[0]).total_seconds() / 3600)
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.hist(d, bins=30, color=LIGHT); ax.set_xlabel("同じ顧客の2行の時刻の差（時間）"); ax.set_ylabel("顧客数")
ax.set_title("同じ顧客の2つの変更は、数分〜3日の間にある（作成者が置いた）")
save(fig, "a715_gap.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
