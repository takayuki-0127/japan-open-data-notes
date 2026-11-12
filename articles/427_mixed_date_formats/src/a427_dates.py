"""427 「2025/1/5」「R7.1.5」「20250105」が混ざった日付の列は、機械に読ませると何件が別の日になるのか
架空の入力2万件（書き方10種類）。乱数の種は427。"""
import json, re, datetime as dt
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(427)
N = 20_000
SRC = "出所：架空のデータ（作成者が乱数で作成、seed 427）"
ERAS = [("令和", "R", dt.date(2019, 5, 1)), ("平成", "H", dt.date(1989, 1, 8))]


def wareki(d, long):
    for name, ab, st in ERAS:
        if d >= st:
            y = d.year - st.year + 1
            if long:
                return f"{name}{'元' if y == 1 else y}年{d.month}月{d.day}日"
            return f"{ab}{y}.{d.month}.{d.day}"


STY = {  # 書き方：(名前, 割合, 入力元, 関数)
    "A": ("2025/1/5", .30, "JP", lambda d: f"{d.year}/{d.month}/{d.day}"),
    "B": ("2025-01-05", .20, "JP", lambda d: d.strftime("%Y-%m-%d")),
    "C": ("20250105", .10, "JP", lambda d: d.strftime("%Y%m%d")),
    "D": ("2025年1月5日", .08, "JP", lambda d: f"{d.year}年{d.month}月{d.day}日"),
    "E": ("R7.1.5", .07, "JP", lambda d: wareki(d, False)),
    "F": ("令和7年1月5日", .05, "JP", lambda d: wareki(d, True)),
    "G": ("1/5/2025（月/日/年）", .06, "US", lambda d: f"{d.month}/{d.day}/{d.year}"),
    "H": ("5/1/2025（日/月/年）", .04, "EU", lambda d: f"{d.day}/{d.month}/{d.year}"),
    "I": ("25/1/5（年が2桁）", .06, "OLD", lambda d: f"{d.year % 100}/{d.month}/{d.day}"),
    "J": ("45662（表計算の通し番号）", .04, "XLS", lambda d: str((d - dt.date(1899, 12, 30)).days)),
}
keys = list(STY)
sty = rng.choice(keys, size=N, p=[STY[k][1] for k in keys])
start = dt.date(2016, 1, 1); span = (dt.date(2025, 12, 31) - start).days + 1
true = [start + dt.timedelta(days=int(x)) for x in rng.integers(0, span, N)]
df = pd.DataFrame({"row_id": np.arange(1, N + 1), "style": sty, "source": [STY[k][2] for k in sty], "s": [STY[k][3](d) for k, d in zip(sty, true)],
                   "true": pd.to_datetime(true)})
df.assign(true=df.true.dt.strftime("%Y-%m-%d")).to_csv(DATA / "mixed_dates.csv", index=False)


def judge(parsed):
    """parsed：datetime64 の Series（読めなければ NaT）。正しい／エラー／黙って別の日"""
    p = pd.to_datetime(parsed, errors="coerce")
    return np.where(p.isna(), "エラー", np.where(p.values == df.true.values, "正しい", "別の日"))


# ---- ① そのまま読む（pandas に書式を任せる）
m1 = pd.to_datetime(df.s, format="mixed", errors="coerce")
# ---- ② 書式を1つに決めて読む
m2 = pd.to_datetime(df.s, format="%Y/%m/%d", errors="coerce")


