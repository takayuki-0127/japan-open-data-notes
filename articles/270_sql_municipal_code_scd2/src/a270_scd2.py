"""270 市区町村の合併を SQL でどう扱うか：期間つきマスタ（SCD2）と再帰 CTE で、2000年のコードを今のコードへ
T-SQL（sql/*.sql）を DuckDB で動かして確かめる。データは F94 の写し（総務省「廃置分合等情報」ほか）"""
import json, re
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save, tsql_to_duckdb


def q(name):
    s = tsql_to_duckdb((SQL / name).read_text(encoding="utf-8"))
    return re.sub(r"DATEADD\(day,\s*(-?\d+),\s*", r"date_add(INTERVAL (\1) DAY, ", s)


def ctas(sql):
    """T-SQL の SELECT … INTO dbo.x を DuckDB の CREATE TABLE dbo.x AS に置き換える"""
    m = re.search(r"\nINTO (dbo\.\w+)\n", sql)
    body = sql.replace(m.group(0), "\n")
    body = "\n".join(l for l in body.split("\n") if not l.startswith("--"))
    return f"CREATE TABLE {m.group(1)} AS {body}"


# ---- 読み込み（01 の表を DuckDB で作る）
ev = pd.read_csv(DATA / "merger_events.csv", dtype=str)
u00 = pd.read_csv(DATA / "old_units_2000.csv", dtype={"code": str})[["code", "name", "pop2000"]]
u20 = pd.read_csv(DATA / "units_2020.csv", dtype={"code": str})
u20["name"] = u20["name"].str.split().str[-1]
names = dict(zip(u20.code, u20.name)) | dict(zip(u00.code, u00.name))
rows = []
for _, r in ev.iterrows():
    m = re.search(r"([^、()\s]+)\(" + r.new + r"\)", r.text)
    nm = names.get(r.new) or re.sub(r"^[がに]", "", m.group(1))
    for o in r.olds.split(";"):
        rows.append(dict(eff_date=r.date, kind=r.kind, old_code=o, new_code=r.new, new_name=nm))
ex = pd.DataFrame(rows)
ex.to_csv(DATA / "events_x.csv", index=False)

con = duckdb.connect(); con.execute("CREATE SCHEMA dbo")
con.execute("CREATE TABLE dbo.units2000 AS SELECT * FROM u00")
con.execute("CREATE TABLE dbo.units2020 AS SELECT code, name, CAST(pop2020 AS BIGINT) pop2020 FROM u20")
con.execute("CREATE TABLE dbo.events_x AS SELECT CAST(eff_date AS DATE) eff_date, kind, old_code, new_code, new_name FROM ex")
# 政令市（市全体のコード）：2020年の単位のうち、3桁目が1のもの
con.execute("CREATE TABLE dbo.seirei_cities AS SELECT code FROM dbo.units2020 WHERE substr(code, 3, 1) = '1' AND code NOT BETWEEN '13101' AND '13123'")
ward = con.execute("SELECT eff_date, old_code, new_code FROM dbo.events_x WHERE substr(new_code, 3, 1) = '1' AND new_code NOT IN (SELECT code FROM dbo.seirei_cities) AND new_code NOT BETWEEN '13101' AND '13123'").df()
# T-SQL の UPDATE … FROM を DuckDB の UPDATE … SET … WHERE に（同じ中身）
con.execute("""UPDATE dbo.events_x SET new_code = (SELECT MAX(c.code) FROM dbo.seirei_cities c
    WHERE left(c.code, 2) = left(events_x.new_code, 2) AND c.code <= events_x.new_code)
    WHERE substr(new_code, 3, 1) = '1' AND new_code NOT IN (SELECT code FROM dbo.seirei_cities) AND new_code NOT BETWEEN '13101' AND '13123'""")
con.execute("""UPDATE dbo.events_x SET new_name = (SELECT u.name FROM dbo.units2020 u WHERE u.code = events_x.new_code)
    WHERE new_code IN (SELECT code FROM dbo.seirei_cities)""")
n_zero = con.execute("""SELECT COUNT(*) FROM (SELECT x.new_code, x.eff_date FROM dbo.events_x x JOIN dbo.events_x y
    ON y.old_code = x.new_code AND y.old_code <> y.new_code AND y.eff_date = x.eff_date GROUP BY x.new_code, x.eff_date)""").fetchone()[0]

