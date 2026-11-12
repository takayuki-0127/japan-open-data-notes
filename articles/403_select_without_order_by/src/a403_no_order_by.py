"""403 ORDER BY のない SELECT の並びに頼ると、結果はどれだけ再現しないのか
架空の明細100万行で、並びを決めない処理8つを、DuckDB のスレッドの数と「入れた順を保つ」設定を変えて100回ずつ実行する。
SQLite では、索引の有無と表の作り直しで「先頭の1件」が変わるかを見る。
実行ごとに変わること自体が結果なので、DuckDB の回数の表は流すたびに少し変わる（results/*_varies_each_run.*）。
SQL Server では動かしていない（未検証）。"""
import json, sqlite3, hashlib, collections
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 403
SRC = "架空のデータ（作成者が乱数で作成、seed 403）"
rng = np.random.default_rng(SEED)
N, NC, RUNS = 1_000_000, 2000, 100
det = pd.DataFrame({"id": np.arange(1, N + 1), "cust": rng.integers(1, NC + 1, N),
                    "sale_day": rng.integers(0, 365, N), "amount": rng.integers(1, 500, N) * 10})
cust = pd.DataFrame({"cust": np.arange(1, NC + 1), "area": rng.integers(1, 9, NC)})
det.head(5000).to_csv(DATA / "detail_head5000.csv", index=False)

OPS = {
 "①先頭の1件（LIMIT 1）": ("SELECT id FROM detail LIMIT 1", "id=1"),
 "②条件つきの先頭の1件": ("SELECT id FROM detail WHERE amount >= 4900 LIMIT 1", "いちばん小さい id"),
 "③先頭の10件（つないだ後）": ("SELECT d.id FROM detail d JOIN cust c ON c.cust=d.cust WHERE c.area=3 LIMIT 10", "id の小さい10件"),
 "④顧客ごとの最初の1件（first）": ("SELECT SUM(x) FROM (SELECT cust, first(id) AS x FROM detail GROUP BY cust)", "顧客ごとのいちばん小さい id"),
 "⑤連番（ROW_NUMBER() OVER ()）": ("SELECT SUM(CASE WHEN rn=id THEN 0 ELSE 1 END) FROM (SELECT id, ROW_NUMBER() OVER () AS rn FROM detail)", "連番＝id"),
 "⑥集計した後の先頭の5件": ("SELECT cust FROM (SELECT cust, SUM(amount) AS a FROM detail GROUP BY cust) LIMIT 5", "―"),
 "⑦重なりを除いた後の先頭の5件": ("SELECT cust FROM (SELECT DISTINCT cust FROM detail) LIMIT 5", "―"),
 "⑧文字をつなぐ（string_agg）": ("SELECT md5(string_agg(CAST(id AS VARCHAR), ',')) FROM detail WHERE cust=7", "id の小さい順"),
}
EXPECT = {}
EXPECT["①先頭の1件（LIMIT 1）"] = "1"
EXPECT["②条件つきの先頭の1件"] = str(int(det.loc[det.amount >= 4900, "id"].min()))
m = det.merge(cust, on="cust"); EXPECT["③先頭の10件（つないだ後）"] = ",".join(map(str, sorted(m.loc[m.area == 3, "id"])[:10]))
EXPECT["④顧客ごとの最初の1件（first）"] = str(int(det.groupby("cust").id.min().sum()))
EXPECT["⑤連番（ROW_NUMBER() OVER ()）"] = "0"
EXPECT["⑧文字をつなぐ（string_agg）"] = hashlib.md5(",".join(map(str, det.loc[det.cust == 7, "id"])).encode()).hexdigest()

