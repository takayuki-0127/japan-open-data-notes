"""330 同じファイルを2回取り込んでも、数字が二重にならない形はどう作るか
架空の日次売上ファイルを、追記だけ／その日の分を洗い替え／キーで上書き の3つ（＋版を確かめる形）で取り込み、
6つの場面で「二重・欠け・古い値」が何行出るかを数える。DuckDB で実行（T-SQL の MERGE は未検証）。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 330; rng = np.random.default_rng(SEED)
DAYS = pd.date_range("2026-04-01", periods=10).strftime("%Y-%m-%d").tolist(); STORES, ITEMS = 20, 15
def day_file(day, version=1):
    """1日分のファイル：店×商品の行（キー＝日・店・商品）。売れなかった組み合わせは行がない"""
    rows = [(day, s, i, int(rng.integers(1, 40)), version) for s in range(1, STORES + 1) for i in range(1, ITEMS + 1) if rng.random() < 0.8]
    d = pd.DataFrame(rows, columns=["sales_date", "store_id", "item_id", "qty", "file_version"]); d["amount"] = d.qty * (100 + d.item_id * 30); return d
BASE = {d: day_file(d) for d in DAYS}
def corrected(day):          # 訂正版：1割の行の数量が変わる
    d = BASE[day].copy(); d["file_version"] = 2; i = d.sample(frac=0.1, random_state=7).index
    d.loc[i, "qty"] += 3; d["amount"] = d.qty * (100 + d.item_id * 30); return d
def corrected_fewer(day):    # 訂正版：5%の行が取り消されて、ファイルから消える
    d = BASE[day].copy(); d["file_version"] = 2; return d.drop(d.sample(frac=0.05, random_state=8).index)

DDL = """CREATE OR REPLACE TABLE sales (sales_date VARCHAR, store_id INT, item_id INT, qty INT, amount BIGINT, file_version INT{pk});
         CREATE OR REPLACE TABLE load_log (file_name VARCHAR, file_version INT, sales_date VARCHAR, rows INT);"""
class Stop(Exception): pass
def run_file(con, how, f, stop_after=None):
    """1つのファイルを取り込む。stop_after 行で止まる場面も作る"""
    con.register("stg", f); day = f.sales_date.iloc[0]; ver = int(f.file_version.iloc[0])
    part = f"(SELECT * FROM stg LIMIT {stop_after})" if stop_after else "stg"
    cols = "sales_date, store_id, item_id, qty, amount, file_version"
    if how == "A 追記だけ":
        con.sql(f"INSERT INTO sales SELECT {cols} FROM {part}")                       # 止まっても、入った分は残る
    elif how == "B その日の分を洗い替え":
        con.sql("BEGIN"); con.sql(f"DELETE FROM sales WHERE sales_date IN (SELECT DISTINCT sales_date FROM stg)")
        con.sql(f"INSERT INTO sales SELECT {cols} FROM {part}")
        if stop_after: con.sql("ROLLBACK"); raise Stop()
        con.sql("COMMIT")
    elif how == "C キーで上書き":
        con.sql("BEGIN")
        con.sql(f"""INSERT INTO sales SELECT {cols} FROM {part}
                    ON CONFLICT (sales_date, store_id, item_id) DO UPDATE SET qty = excluded.qty, amount = excluded.amount, file_version = excluded.file_version""")
        if stop_after: con.sql("ROLLBACK"); raise Stop()
        con.sql("COMMIT")
    elif how == "D 版を確かめて、その日の分を洗い替え":
        newest = con.sql(f"SELECT coalesce(max(file_version), 0) FROM load_log WHERE sales_date = '{day}'").fetchone()[0]
        if ver < newest: return                                                        # 古い版は入れない
        con.sql("BEGIN"); con.sql(f"DELETE FROM sales WHERE sales_date = '{day}'")
        con.sql(f"INSERT INTO sales SELECT {cols} FROM {part}")
        if stop_after: con.sql("ROLLBACK"); raise Stop()
        con.sql(f"INSERT INTO load_log VALUES ('{day}_v{ver}', {ver}, '{day}', {len(f)})"); con.sql("COMMIT")
    elif how == "E キーで上書き＋版の比較＋古い版の行を消す":
        con.sql("BEGIN")
        con.sql(f"""INSERT INTO sales SELECT {cols} FROM {part}
                    ON CONFLICT (sales_date, store_id, item_id) DO UPDATE SET qty = excluded.qty, amount = excluded.amount, file_version = excluded.file_version
                    WHERE excluded.file_version >= sales.file_version""")                 # 古い版では上書きしない
        con.sql("""DELETE FROM sales USING (SELECT sales_date, max(file_version) AS v FROM stg GROUP BY 1) f
                   WHERE sales.sales_date = f.sales_date AND sales.file_version < f.v""")  # 新しい版に出てこなかった行（取り消し）を消す
        if stop_after: con.sql("ROLLBACK"); raise Stop()
        con.sql("COMMIT")
    if stop_after and how == "A 追記だけ": raise Stop()

def scenario(name):
    """届く順のリスト [(ファイル, 途中で止める行数)] と、最後にあるべき姿を返す"""
    seq = [(BASE[d], None) for d in DAYS]; truth = dict(BASE); d5 = DAYS[4]
    if name == "S1 同じファイルの再送": seq.insert(5, (BASE[d5], None))
    elif name == "S2 途中で止まって流し直し": seq[4:5] = [(BASE[d5], len(BASE[d5]) // 2), (BASE[d5], None)]
    elif name == "S3 訂正版が届く（値が変わる）": c = corrected(d5); seq.insert(7, (c, None)); truth[d5] = c
    elif name == "S4 訂正版が届く（行が減る）": c = corrected_fewer(d5); seq.insert(7, (c, None)); truth[d5] = c
    elif name == "S5 訂正版のあとに古い版が届く": c = corrected(d5); seq.insert(6, (c, None)); seq.insert(8, (BASE[d5], None)); truth[d5] = c
    elif name == "S6 遅れた行が翌日のファイルに入る":
        late = BASE[d5].sample(frac=0.1, random_state=9); f5 = BASE[d5].drop(late.index); f6 = pd.concat([late, BASE[DAYS[5]]], ignore_index=True)
        seq[4] = (f5, None); seq[5] = (f6, None)                                       # 6日目のファイルに、5日目の行が1割まじる
    T = pd.concat(truth.values(), ignore_index=True)
    return seq, T
HOW = ["A 追記だけ", "B その日の分を洗い替え", "C キーで上書き", "D 版を確かめて、その日の分を洗い替え", "E キーで上書き＋版の比較＋古い版の行を消す"]
SCN = ["S1 同じファイルの再送", "S2 途中で止まって流し直し", "S3 訂正版が届く（値が変わる）", "S4 訂正版が届く（行が減る）", "S5 訂正版のあとに古い版が届く", "S6 遅れた行が翌日のファイルに入る"]
K = ["sales_date", "store_id", "item_id"]; out = []
for how in HOW:
    for s in SCN:
        con = duckdb.connect(); con.sql(DDL.format(pk=", PRIMARY KEY (sales_date, store_id, item_id)" if how[0] in "CE" else ""))
        seq, T = scenario(s)
        for f, stop in seq:
            try: run_file(con, how, f, stop)
            except Stop: pass
        got = con.sql("SELECT * FROM sales").df()
        g = got.groupby(K).agg(n=("qty", "size"), amount=("amount", "sum"), last=("amount", "last")).reset_index()
        m = T[K + ["amount"]].merge(g, on=K, how="outer", suffixes=("_t", "_g"), indicator=True)
        dup = int((m.n > 1).sum()); missing = int((m._merge == "left_only").sum()); extra = int((m._merge == "right_only").sum())
        stale = int(((m._merge == "both") & (m.n == 1) & (m.amount_t != m.amount_g)).sum())
        out.append({"取り込み方": how, "場面": s, "二重の行": dup, "欠けた行": missing, "残った行（あるべきでない）": extra, "古い値の行": stale,
                    "おかしい行の合計": dup + missing + extra + stale, "売上合計のずれ（%）": (got.amount.sum() / T.amount.sum() - 1) * 100, "あるべき行数": len(T), "表の行数": len(got)})
res = pd.DataFrame(out); res.to_csv(RES / "scenario_results.csv", index=False)
piv = res.pivot(index="場面", columns="取り込み方", values="おかしい行の合計").loc[SCN, HOW]
pct = res.pivot(index="場面", columns="取り込み方", values="売上合計のずれ（%）").loc[SCN, HOW]
piv.to_csv(RES / "wrong_rows_matrix.csv"); pct.round(3).to_csv(RES / "total_error_matrix.csv")
main = {"days": len(DAYS), "rows_per_day": int(np.mean([len(v) for v in BASE.values()])), "rows_total": int(sum(len(v) for v in BASE.values())),
        "scenarios_with_error": {h: int((piv[h] > 0).sum()) for h in HOW}, "matrix_wrong_rows": piv.to_dict(), "matrix_total_pct": pct.round(3).to_dict(),
        "duckdb_version": duckdb.__version__}
json.dump(main, open(RES / "a330_main.json", "w"), ensure_ascii=False, indent=1)
print(res.drop(columns=["あるべき行数"]).to_string()); print(json.dumps(main["scenarios_with_error"], ensure_ascii=False))

SRC = "架空の日次売上ファイル（作成者が乱数で作成、seed 330）。DuckDB で実行（SQL Server 本体では未検証）"
fig, ax = plt.subplots(figsize=(10.2, 4.2)); M = piv.values.astype(float)
ax.imshow(np.where(M > 0, 1, 0), cmap="Oranges", vmin=0, vmax=2.2, aspect="auto")
kinds = res.set_index(["場面", "取り込み方"])
for i, s in enumerate(SCN):
    for j, h in enumerate(HOW):
        r = kinds.loc[(s, h)]; parts = [f"{n}{int(r[c])}" for c, n in [("二重の行", "二重"), ("欠けた行", "欠け"), ("残った行（あるべきでない）", "残り"), ("古い値の行", "古い値")] if r[c] > 0]
        ax.text(j, i, "ずれ0" if not parts else "・".join(parts), ha="center", va="center", fontsize=9.5, color=INK, weight="bold" if parts else None)
ax.set_xticks(range(5)); ax.set_xticklabels(["A 追記だけ", "B その日の分を\n洗い替え", "C キーで上書き", "D 版を確かめて\n洗い替え", "E 上書き＋版の比較\n＋古い版の行を消す"], fontsize=9.5); ax.xaxis.tick_top()
ax.set_yticks(range(6)); ax.set_yticklabels(SCN, fontsize=10)
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_title("6つの場面で、表におかしい行が何行残ったか（数字は行数）", loc="left", fontsize=11.5, pad=36, x=-0.42)
save(fig, "a330_matrix.png", SRC)
fig, ax = plt.subplots(figsize=(9.4, 4.2)); w = 0.17
for j, (h, c) in enumerate(zip(HOW, [ORANGE, BLUE, GREEN, GRAY, INK])):
    ax.bar(np.arange(6) + (j - 2) * w, pct[h].values, w, color=c, label=h)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(range(6)); ax.set_xticklabels(["S1\n再送", "S2\n途中で止まる", "S3 訂正版\n（値が変わる）", "S4 訂正版\n（行が減る）", "S5 訂正版のあと\nに古い版", "S6 遅れた行が\n翌日のファイルに"], fontsize=9)
ax.set_ylabel("10日分の売上合計のずれ（%）"); ax.legend(frameon=False, fontsize=9, ncol=1, loc="upper left")
ax.set_title("売上の合計で見たずれ：追記だけは再送のたびに二重になり、洗い替えは遅れた行で欠ける", loc="left", fontsize=11.5)
save(fig, "a330_total_error.png", SRC)
tab = pd.DataFrame({"取り込み方": ["A 追記だけ", "B その日の分を洗い替え", "C キーで上書き", "D 版を確かめて洗い替え", "E 上書き＋版の比較\n＋古い版の行を消す"],
                    "ずれた場面（6つ中）": [main["scenarios_with_error"][h] for h in HOW],
                    "前提": ["なし", "ファイルが、その日の全部の行を持つ", "行を1つに決めるキーがある", "ファイルがその日の全部を持ち、\n版の番号が分かる", "キーがあり、行ごとに版の番号を持つ"],
                    "弱いところ": ["再送・流し直しで二重になる", "古い版・日をまたぐ行", "取り消された行が残る・古い版", "日をまたぐ行", "6つの場面では出なかった"]})
tab.replace("\n", "", regex=True).to_csv(RES / "design_summary.csv", index=False)
fig, ax = plt.subplots(figsize=(10.0, 3.6)); ax.axis("off")
t = ax.table(cellText=tab.values, colLabels=["取り込み方", "ずれた場面\n（6つ中）", "前提", "弱いところ"], loc="center", cellLoc="center", colWidths=[0.25, 0.11, 0.34, 0.30])
t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 2.3)
for (r_, c_), cell in t.get_celld().items():
    cell.set_edgecolor("#d0d0d0")
    if r_ == 0: cell.set_facecolor("#eef3fa"); cell.set_text_props(weight="bold")
ax.set_title("取り込み方ごとの、ずれた場面の数・前提・弱いところ", loc="left", fontsize=11.5)
save(fig, "a330_summary.png", SRC, y=0.02)
