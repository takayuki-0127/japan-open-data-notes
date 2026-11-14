"""752 先頭に BOM のついた CSV を csv モジュールで読むと、最初の列名が一致せず、何行の売上が黙って集計から落ちるのか

架空の店別・日別の売上を、月ごとの CSV 24本（2024-01〜2025-12）に書き出す。
2025-04 からは書き出しの仕組みが変わり、UTF-8 の BOM（先頭の3バイト EF BB BF）がつく。
  A csv.DictReader（encoding="utf-8"）で読み、row.get("store_id") で店ごとに足す（よくある書き方）
  B 同じく encoding="utf-8-sig" で読む
  C pandas.read_csv、D DuckDB の read_csv
A で店が分からなくなった行・売上と、店のマスタと結べなかった行を数える。seed 752。
"""
import csv, json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店別・日別の売上 CSV（作成者が乱数で作成、seed 752）"
rng = np.random.default_rng(752)
NS = 36
stores = pd.DataFrame({"store_id": [f"S{i:03d}" for i in range(1, NS + 1)],
                       "area": rng.choice(["北", "中", "南"], NS, p=[0.3, 0.4, 0.3])})
stores.to_csv(DATA / "stores.csv", index=False)
size = np.exp(rng.normal(0, 0.4, NS))
months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
BOM_FROM = pd.Timestamp("2025-04-01")
files = []
for m in months:
    days = pd.date_range(m, m + pd.offsets.MonthEnd(0), freq="D")
    rows = []
    for d in days:
        wk = 1.25 if d.dayofweek >= 5 else 1.0
        for i in range(NS):
            v = 180000 * size[i] * wk * rng.lognormal(0, 0.15)
            rows.append((stores.store_id[i], d.strftime("%Y-%m-%d"), int(round(v, -1))))
    df = pd.DataFrame(rows, columns=["store_id", "date", "sales"])
    name = f"sales_{m.strftime('%Y%m')}.csv"
    bom = m >= BOM_FROM
    with open(DATA / name, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
        df.to_csv(f, index=False, lineterminator="\n")
    files.append((name, bom, len(df), int(df.sales.sum())))
F = pd.DataFrame(files, columns=["file", "bom", "rows", "sales"])
master = dict(zip(stores.store_id, stores.area))


def read_dictreader(enc):
    by_store, by_area, unknown_rows, unknown_sales, heads = {}, {}, 0, 0, []
    for name in F.file:
        with open(DATA / name, encoding=enc, newline="") as f:
            r = csv.DictReader(f)
            heads.append(r.fieldnames[0])
            for row in r:
                s = row.get("store_id")          # 列名が "﻿store_id" だと None が返る
                amt = int(row["sales"])
                if s is None:
                    unknown_rows += 1; unknown_sales += amt
                    continue
                by_store[s] = by_store.get(s, 0) + amt
                a = master.get(s)
                by_area[a] = by_area.get(a, 0) + amt
    return by_store, by_area, unknown_rows, unknown_sales, heads


A_store, A_area, A_unk_rows, A_unk_sales, A_heads = read_dictreader("utf-8")
B_store, B_area, B_unk_rows, B_unk_sales, B_heads = read_dictreader("utf-8-sig")
# C pandas
C = pd.concat([pd.read_csv(DATA / n, dtype={"store_id": str}) for n in F.file], ignore_index=True)
# D DuckDB
con = duckdb.connect(); con.execute("SET threads=1")
q = [x for x in (SQL / "02_bom_duckdb.sql").read_text(encoding="utf-8").replace("{DATA}", str(DATA)).split(";") if "SELECT" in x]
D_cols = con.execute(q[0]).df().column_name.tolist()
D_tot = int(con.execute(q[1]).fetchone()[0]); D_unm = int(con.execute(q[2]).fetchone()[0]); assert D_unm == 0
true_total = int(F.sales.sum())
assert sum(B_store.values()) == true_total and B_unk_rows == 0
assert int(C.sales.sum()) == true_total and list(C.columns)[0] == "store_id"
assert D_tot == true_total and D_cols[0] == "store_id"
assert sum(A_store.values()) + A_unk_sales == true_total
bomF = F[F.bom]
assert A_unk_rows == int(bomF.rows.sum())
# 月ごと：A で店ごとに足した合計
mon_A = []
for name, bom, rows, s in files:
    mon_A.append(0 if bom else s)
out = {"files": len(F), "bom_files": int(F.bom.sum()), "bom_from": "2025-04",
       "rows_total": int(F.rows.sum()), "rows_store_unknown_A": A_unk_rows,
       "rows_store_unknown_pct": round(A_unk_rows / F.rows.sum() * 100, 1),
       "sales_total_oku": round(true_total / 1e8, 2),
       "sales_dropped_pct": round(A_unk_sales / true_total * 100, 1),
       "sales_2025_dropped_pct": round(A_unk_sales / int(F[F.file.str.contains("2025")].sales.sum()) * 100, 1),
       "header_first_A_bom_file": repr(A_heads[-1]), "header_len_A_bom_file": len(A_heads[-1]),
       "header_first_A_plain_file": repr(A_heads[0]),
       "error_raised_A": False,
       "yoy_2025_true_pct": round((F[F.file.str.contains("2025")].sales.sum() / F[F.file.str.contains("2024")].sales.sum() - 1) * 100, 1),
       "yoy_2025_A_pct": round((sum(mon_A[12:]) / sum(mon_A[:12]) - 1) * 100, 1),
       "utf8_sig_ok": True, "pandas_ok": True, "duckdb_ok": True}
# 店ごとの見かけ：A はどの店も 2025-04 以降が欠ける
st = pd.DataFrame({"store_id": list(B_store), "true": list(B_store.values())})
st["A"] = st.store_id.map(A_store).fillna(0)
st["ratio"] = st.A / st.true
out["store_ratio_min"] = round(float(st.ratio.min()), 3); out["store_ratio_max"] = round(float(st.ratio.max()), 3)
json.dump(out, open(RES / "a752_main.json", "w"), ensure_ascii=False, indent=1)
F.assign(sales_read_A=mon_A).to_csv(RES / "files.csv", index=False)

# 図1：月ごとの合計
x = months
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.bar(x, F.sales / 1e6, width=20, color=LIGHT, label="本当の売上（utf-8-sig・pandas・DuckDB）")
ax.bar(x, np.array(mon_A) / 1e6, width=20, color=BLUE, label="csv.DictReader（utf-8）で店ごとに足した売上")
ax.axvline(BOM_FROM - pd.Timedelta(days=15), color=ORANGE, lw=1.2, ls="--")
ax.text(BOM_FROM, (F.sales.max() / 1e6) * 1.02, "ここから BOM つき", color=ORANGE, fontsize=9)
ax.set_ylim(0, F.sales.max() / 1e6 * 1.38); ax.set_ylabel("月の売上（百万円）"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title("BOM のついた月は、店の列が見つからず売上がまるごと集計から落ちる")
save(fig, "a752_monthly.png", SRC)
# 図2：列名の見え方
fig, ax = plt.subplots(figsize=(8, 3.2)); ax.axis("off")
lines = [("BOM なしの CSV", A_heads[0], len(A_heads[0]), BLUE), ("BOM つきの CSV（utf-8 で読む）", A_heads[-1], len(A_heads[-1]), ORANGE),
         ("BOM つきの CSV（utf-8-sig で読む）", B_heads[-1], len(B_heads[-1]), GREEN)]
for i, (lab, h, n, c) in enumerate(lines):
    y = 0.8 - i * 0.3
    ax.text(0.0, y, lab, fontsize=11, color=c, transform=ax.transAxes)
    ax.text(0.45, y, f"print → {h}", fontsize=11, transform=ax.transAxes)
    ax.text(0.75, y, f"repr → {h!r}  （{n}文字）", fontsize=10, color=GRAY, transform=ax.transAxes)
ax.set_title("画面では同じ「store_id」に見えるが、BOM つきは見えない1文字が先頭にある")
save(fig, "a752_header.png", SRC)
# 図3：4つの読み方の合計
fig, ax = plt.subplots(figsize=(7.5, 3.6))
labs = ["csv（utf-8）", "csv（utf-8-sig）", "pandas", "DuckDB"]
vals = [sum(A_store.values()), sum(B_store.values()), int(C.sales.sum()), D_tot]
cols = [ORANGE, GREEN, GREEN, GREEN]
ax.bar(labs, np.array(vals) / 1e8, color=cols)
for i, v in enumerate(vals):
    ax.text(i, v / 1e8 + 0.02, f"{v / true_total * 100:.1f}%", ha="center", fontsize=10)
ax.set_ylabel("2年間の売上の合計（億円）")
ax.set_title("pandas と DuckDB は BOM を外して読むが、csv モジュールは外さない")
save(fig, "a752_readers.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