# ---- 02 SCD2、04 再帰 CTE
con.execute(ctas(q("02_scd2.sql")))
con.execute(ctas(q("04_roll_forward.sql")))
scd = con.execute("SELECT * FROM dbo.muni_scd2 ORDER BY sk").df()
cw = con.execute("SELECT * FROM dbo.crosswalk ORDER BY code2000").df()
scd.to_csv(RES / "muni_scd2.csv", index=False)
cw.to_csv(RES / "crosswalk_sql.csv", index=False)

# ---- 05 照合
c1, c2, c3 = [con.execute(s).fetchone() for s in q("05_checks.sql").split(";") if s.strip() and "SELECT" in s]
f94 = pd.read_csv(DATA / "crosswalk_2000_2020.csv", dtype=str)
mrg = cw.merge(f94[["code2000", "code2020"]], on="code2000", how="outer")
agree = int((mrg.code_now == mrg.code2020).sum())
overlap = con.execute("""SELECT COUNT(*) FROM dbo.muni_scd2 a JOIN dbo.muni_scd2 b
    ON a.code = b.code AND a.sk < b.sk AND a.valid_to >= b.valid_from""").fetchone()[0]
n_multi = int((scd.groupby("code").size() > 1).sum())

# ---- 03 ある日の数を、総務省の公表値と比べる（公表値は東京23区を含まない）
pub = {"2006-03-31": 1821, "2010-03-31": 1727, "2014-04-05": 1718, "2018-10-01": 1718}
alld = sorted(set(pd.date_range("2000-10-01", "2020-10-01", freq="MS").strftime("%Y-%m-%d")) | set(pub))
dates = pd.DataFrame({"as_of": pd.to_datetime(alld)})
con.execute("CREATE TABLE dbo.check_dates AS SELECT CAST(as_of AS DATE) as_of FROM dates")
cnt = con.execute(q("03_as_of.sql")).df()
cnt["n_muni"] = cnt.n_units - cnt.n_ward23
cnt.to_csv(RES / "counts_by_date.csv", index=False)
cmp_pub = {d: dict(sql=int(cnt.loc[cnt.as_of == pd.Timestamp(d), "n_muni"].iloc[0]), published=v) for d, v in pub.items()}

# ---- コードをそのままつないだら（素朴な結合）
nv = con.execute("""
SELECT u.code, u.pop2000, n.pop2020,
       CASE WHEN n.code IS NULL THEN 'gone'
            WHEN (SELECT COUNT(*) FROM dbo.crosswalk c WHERE c.code_now = u.code) > 1 THEN 'grew'
            ELSE 'same' END AS kind,
       (SELECT SUM(u2.pop2000) FROM dbo.crosswalk c JOIN dbo.units2000 u2 ON u2.code = c.code2000
         WHERE c.code_now = u.code) AS pop2000_now_area
FROM dbo.units2000 u LEFT JOIN dbo.units2020 n ON n.code = u.code""").df()
tot = nv.pop2000.sum()
summ = nv.groupby("kind").agg(n=("code", "size"), pop=("pop2000", "sum"))
summ["pop_share"] = summ["pop"] / tot
g = nv[nv.kind == "grew"].copy()
g["naive"] = g.pop2020 / g.pop2000 - 1
g["right"] = g.pop2020 / g.pop2000_now_area - 1
grew = dict(n=len(g), naive_median=float(g.naive.median()), right_median=float(g.right.median()),
            naive_up_right_down=int(((g.naive > 0) & (g.right < 0)).sum()),
            naive_up=int((g.naive > 0).sum()), right_up=int((g.right > 0).sum()))
s = nv[nv.kind == "same"]
same_change_median = float((s.pop2020 / s.pop2000 - 1).median())