con = duckdb.connect()
con.register("d0", det); con.register("c0", cust)
con.execute("CREATE TABLE detail AS SELECT * FROM d0 ORDER BY id"); con.execute("CREATE TABLE cust AS SELECT * FROM c0 ORDER BY cust")
rows = []
for pio in [True, False]:
    for th in [1, 2, 4, 8]:
        con.execute(f"SET threads={th}"); con.execute(f"SET preserve_insertion_order={'true' if pio else 'false'}")
        for name, (sql, _) in OPS.items():
            out = collections.Counter()
            for _ in range(RUNS):
                r = con.execute(sql).fetchall()
                out[",".join(str(x[0]) for x in r)] += 1
            top = out.most_common(1)[0]
            rows.append({"処理": name, "入れた順を保つ": "する（既定）" if pio else "しない", "スレッド": th, "結果の種類": len(out),
                         "いちばん多い結果と違った回": RUNS - top[1],
                         "期待どおりだった回": out.get(EXPECT[name], 0) if name in EXPECT else None})
duck = pd.DataFrame(rows); duck.to_csv(RES / "duckdb_runs_varies_each_run.csv", index=False)

# ---------------- SQLite：1回ごとには同じだが、索引や表の作り直しで変わる ----------------
sub = det.head(200_000).copy()
def first_rows(setup):
    c = sqlite3.connect(":memory:")
    sub.to_sql("detail", c, index=False)
    for s in setup: c.execute(s)
    q = {"顧客7の先頭の1件": "SELECT id FROM detail WHERE cust=7 LIMIT 1",
         "金額4,900円以上の先頭の1件": "SELECT id FROM detail WHERE amount>=4900 LIMIT 1",
         "顧客7の先頭の3件": "SELECT id FROM detail WHERE cust=7 LIMIT 3",
         "顧客ごとの件数の先頭の3件": "SELECT cust FROM (SELECT cust, COUNT(*) FROM detail GROUP BY cust) LIMIT 3"}
    res = {}
    for k, s in q.items():
        outs = {",".join(str(x[0]) for x in c.execute(s).fetchall()) for _ in range(20)}
        assert len(outs) == 1                                  # 同じ状態なら、20回とも同じ
        res[k] = outs.pop()
    return res
SETUPS = {"索引なし": [],
          "索引（顧客, 金額）": ["CREATE INDEX ix1 ON detail(cust, amount)"],
          "索引（顧客, 日）": ["CREATE INDEX ix2 ON detail(cust, sale_day)"],
          "索引（金額）": ["CREATE INDEX ix3 ON detail(amount)"],
          "表を日の順に作り直した": ["CREATE TABLE d2 AS SELECT * FROM detail ORDER BY sale_day, id", "DROP TABLE detail", "ALTER TABLE d2 RENAME TO detail"],
          "行を消して入れ直した": ["CREATE TABLE keep AS SELECT * FROM detail WHERE id<=1000", "DELETE FROM detail WHERE id<=1000", "INSERT INTO detail SELECT * FROM keep", "DROP TABLE keep"]}
sq = pd.DataFrame({k: first_rows(v) for k, v in SETUPS.items()}).T.reset_index().rename(columns={"index": "表の状態"})
sq.to_csv(RES / "sqlite_first_rows.csv", index=False)
base = sq.iloc[0]
sq_diff = {c: int((sq[c] != base[c]).sum()) for c in sq.columns[1:]}

# ---------------- ORDER BY を足すと ----------------
FIX = {"①": "SELECT id FROM detail ORDER BY id LIMIT 1", "②": "SELECT id FROM detail WHERE amount >= 4900 ORDER BY id LIMIT 1",
       "③": "SELECT d.id FROM detail d JOIN cust c ON c.cust=d.cust WHERE c.area=3 ORDER BY d.id LIMIT 10",
       "④": "SELECT SUM(x) FROM (SELECT cust, MIN(id) AS x FROM detail GROUP BY cust)",
       "⑤": "SELECT SUM(CASE WHEN rn=id THEN 0 ELSE 1 END) FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn FROM detail)",
       "⑧": "SELECT md5(string_agg(CAST(id AS VARCHAR), ',' ORDER BY id)) FROM detail WHERE cust=7"}
