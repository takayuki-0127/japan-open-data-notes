"""301：毎月の CSV を取り込む4つの形を、同じ24か月の「届き方」で比べる。
A＝型つきの表にそのまま追記／B＝ステージング表で型を確かめて追記し、最後に入れた行を選ぶビューで読む／
C＝ステージング＋型の確認＋キーで入れ替え＋取り込みの記録（トランザクション）／D＝C＋新しい版だけ入れ替える。
検証は DuckDB。T-SQL 版（sql/01_load_tsql.sql）は SQL Server では未検証。
"""
import hashlib, json, shutil
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, GREEN, INK, save

SEED = 301
SRC = "出典：経済産業省「商業動態統計」業態別販売額（232 の写し）をもとに、届き方（速報→確報・再実行・途中の失敗など）を作成者が乱数で作成（seed 301）"
rng = np.random.default_rng(SEED)
truth = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"])
GY = sorted(truth.gyotai.unique())
months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")           # 24回の取り込み
hist = truth[truth.ym < "2023-12-01"]                                      # 2023-11 までは正しく入っている
target = truth[(truth.ym >= "2023-12-01") & (truth.ym <= "2025-12-01")]    # 最後に合っていてほしい範囲

# ---- 届くファイルを作る：当月（速報＝少しずれる）と前月（確報＝正しい値）
IN = DATA / "incoming"; shutil.rmtree(IN, ignore_errors=True); IN.mkdir()
tv = truth.set_index(["gyotai", "ym"]).sales
files = []
for m in months:
    rows = []
    prev = m - pd.DateOffset(months=1)
    for g in GY:
        rows.append((g, prev.strftime("%Y-%m-%d"), str(int(tv[(g, prev)]))))                       # 確報
        prelim = int(round(tv[(g, m)] * (1 + rng.normal(0, 0.004))))                               # 速報
        rows.append((g, m.strftime("%Y-%m-%d"), str(prelim)))
    files.append([m, rows])
# 2025-12 の確報は、最後にもう1回届く（2026-01 分の届け。当月分は範囲外なので入れない）
last = [(g, "2025-12-01", str(int(tv[(g, pd.Timestamp('2025-12-01'))]))) for g in GY]

# ---- 起きること（どれも実際によくある型。月は乱数ではなく固定）
DOUBLE_RUN = {pd.Timestamp("2024-05-01"), pd.Timestamp("2025-03-01")}    # 同じファイルを2回流す
COMMA = pd.Timestamp("2024-09-01")                                        # 数字に桁区切りのコンマ、1つは「-」
FAIL_MID = pd.Timestamp("2025-07-01")                                     # 途中で失敗し、流し直す
for m, rows in files:
    if m == COMMA:
        for i, (g, ym, s) in enumerate(rows):
            rows[i] = (g, ym, f"{int(s):,}")
        g, ym, _ = rows[1]; rows[1] = (g, ym, "-")                        # 1つの業態の速報が「-」

def write(name, rows):
    p = IN / name
    pd.DataFrame(rows, columns=["gyotai", "ym", "sales"]).to_csv(p, index=False)
    return p
paths = [(m, write(f"sales_{m:%Y-%m}.csv", rows)) for m, rows in files] + [(pd.Timestamp("2026-01-01"), write("sales_2026-01.csv", last))]
# 2024-09 のファイルの「直した版」が、2か月後（2024-11 の取り込みのあと）に届く。中身は 2024-09 時点のまま（9月は速報）
v2 = []
for g in GY:
    v2.append((g, "2024-08-01", str(int(tv[(g, pd.Timestamp("2024-08-01"))]))))
    v2.append((g, "2024-09-01", dict(((r[0], r[1]), r[2]) for r in files[8][1]).get((g, "2024-09-01")).replace(",", "")))
g0 = files[8][1][1][0]                                                    # 「-」だった業態の9月の速報を、直した版では数字にする
v2 = [(g, ym, (str(int(round(tv[(g, pd.Timestamp("2024-09-01"))] * 1.003))) if (g == g0 and ym == "2024-09-01") else s)) for g, ym, s in v2]
V2 = write("sales_2024-09_v2.csv", v2)