# ---- ③ 書き方ごとに判定して読む（決まりを1つずつ足す）
def r_ymd(s, src):
    m = re.fullmatch(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", s)
    return dt.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def r_compact(s, src):
    return dt.datetime.strptime(s, "%Y%m%d").date() if re.fullmatch(r"(19|20)\d{6}", s) else None


def r_kanji(s, src):
    m = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", s)
    return dt.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def r_wareki(s, src):
    m = re.fullmatch(r"(令和|平成|R|H)(元|\d{1,2})[年.](\d{1,2})[月.](\d{1,2})日?", s)
    if not m:
        return None
    st = {"令和": 2019, "R": 2019, "平成": 1989, "H": 1989}[m[1]]
    y = 1 if m[2] == "元" else int(m[2])
    return dt.date(st + y - 1, int(m[3]), int(m[4]))


def r_slash_guess(s, src):
    """年が後ろの形。入力元を見ずに、13以上の数があるほうを日とみなす。どちらも12以下なら月/日/年とみなす"""
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if not m:
        return None
    a, b, y = int(m[1]), int(m[2]), int(m[3])
    return dt.date(y, b, a) if a > 12 else dt.date(y, a, b)


def r_slash_source(s, src):
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if not m or src not in ("US", "EU"):
        return None
    a, b, y = int(m[1]), int(m[2]), int(m[3])
    return dt.date(y, a, b) if src == "US" else dt.date(y, b, a)


def r_yy(s, src):
    m = re.fullmatch(r"(\d{2})/(\d{1,2})/(\d{1,2})", s)
    return dt.date(2000 + int(m[1]), int(m[2]), int(m[3])) if m and src == "OLD" else None


def r_serial(s, src):
    return dt.date(1899, 12, 30) + dt.timedelta(days=int(s)) if re.fullmatch(r"\d{5}", s) and src == "XLS" else None


RULES = [("年/月/日・年-月-日", [r_ymd]), ("＋8桁の数字", [r_compact]), ("＋年月日（漢字）", [r_kanji]), ("＋和暦", [r_wareki]),
         ("＋月/日/年と日/月/年（数字だけで判定）", [r_slash_guess]), ("＋入力元で月と日の順を決める", [r_slash_source]),
         ("＋年が2桁（入力元で判定）", [r_yy]), ("＋表計算の通し番号（入力元で判定）", [r_serial])]


def apply(rules):
    out = []
    for s, src in zip(df.s, df.source):
        v = None
        for f in rules:
            try:
                v = f(s, src)
            except ValueError:
                v = None
            if v is not None:
                break
        out.append(pd.NaT if v is None else pd.Timestamp(v))
    return pd.Series(out)


steps = []; cur = []
for name, fs in RULES:
    if fs == [r_slash_source]:
        cur = [f for f in cur if f is not r_slash_guess] + fs     # 数字だけの判定を、入力元での判定に入れ替える
    else:
        cur = cur + fs
    j = judge(apply(cur))
    steps.append({"決まり": name, "正しい": int((j == "正しい").sum()), "エラー": int((j == "エラー").sum()), "別の日": int((j == "別の日").sum())})
m3 = apply(cur)
pd.DataFrame(steps).to_csv(RES / "rules_step_by_step.csv", index=False)

# ---- 集計
out = {}
tab = []
for lab, p in [("①そのまま読む", m1), ("②書式を1つに決めて読む", m2), ("③書き方ごとに判定して読む", m3)]:
    j = judge(p)
    out[lab] = {k: int((j == k).sum()) for k in ["正しい", "エラー", "別の日"]}
    for k in keys:
        mk = (df["style"] == k).values
        tab.append({"読み方": lab, "書き方": k, "例": STY[k][0], "件数": int(mk.sum()), "正しい": int((j[mk] == "正しい").sum()), "エラー": int((j[mk] == "エラー").sum()),
                    "別の日": int((j[mk] == "別の日").sum())})
tab = pd.DataFrame(tab); tab.to_csv(RES / "by_style.csv", index=False)

# ①で別の日になった行：どれだけ離れた日か
j1 = judge(m1); w = (j1 == "別の日")
gap = (pd.to_datetime(m1[w]) - df.true[w]).dt.days
wr = df[w].assign(parsed=pd.to_datetime(m1[w]).dt.strftime("%Y-%m-%d"), gap_days=gap.values)
wr.assign(true=wr.true.dt.strftime("%Y-%m-%d")).head(300).to_csv(RES / "silently_wrong_examples.csv", index=False)
gap_by = {}
for k in keys:
    g = gap[(df["style"][w] == k).values]
    if len(g):
        gap_by[k] = {"件数": int(len(g)), "中央値の日数": float(np.median(np.abs(g))), "最大の日数": int(np.abs(g).max()),
                     "同じ年の中": round(float((np.abs(g) < 366).mean() * 100), 1), "未来の日付（2026年以降）": int((pd.to_datetime(m1[w])[(df["style"][w] == k).values] > "2025-12-31").sum())}
# 日と月の取り違え：日が12以下の行の割合
H = df[df["style"] == "H"]
day_le12 = float((H.true.dt.day <= 12).mean() * 100)
same_dm = float((H.true.dt.day == H.true.dt.month).mean() * 100)
# 範囲の検査（2016〜2025年の外なら怪しい）で、①の「別の日」は何件見つかるか
p1 = pd.to_datetime(m1[w])
range_catch = int(((p1 < "2016-01-01") | (p1 > "2025-12-31")).sum())
range_by = {k: int((((p1 < "2016-01-01") | (p1 > "2025-12-31")) & (df["style"][w] == k).values).sum()) for k in gap_by}

# ---- DuckDB で②と同じ読み方を確かめる
con = duckdb.connect()
con.execute(f"CREATE TABLE raw_dates AS SELECT row_id, source, s FROM read_csv('{DATA / 'mixed_dates.csv'}', header=true, all_varchar=true)")
con.execute("ALTER TABLE raw_dates ALTER row_id TYPE INTEGER")
def q(sql):
    return pd.to_datetime(pd.Series([x[0] for x in con.execute(sql).fetchall()]), errors="coerce")


a = q("SELECT CAST(TRY_STRPTIME(s, '%Y/%m/%d')::DATE AS VARCHAR) FROM raw_dates ORDER BY row_id"); b = m2
same = bool(((a.isna() & b.isna()) | (a.values == b.values)).all())
assert same
d3 = q("""SELECT CAST(COALESCE(TRY_STRPTIME(s, '%Y/%m/%d'), TRY_STRPTIME(s, '%Y-%m-%d'), TRY_STRPTIME(s, '%Y%m%d'), TRY_STRPTIME(s, '%Y年%m月%d日'))::DATE AS VARCHAR)
            FROM raw_dates ORDER BY row_id""")
j3 = judge(d3)
duck = {"②と同じ結果": same, "西暦の4つの書式を順に試す": {k: int((j3 == k).sum()) for k in ["正しい", "エラー", "別の日"]}}
pd.DataFrame([{"確かめたこと": "DuckDB の TRY_STRPTIME(s, '%Y/%m/%d') が pandas の②と全行で一致", "結果": same},
              {"確かめたこと": "西暦の4書式を COALESCE で順に試す：正しい／エラー／別の日", "結果": str(duck["西暦の4つの書式を順に試す"])}]).to_csv(RES / "sql_check_duckdb.csv", index=False)

main = {"n": N, "styles": {k: {"例": STY[k][0], "件数": int((df["style"] == k).sum())} for k in keys}, "methods": out, "steps": steps,
        "wrong_gap_by_style": gap_by, "H_day_le12_pct": round(day_le12, 1), "H_same_day_month_pct": round(same_dm, 1),
        "range_check_catches": range_catch, "range_check_by_style": range_by, "wrong_total_m1": int(w.sum()), "duckdb": duck,
        "pandas": pd.__version__}
json.dump(main, open(RES / "a427_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1：読み方ごとの結果
fig, ax = plt.subplots(figsize=(8.6, 3.6))
labs = list(out); y = np.arange(len(labs)); left = np.zeros(len(labs))
for k, c in [("正しい", BLUE), ("エラー", GRAY), ("別の日", ORANGE)]:
    v = np.array([out[l][k] for l in labs]) / N * 100
    ax.barh(y, v, left=left, color=c, label={"正しい": "正しい日付", "エラー": "読めない（エラー）", "別の日": "黙って別の日"}[k])
    for i, (a_, l_) in enumerate(zip(v, left)):
        if a_ > 1.5:
            ax.text(l_ + a_ / 2, i, f"{a_:.1f}%", ha="center", va="center", fontsize=9, color="white" if k != "エラー" else INK)
    left += v
ax.set_yticks(y); ax.set_yticklabels(labs); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("2万件に占める割合（%）")
ax.set_title("読み方ごとの結果：そのまま読むと、黙って別の日になる行が出る")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
save(fig, "a427_methods.png", SRC, y=-0.2)

# ---- 図2：①の書き方ごとの結果
t1 = tab[tab["読み方"] == "①そのまま読む"]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
y = np.arange(len(t1)); left = np.zeros(len(t1))
for k, c in [("正しい", BLUE), ("エラー", GRAY), ("別の日", ORANGE)]:
    v = (t1[k] / t1["件数"] * 100).values
    ax.barh(y, v, left=left, color=c, label={"正しい": "正しい日付", "エラー": "読めない（エラー）", "別の日": "黙って別の日"}[k])
    left += v
for i, (_, rw) in enumerate(t1.iterrows()):
    ax.text(101, i, f"別の日 {rw['別の日']:,}件" if rw["別の日"] else "", va="center", fontsize=9, color=ORANGE)
ax.set_yticks(y); ax.set_yticklabels(t1["例"]); ax.invert_yaxis(); ax.set_xlim(0, 118); ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("その書き方の行に占める割合（%）"); ax.set_title("そのまま読んだとき、どの書き方が別の日になるか")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.14))
save(fig, "a427_by_style.png", SRC, y=-0.13)

# ---- 図3：決まりを足すごとの減り方
fig, ax = plt.subplots(figsize=(9, 4.6))
st = pd.DataFrame(steps); yy = np.arange(len(st))
ax.barh(yy - 0.2, st["エラー"], 0.4, color=GRAY, label="読めない（エラー）")
ax.barh(yy + 0.2, st["別の日"], 0.4, color=ORANGE, label="黙って別の日")
for i, rw in st.iterrows():
    ax.text(rw["エラー"] + 100, i - 0.2, f"{rw['エラー']:,}", va="center", fontsize=8.5)
    ax.text(rw["別の日"] + 100, i + 0.2, f"{rw['別の日']:,}", va="center", fontsize=8.5, color=ORANGE)
ax.set_yticks(yy); ax.set_yticklabels(st["決まり"], fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 11500)
ax.set_xlabel("件数（2万件中）"); ax.set_title("決まりを1つ足すごとに、読めない行と別の日になる行はどう減るか"); ax.legend(frameon=False, loc="lower right")
save(fig, "a427_rules_steps.png", SRC)
print(json.dumps(main, ensure_ascii=False)[:3000])