con.execute("SET threads=8"); con.execute("SET preserve_insertion_order=false")
fix = []
for k, sql in FIX.items():
    name = next(n for n in OPS if n.startswith(k))
    outs = collections.Counter(",".join(str(x[0]) for x in con.execute(sql).fetchall()) for _ in range(RUNS))
    fix.append({"処理": name, "結果の種類": len(outs), "期待どおりだった回": outs.get(EXPECT[name], 0)})
fix = pd.DataFrame(fix); fix.to_csv(RES / "duckdb_with_order_by.csv", index=False)
assert (fix["結果の種類"] == 1).all() and (fix["期待どおりだった回"] == RUNS).all()

json.dump({"行数": N, "回数": RUNS, "DuckDB": duckdb.__version__, "SQLite": sqlite3.sqlite_version,
           "SQLite_索引なしと違う結果になった状態の数（5つのうち）": sq_diff},
          open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# ---------------- 図 ----------------
names = list(OPS)
def heat(pio, ax, title):
    d = duck[duck["入れた順を保つ"] == pio].pivot(index="処理", columns="スレッド", values="いちばん多い結果と違った回").reindex(names)
    im = ax.imshow(d.values, cmap="Oranges", vmin=0, vmax=100, aspect="auto")
    for i in range(d.shape[0]):
        for j in range(d.shape[1]):
            v = d.values[i, j]; ax.text(j, i, f"{int(v)}", ha="center", va="center", fontsize=9, color="white" if v > 60 else INK)
    ax.set_xticks(range(4)); ax.set_xticklabels([f"{t}" for t in d.columns]); ax.set_xlabel("スレッドの数"); ax.set_title(title, fontsize=11)
    return d
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw={"wspace": .05})
heat("する（既定）", ax[0], "入れた順を保つ設定：する（既定）"); ax[0].set_yticks(range(len(names))); ax[0].set_yticklabels(names, fontsize=9)
heat("しない", ax[1], "入れた順を保つ設定：しない"); ax[1].set_yticks([])
fig.suptitle("100回のうち、いちばん多い結果と違った回数（DuckDB、100万行）", y=1.0)
save(fig, "a403_runs_differ.png", SRC + "。流すたびに回数は少し変わる", y=-0.03)

fig, ax = plt.subplots(figsize=(9.6, 3.6)); ax.axis("off")
tb = ax.table(cellText=sq.iloc[:, 1:].values, rowLabels=sq["表の状態"], colLabels=list(sq.columns[1:]), loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.9)
for (r, c), ce in tb.get_celld().items():
    ce.set_edgecolor("#d0d0d0")
    if r > 1 and c >= 0 and sq.iloc[r - 1, c + 1] != sq.iloc[0, c + 1]: ce.set_facecolor("#fde3d8")
ax.set_title("SQLite（20万行）：同じ SELECT が返した id。色つきは、索引なしのときと違う答え", pad=10)
save(fig, "a403_sqlite_first_rows.png", SRC + "。同じ状態では20回とも同じ答えだった", y=0.02)

fig, ax = plt.subplots(figsize=(8.4, 4.2))
d = duck[(duck["入れた順を保つ"] == "する（既定）")].pivot(index="処理", columns="スレッド", values="期待どおりだった回").reindex([n for n in names if n in EXPECT])
x = np.arange(len(d)); w = .2
for j, (th, c) in enumerate(zip(d.columns, [GRAY, LIGHT, BLUE, ORANGE])):
    ax.bar(x + (j - 1.5) * w, d[th].astype(float), w, color=c, label=f"スレッド{th}")
ax.set_xticks(x); ax.set_xticklabels([n[:1] + n[1:].split("（")[0] for n in d.index], rotation=15, ha="right", fontsize=9)
ax.set_ylabel("100回のうち、期待どおりだった回"); ax.set_title("「入れた順に返るはず」という期待どおりだった回数（既定の設定）"); ax.legend(frameon=False, ncol=4, fontsize=9)
save(fig, "a403_as_expected.png", SRC + "。流すたびに回数は少し変わる", y=-0.08)
print(duck.to_string()); print(sq.to_string()); print(sq_diff); print(fix.to_string())