# ---- 4つの形
def period(p):            # ファイル名から「何月時点の届けか」を取る
    return pd.Timestamp(p.name[6:13] + "-01")

def setup(con):
    for t in "ab":
        con.execute(f"CREATE TABLE sales_{t} (gyotai VARCHAR, ym DATE, sales BIGINT, loaded_file VARCHAR, loaded_seq INT)")
    for t in "cd":
        con.execute(f"CREATE TABLE sales_{t} (gyotai VARCHAR, ym DATE, sales BIGINT, loaded_file VARCHAR, src_period DATE, PRIMARY KEY (gyotai, ym))")
        con.execute(f"CREATE TABLE reject_{t} (loaded_file VARCHAR, gyotai VARCHAR, ym VARCHAR, sales VARCHAR, reason VARCHAR)")
        con.execute(f"CREATE TABLE log_{t} (loaded_file VARCHAR, file_hash VARCHAR, rows_in INT, rows_ok INT, rows_reject INT, rows_skipped_old INT)")
    con.register("hist", hist)
    for t in "ab":
        con.execute(f"INSERT INTO sales_{t} SELECT gyotai, ym, sales, 'history', 0 FROM hist")
    for t in "cd":
        con.execute(f"INSERT INTO sales_{t} SELECT gyotai, ym, sales, 'history', DATE '2023-11-01' FROM hist")
    # B は、キーごとに「最後に入れた行」を選ぶビューで読む
    con.execute("""CREATE VIEW v_b AS SELECT gyotai, ym, sales FROM (
        SELECT *, row_number() OVER (PARTITION BY gyotai, ym ORDER BY loaded_seq DESC) AS rn FROM sales_b) WHERE rn = 1""")

OK = "TRY_CAST(replace(sales, ',', '') AS BIGINT) IS NOT NULL AND TRY_CAST(ym AS DATE) IS NOT NULL"
SEQ = [0]

def load_a(con, p, fail_after=None):
    """A：型つきの表に、そのまま追記する。1行でも型に合わないとファイル全体が失敗。6行ずつ確定（BATCHSIZE に当たる）"""
    df = pd.read_csv(p, dtype=str)
    try:
        typed = pd.DataFrame({"gyotai": df.gyotai, "ym": pd.to_datetime(df.ym), "sales": df.sales.astype("int64")})
    except ValueError:
        return "失敗（型が合わない）"
    for i in range(0, len(typed), 6):
        if fail_after is not None and i >= fail_after:
            return "失敗（途中）"
        chunk = typed.iloc[i:i + 6]; con.register("chunk", chunk)
        con.execute(f"INSERT INTO sales_a SELECT gyotai, ym, sales, '{p.name}', {SEQ[0]} FROM chunk")
    return "ok"

def load_b(con, p, fail_after=None):
    """B：ステージング表（全部文字）に入れ、型に直せる行だけ追記する。6行ずつ確定"""
    con.execute(f"CREATE OR REPLACE TABLE stg AS SELECT * FROM read_csv('{p}', all_varchar=true, header=true)")
    ok = con.execute(f"SELECT gyotai, TRY_CAST(ym AS DATE) AS ym, TRY_CAST(replace(sales, ',', '') AS BIGINT) AS sales FROM stg WHERE {OK}").df()
    for i in range(0, len(ok), 6):
        if fail_after is not None and i >= fail_after:
            return "失敗（途中）"
        chunk = ok.iloc[i:i + 6]; con.register("chunk", chunk)
        con.execute(f"INSERT INTO sales_b SELECT gyotai, ym, sales, '{p.name}', {SEQ[0]} FROM chunk")
    return "ok"