out = dict(ward_events=len(ward), ward_rows=ward.astype(str).to_dict("records"), same_day_chains=int(n_zero), n_events=len(ev), n_event_rows=len(ex), scd2_rows=len(scd), codes=int(scd.code.nunique()),
           codes_multi_version=n_multi, version_overlaps=int(overlap),
           crosswalk=dict(rows=int(c1[0]), n_old=int(c1[1]), n_now=int(c1[2]), now_not_in_2020=int(c2[0]),
                          pop2000_rolled=int(c3[0]), pop2000_total=int(tot), agree_with_F94=agree, f94_rows=len(f94),
                          steps=cw.steps.value_counts().sort_index().to_dict()),
           as_of_vs_published=cmp_pub,
           naive_join={k: dict(n=int(v.n), pop_share=round(float(v.pop_share), 4)) for k, v in summ.iterrows()},
           grew=grew, same_change_median=same_change_median)
json.dump(out, open(RES / "checks.json", "w"), ensure_ascii=False, indent=1, default=int)
g.sort_values("code").to_csv(RES / "grew_codes.csv", index=False)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))

# ---- 図1：静岡市まわりの版（SCD2 の行）を時間の帯で
ex_codes = ["22201", "22204", "22100", "22382", "22383"]
sub = scd[scd.code.isin(ex_codes)].copy()
sub = sub.sort_values(["valid_from"])
fig, ax = plt.subplots(figsize=(9, 4.2))
end_cap = pd.Timestamp("2021-03-31")
labels = []
for i, r in enumerate(sub.itertuples()):
    a, b = pd.Timestamp(r.valid_from), min(pd.Timestamp(r.valid_to), end_cap)
    col = BLUE if r.code in ("22201", "22100") else GRAY
    ax.barh(i, (b - a).days, left=a, color=col, height=0.42)
    labels.append(f"sk={r.sk}  {r.code} {r.name}")
    ax.text(a, i - 0.3, f"{a:%Y-%m-%d}〜" + ("" if r.valid_to.year == 9999 else f"{pd.Timestamp(r.valid_to):%Y-%m-%d}"), fontsize=8, color=INK, va="bottom")
ax.set_yticks(range(len(sub))); ax.set_yticklabels(labels, fontsize=9)
ax.set_title("期間つきマスタ（SCD2）の行：静岡市と、合併・編入した市町（1行＝1つの版）", loc="left")
ax.set_ylim(len(sub) - 0.5, -0.9)
ax.set_xlim(pd.Timestamp("2000-06-01"), end_cap)
save(fig, "a270_versions.png")

# ---- 図2：コードをそのままつなぐと
order = ["gone", "grew", "same"]; lab = {"gone": "コードが消えた\n（結合で落ちる）", "grew": "同じコードで\n区域が広がった（黙ってつながる）", "same": "同じコード・\n同じ区域"}
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
for ax, col, ttl, fmt in [(axs[0], "n", "2000年の単位の数（3,252）", "{:,.0f}"), (axs[1], "pop_share", "2000年の人口に占める割合", "{:.0%}")]:
    vals = [summ.loc[k, col] for k in order]
    ax.barh(range(3), vals, color=[ORANGE, BLUE, GRAY]); ax.set_yticks(range(3)); ax.set_yticklabels([lab[k] for k in order], fontsize=9)
    ax.invert_yaxis(); ax.set_title(ttl, loc="left", fontsize=11)
    for i, v in enumerate(vals): ax.text(v, i, " " + fmt.format(v), va="center", fontsize=10)
    ax.set_xticks([])
fig.suptitle("2000年のコードを2020年のマスタにそのまま結合すると", x=0.01, ha="left", fontsize=13)
fig.tight_layout()
save(fig, "a270_naive.png")

# ---- 図3：ある日に有効だった市町村の数（SQL）と総務省の公表値
fig, ax = plt.subplots(figsize=(9, 3.6))
ax.plot(cnt.as_of, cnt.n_muni, color=BLUE, lw=2, label="期間つきマスタから数えた数（23区を除く）")
for d, v in pub.items():
    ax.scatter(pd.Timestamp(d), v, color=ORANGE, zorder=3, s=40)
    ax.annotate(f"公表 {v:,}", (pd.Timestamp(d), v), textcoords="offset points", xytext=(6, 8), fontsize=9, color=ORANGE)
ax.set_ylabel("市町村の数"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("ある日に有効だった市町村の数：SQL で数えた線と、総務省の公表値（点）", loc="left")
save(fig, "a270_counts.png")