def load_cd(con, p, fail_after=None, t="c"):
    """C・D：ステージング＋型の確認＋キーで入れ替え＋記録。全部を1つのトランザクションで。
    D は、すでに入っている行のほうが新しい届け（src_period が後）なら入れ替えない"""
    h = hashlib.sha256(p.read_bytes()).hexdigest(); per = period(p).strftime("%Y-%m-%d")
    if con.execute(f"SELECT count(*) FROM log_{t} WHERE file_hash = ?", [h]).fetchone()[0]:
        return "飛ばした（同じ中身）"
    con.execute(f"CREATE OR REPLACE TABLE stg AS SELECT * FROM read_csv('{p}', all_varchar=true, header=true)")
    newer = f"AND NOT EXISTS (SELECT 1 FROM sales_{t} x WHERE x.gyotai = stg.gyotai AND x.ym = TRY_CAST(stg.ym AS DATE) AND x.src_period > DATE '{per}')" if t == "d" else ""
    con.execute(f"CREATE OR REPLACE TABLE stg_ok AS SELECT gyotai, TRY_CAST(ym AS DATE) AS ym, TRY_CAST(replace(sales, ',', '') AS BIGINT) AS sales FROM stg WHERE {OK} {newer}")
    con.execute("BEGIN")
    try:
        con.execute(f"INSERT INTO reject_{t} SELECT '{p.name}', gyotai, ym, sales, '数字か日付に直せない' FROM stg WHERE NOT ({OK})")
        con.execute(f"DELETE FROM sales_{t} WHERE (gyotai, ym) IN (SELECT gyotai, ym FROM stg_ok)")
        if fail_after is not None:
            raise RuntimeError("途中で失敗")
        con.execute(f"INSERT INTO sales_{t} SELECT gyotai, ym, sales, '{p.name}', DATE '{per}' FROM stg_ok")
        con.execute(f"""INSERT INTO log_{t} SELECT '{p.name}', '{h}', count(*), (SELECT count(*) FROM stg_ok),
                        count(*) FILTER (WHERE NOT ({OK})), count(*) FILTER (WHERE {OK}) - (SELECT count(*) FROM stg_ok) FROM stg""")
        con.execute("COMMIT"); return "ok"
    except RuntimeError:
        con.execute("ROLLBACK"); return "失敗（途中）→ 元に戻した"

con = duckdb.connect(); setup(con)
LOAD = {"A": load_a, "B": load_b, "C": lambda c, p, fail_after=None: load_cd(c, p, fail_after, "c"),
        "D": lambda c, p, fail_after=None: load_cd(c, p, fail_after, "d")}
READ = {"A": "sales_a", "B": "v_b", "C": "sales_c", "D": "sales_d"}       # 月次レポートが読む先
DES = "ABCD"

# ---- 「その時点で正しい姿」：届いたファイルのうち、いちばん新しい届け（同じなら後に届いたほう）の値。「-」は値なし
expected = {(g, pd.Timestamp(y)): int(s) for g, y, s in zip(hist.gyotai, hist.ym, hist.sales)}
exp_per = {k: pd.Timestamp("2023-11-01") for k in expected}
def apply_expected(p):
    df = pd.read_csv(p, dtype=str); per = period(p)
    for g, ym, s in zip(df.gyotai, df.ym, df.sales):
        k = (g, pd.Timestamp(ym)); v = s.replace(",", "")
        if not v.lstrip("-").isdigit() or v == "-":
            continue
        if k not in exp_per or per >= exp_per[k]:
            expected[k] = int(v); exp_per[k] = per

def mismatch(d):
    got = con.execute(f"SELECT gyotai, ym, sum(sales) AS s, count(*) AS n FROM {READ[d]} WHERE ym >= DATE '2023-12-01' GROUP BY 1, 2").df()
    got = {(g, pd.Timestamp(y)): int(s) for g, y, s in zip(got.gyotai, got.ym, got.s)}
    exp = {k: v for k, v in expected.items() if k[1] >= pd.Timestamp("2023-12-01")}
    return sum(1 for k in set(got) | set(exp) if got.get(k) != exp.get(k))

events, steps = [], []
def run(p, m, tag, fail=None):
    SEQ[0] += 1
    for d in DES:
        events.append((p.name, d, tag, LOAD[d](con, p, fail_after=fail)))

for m, p in paths:
    if m == FAIL_MID:
        run(p, m, "1回目", fail=6); run(p, m, "流し直し")
    else:
        run(p, m, "1回目")
        if m in DOUBLE_RUN:
            run(p, m, "2回目（同じファイル）")
    apply_expected(p)
    if m == pd.Timestamp("2024-11-01"):
        run(V2, m, "直した版（2か月前のファイル）"); apply_expected(V2)
    steps.append({"after": p.name, **{d: mismatch(d) for d in DES}})
pd.DataFrame(events, columns=["file", "design", "run", "result"]).to_csv(RES / "load_events.csv", index=False)
st = pd.DataFrame(steps); st.to_csv(RES / "mismatch_by_step.csv", index=False)

# ---- 最後の姿を、正しい値（確報）と突き合わせる
con.register("target", target)
res = {"files": len(paths) + 1, "runs_per_design": sum(1 for e in events if e[1] == "A"), "keys_expected": int(len(target))}
for d in DES:
    src = READ[d]
    r = {}
    r["steps_with_mismatch"] = int((st[d] > 0).sum()); r["steps"] = int(len(st)); r["max_mismatch_keys"] = int(st[d].max())
    r["final_wrong_keys"] = int(con.execute(f"""SELECT count(*) FROM (SELECT gyotai, ym, sum(sales) AS s FROM {src} GROUP BY 1, 2) q
                                              RIGHT JOIN target tg USING (gyotai, ym) WHERE q.s IS NULL OR q.s <> tg.sales""").fetchone()[0])
    for y in (2024, 2025):
        s = con.execute(f"SELECT sum(sales) FROM {src} WHERE year(ym) = {y}").fetchone()[0]
        r[f"sum_{y}_pct_diff"] = round((s / target[target.ym.dt.year == y].sales.sum() - 1) * 100, 3)
    r["rows_in_table_since_2023_12"] = int(con.execute(f"SELECT count(*) FROM sales_{d.lower()} WHERE ym >= DATE '2023-12-01'").fetchone()[0])
    res[d] = r
# B を、ビューを通さずに表から直接集計した場合
r = {}
r["final_wrong_keys"] = int(con.execute("""SELECT count(*) FROM (SELECT gyotai, ym, sum(sales) AS s FROM sales_b GROUP BY 1, 2) q
                                           RIGHT JOIN target tg USING (gyotai, ym) WHERE q.s IS NULL OR q.s <> tg.sales""").fetchone()[0])
for y in (2024, 2025):
    s = con.execute(f"SELECT sum(sales) FROM sales_b WHERE year(ym) = {y}").fetchone()[0]
    r[f"sum_{y}_pct_diff"] = round((s / target[target.ym.dt.year == y].sales.sum() - 1) * 100, 3)
res["B_without_view"] = r
for t in "cd":
    res[t.upper()]["reject_rows"] = int(con.execute(f"SELECT count(*) FROM reject_{t}").fetchone()[0])
    res[t.upper()]["log_rows"] = int(con.execute(f"SELECT count(*) FROM log_{t}").fetchone()[0])
    res[t.upper()]["rows_skipped_old"] = int(con.execute(f"SELECT coalesce(sum(rows_skipped_old), 0) FROM log_{t}").fetchone()[0])
    res[t.upper()]["skipped_same_file"] = sum(1 for e in events if e[1] == t.upper() and e[3].startswith("飛ばした"))
# 直した版のあと、9月の値がどうなったか（C は速報に戻る）
sep = con.execute("""SELECT 'C' AS d, count(*) FROM sales_c c JOIN target tg USING (gyotai, ym) WHERE ym = DATE '2024-09-01' AND c.sales <> tg.sales
                     UNION ALL SELECT 'D', count(*) FROM sales_d c JOIN target tg USING (gyotai, ym) WHERE ym = DATE '2024-09-01' AND c.sales <> tg.sales""").fetchall()
res["sep2024_wrong_final"] = {k: int(v) for k, v in sep}
# 取り込みのあとの点検（キーの重複）が鳴るか
res["dup_check"] = {d: int(con.execute(f"SELECT count(*) FROM (SELECT gyotai, ym FROM sales_{d.lower()} GROUP BY 1, 2 HAVING count(*) > 1)").fetchone()[0]) for d in DES}
json.dump(res, open(RES / "a301_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1)); print(st.to_string())

COL = {"A": GRAY, "B": ORANGE, "C": GREEN, "D": BLUE}
NAME = {"A": "A そのまま追記", "B": "B 追記＋最後の行を選ぶビュー", "C": "C キーで入れ替え＋記録", "D": "D C＋新しい版だけ入れ替え"}
# ---- 図1：取り込みのたびに、その時点の正しい姿と合わなかったキーの数
fig, ax = plt.subplots(figsize=(8.6, 4.3))
x = np.arange(len(st))
for d in "BCD":
    ax.plot(x, st[d], color=COL[d], lw=4 if d == "B" else 2, alpha=0.55 if d == "B" else 1, marker="o", ms=3.5, label=NAME[d])
ax.set_xticks(x[::3]); ax.set_xticklabels([s[6:13] for s in st.after][::3], rotation=45, fontsize=8)
ax.set_ylabel("合わなかったキーの数（業態×月）"); ax.set_xlabel("取り込んだファイル")
ax.set_title("取り込みのたびに「その時点の正しい姿」と比べる", fontsize=12)
ax.text(0.01, 0.6, "A は2回目から毎回ずれ、最後は144キー（図では省略）", transform=ax.transAxes, fontsize=9, color=GRAY)
ax.legend(frameon=False, fontsize=9, loc="center left")
save(fig, "a301_mismatch_steps.png", SRC, y=-0.12)

# ---- 図2：最後に残ったずれ（確報と違うキー）
fig, ax = plt.subplots(figsize=(8, 4.2))
lab = ["A", "B（ビューなしで集計）", "B", "C", "D"]
v = [res["A"]["final_wrong_keys"], res["B_without_view"]["final_wrong_keys"], res["B"]["final_wrong_keys"], res["C"]["final_wrong_keys"], res["D"]["final_wrong_keys"]]
b = ax.bar(lab, v, color=[GRAY, "#f3b79d", ORANGE, GREEN, BLUE])
for xx, vv in zip(range(5), v):
    ax.text(xx, vv + 1.5, str(vv), ha="center")
ax.set_ylabel(f"確報と違うキーの数（全{res['keys_expected']}）"); ax.set_title("25か月分を取り込み終えたあと、確報と違っていたキー")
save(fig, "a301_final_wrong.png", SRC)

# ---- 図3：起きたことごとに、4つの形で何が残ったか（表）
rowsT = [
    ("毎月の確報（前月の値の直し）", "速報と確報が両方残る", "ビューが新しい行を選ぶ", "確報に入れ替わる", "確報に入れ替わる"),
    ("同じファイルを2回流した", "同じ行が2つずつ入る", "ビューでは1つに見える", "2回目は飛ばす", "2回目は飛ばす"),
    ("桁区切りのコンマと「-」", "ファイル全体が失敗", "「-」の行を黙って落とす", "「-」の行をはじいて記録", "「-」の行をはじいて記録"),
    ("途中で失敗して流し直した", "先に入った行が二重に残る", "ビューでは1つに見える", "失敗した分は元に戻る", "失敗した分は元に戻る"),
    ("2か月前のファイルの直した版", "古い値がさらに足される", "9月が速報に戻る", "9月が速報に戻る", "古い版は入れ替えない"),
]
fig, ax = plt.subplots(figsize=(11.5, 3.3)); ax.axis("off")
tb = ax.table(cellText=rowsT, colLabels=["起きたこと", "A そのまま追記", "B 追記＋ビュー", "C キーで入れ替え＋記録", "D C＋新しい版だけ"],
              loc="center", cellLoc="left", colWidths=[0.21, 0.19, 0.19, 0.2, 0.2])
tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.9)
for (r_, c_), cell in tb.get_celld().items():
    cell.set_edgecolor("#d9d8d2")
    if r_ == 0: cell.set_facecolor("#f0efe9"); cell.set_text_props(weight="bold")
    elif c_ == 4: cell.set_facecolor("#e8f1fc")
ax.set_title("起きたことと、4つの形で残ったもの", pad=4)
save(fig, "a301_incidents.png", SRC, y=0.02)
