"""357 「週」の決め方で、週次の売上はどれだけ変わるのか（架空の日次売上5年分）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import SQL, RES, save, BLUE, ORANGE, GRAY, GREEN, INK, LIGHT

SEED = 357
SRC = "架空の日次売上（作成者が乱数で作成、seed 357）"
rng = np.random.default_rng(SEED)
GROWTH = 0.03                                             # 本当の伸び：年3%

# ---------- 架空の日次売上：2020-12-28（月）〜2026-01-04（日）。分析は2021〜2025年の日付 ----------
d = pd.date_range("2021-01-01", "2025-12-31")
df = pd.DataFrame({"d": d})
dow = df["d"].dt.dayofweek.values                         # 0=月
wk = np.array([1.00, 0.95, 0.95, 1.00, 1.15, 1.50, 1.40])[dow]
doy = df["d"].dt.dayofyear.values
season = 1 + 0.06 * np.sin(2 * np.pi * (doy - 80) / 365.25)
md = df["d"].dt.strftime("%m-%d").values
special = np.ones(len(df))
special[np.isin(md, ["12-26", "12-27", "12-28", "12-29", "12-30", "12-31"])] = 1.6     # 年末の山
special[md == "01-01"] = 0.3                                                             # 元日は少ない
special[np.isin(md, ["01-02", "01-03"])] = 1.3
years = (df["d"] - pd.Timestamp("2021-01-01")).dt.days.values / 365.25
level = (1 + GROWTH) ** years
df["amount"] = np.round(1_000_000 * level * wk * season * special * rng.lognormal(-0.03 ** 2 / 2, 0.03, len(df)))
df["truth"] = 1_000_000 * level * wk * season * special   # 揺れのない値

# ---------- 3つの「週」 ----------
iso = df["d"].dt.isocalendar()
df["iso_y"], df["iso_w"] = iso["year"].values, iso["week"].values
df["y"] = df["d"].dt.year
jan1_sun0 = ((pd.to_datetime(df["y"].astype(str) + "-01-01").dt.dayofweek + 1) % 7).values      # 1月1日の曜日（日=0）
df["sun_w"] = (df["d"].dt.dayofyear.values + jan1_sun0 - 1) // 7 + 1                             # SQL Server の DATEPART(week)（DATEFIRST 7）
first = pd.to_datetime(df["d"].dt.strftime("%Y-%m-01"))
df["m"] = df["d"].dt.month
df["mon_w"] = (df["d"].dt.day.values + first.dt.dayofweek.values - 1) // 7 + 1                   # 月の中の第何週（月曜始まり）

# T-SQL の「ISO の年」の式を確かめる：YEAR(DATEADD(day, 26 - iso_week, d))
chk = (df["d"] + pd.to_timedelta(26 - df["iso_w"].astype(int), unit="D")).dt.year
assert (chk.values == df["iso_y"].values).all()

defs = {"ISO 週": ["iso_y", "iso_w"], "日曜始まり（1月1日の週が第1週）": ["y", "sun_w"], "月で切る週": ["y", "m", "mon_w"]}
weekly = {}
for name, keys in defs.items():
    g = df.groupby(keys).agg(days=("d", "size"), sales=("amount", "sum"), truth=("truth", "sum"), d0=("d", "min")).reset_index()
    if name == "ISO 週":
        g = g[g["iso_y"].between(2021, 2025)]            # 2020年・2026年の週に入る端の日は除く（下で数える）
    weekly[name] = g

# ---------- ① 週の数と、7日そろわない週 ----------
rows = []
for name, g in weekly.items():
    ycol = "iso_y" if name == "ISO 週" else "y"
    for y, s in g.groupby(ycol):
        rows.append({"決め方": name, "年": int(y), "週の数": len(s), "7日未満の週": int((s["days"] < 7).sum()),
                     "いちばん短い週の日数": int(s["days"].min())})
cnt = pd.DataFrame(rows)
cnt.to_csv(RES / "weeks_per_year.csv", index=False)
tot = cnt.groupby("決め方", sort=False).agg(週の数=("週の数", "sum"), 七日未満=("7日未満の週", "sum")).reset_index()

# 同じ日でも週の番号が違う日の割合（ISO と 日曜始まり）
diff_num = float((df["iso_w"].values != df["sun_w"].values).mean() * 100)
# ISO の年が暦の年と違う日
iso_other = df[df["iso_y"] != df["y"]]
iso_other_days = int(len(iso_other))

# ---------- ② 前年の同じ番号の週と比べる（本当の伸びは年3%） ----------
def yoy_table(name):
    g = weekly[name].copy()
    ycol = "iso_y" if name == "ISO 週" else "y"
    keys = [k for k in defs[name] if k != ycol]
    prev = g.copy(); prev[ycol] = prev[ycol] + 1
    m = g.merge(prev, on=[ycol] + keys, how="left", suffixes=("", "_prev"))
    m = m[m[ycol] >= 2022]
    m["yoy"] = (m["sales"] / m["sales_prev"] - 1) * 100
    m["no_partner"] = m["sales_prev"].isna()
    m["days_differ"] = (~m["no_partner"]) & (m["days"] != m["days_prev"])
    m["err"] = m["yoy"] - GROWTH * 100
    return m, ycol

yrows, ytabs = [], {}
for name in defs:
    m, ycol = yoy_table(name)
    ytabs[name] = m
    ok = ~m["no_partner"]
    full = ok & ~m["days_differ"]
    yrows.append({"決め方": name, "比べる週の数": int(len(m)), "前年に相手がない週": int(m["no_partner"].sum()),
                  "日数が前年と違う週": int(m["days_differ"].sum()),
                  "本当の伸びから5ポイント以上ずれた週": int((m.loc[ok, "err"].abs() >= 5).sum()),
                  "うち日数は同じなのにずれた週": int((m.loc[full, "err"].abs() >= 5).sum()),
                  "ずれの中央値": float(m.loc[ok, "err"].abs().median()), "最大のずれ": float(m.loc[ok, "err"].abs().max()),
                  "日数が同じ週だけのずれの中央値": float(m.loc[full, "err"].abs().median())})
ysum = pd.DataFrame(yrows)
ysum.round(2).to_csv(RES / "same_week_yoy_errors.csv", index=False)
for name, m in ytabs.items():
    ycol = "iso_y" if name == "ISO 週" else "y"
    m.drop(columns=["truth", "truth_prev"]).assign(d0=m["d0"].dt.strftime("%Y-%m-%d"), d0_prev=m["d0_prev"].dt.strftime("%Y-%m-%d")).round(3) \
        .to_csv(RES / f"yoy_{['iso','sun','month'][list(defs).index(name)]}.csv", index=False)

# 基準：364日前（同じ曜日）からの7日間どうしを比べる
al = df.set_index("d")["amount"]
al7 = al.rolling(7).sum()
aligned = (al7 / al7.shift(364) - 1).dropna() * 100
aligned_w = aligned[aligned.index.dayofweek == 6]                       # 月〜日の7日間
al_err = (aligned_w - GROWTH * 100).abs()
aligned_sum = {"weeks": int(len(aligned_w)), "median_abs_err": float(al_err.median()), "max_abs_err": float(al_err.max()),
               "over5": int((al_err >= 5).sum())}

# ---------- ③ 取り違え：YEAR(d) と ISO 週を組み合わせる ----------
bug = df.groupby(["y", "iso_w"]).agg(days=("d", "size"), sales=("amount", "sum")).reset_index()
right = weekly["ISO 週"].rename(columns={"iso_y": "y"})[["y", "iso_w", "days", "sales"]]
b = bug.merge(right, on=["y", "iso_w"], how="left", suffixes=("_bug", "_ok"))
b["diff_pct"] = (b["sales_bug"] / b["sales_ok"] - 1) * 100
bugged = b[(b["days_bug"] != b["days_ok"]) | b["sales_ok"].isna()].copy()
bugged.round(2).to_csv(RES / "year_isoweek_mixup.csv", index=False)
bug_sum = {"wrong_groups": int(len(bugged)), "days_over7": int((bug["days"] > 7).sum()), "max_days": int(bug["days"].max()),
           "max_over_pct": float(bugged["diff_pct"].max()), "min_under_pct": float(bugged["diff_pct"].min()),
           "iso_year_differs_days": iso_other_days}

# ---------- ④ SQL（DuckDB）で同じ集計。pandas と合うことを確かめる ----------
con = duckdb.connect(); con.execute("SET threads=1")
con.register("s_df", df[["d", "amount"]]); con.execute("CREATE TABLE sales AS SELECT CAST(d AS DATE) AS d, amount FROM s_df")
sq = con.execute((SQL / "01_weekly_duckdb.sql").read_text(encoding="utf-8")).df()
for code, name in [("ISO", "ISO 週"), ("SUN", "日曜始まり（1月1日の週が第1週）"), ("MONTH", "月で切る週")]:
    a = sq[sq["def"] == code]
    if code == "ISO":
        a = a[a["y"].between(2021, 2025)]
    assert len(a) == len(weekly[name]) and np.isclose(a["sales"].sum(), weekly[name]["sales"].sum()), code
    assert sorted(a["days"].tolist()) == sorted(weekly[name]["days"].tolist()), code

# ---------- 図 ----------
fig, ax = plt.subplots(figsize=(9, 4.0))
x = np.arange(len(tot)); full = tot["週の数"] - tot["七日未満"]
ax.bar(x, full, color=BLUE, label="7日そろった週")
ax.bar(x, tot["七日未満"], bottom=full, color=ORANGE, label="7日未満の週")
for xi, f, p in zip(x, full, tot["七日未満"]):
    ax.text(xi, f / 2, f"{int(f)}", ha="center", color="white", fontsize=11)
    if p > 0: ax.text(xi, f + p + 4, f"7日未満 {int(p)}", ha="center", color=ORANGE, fontsize=10.5)
ax.set_xticks(x); ax.set_xticklabels(tot["決め方"]); ax.set_ylabel("5年間の週の数")
ax.set_title("決め方によって、7日そろわない週の数が違う"); ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.1))
save(fig, "a357_partial_weeks.png", "2021〜2025年。" + SRC, y=-0.1)

fig, axes = plt.subplots(1, 3, figsize=(11, 3.9), sharey=True)
for ax, name, c in zip(axes, defs, [BLUE, ORANGE, GREEN]):
    m = ytabs[name]; ycol = "iso_y" if name == "ISO 週" else "y"
    s = m[(m[ycol] == 2025) & ~m["no_partner"]].sort_values("d0")
    ax.axhline(GROWTH * 100, color=INK, lw=1)
    same = ~s["days_differ"]
    ax.scatter(np.arange(len(s))[same.values], s["yoy"][same].clip(-60, 60), s=14, color=c, label="日数が同じ週")
    ax.scatter(np.arange(len(s))[~same.values], s["yoy"][~same].clip(-60, 60), s=26, color=c, marker="x", label="日数が違う週")
    ax.set_title(name, fontsize=11); ax.set_xlabel("2025年の週（年初から順）")
axes[1].scatter([], [], s=14, color=GRAY, label="日数が前年と同じ週"); axes[1].scatter([], [], s=26, color=GRAY, marker="x", label="日数が前年と違う週")
axes[1].legend(frameon=False, fontsize=9.5, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.2))
axes[0].set_ylabel("前年の同じ番号の週との比（%）")
fig.suptitle("前年の同じ番号の週と比べると、本当の伸び（+3%、黒い線）からずれる週がある", y=1.02, fontsize=12.5)
save(fig, "a357_same_week_yoy_2025.png", "±60%を超える値は端に寄せて表示。" + SRC, y=-0.12)

fig, ax = plt.subplots(figsize=(9, 4.0))
w1 = b[(b["iso_w"] == 1) & b["y"].between(2021, 2025)]
xs = np.arange(len(w1))
ax.bar(xs - 0.2, w1["sales_ok"] / 1e6, 0.4, color=BLUE, label="ISO の年でまとめた第1週（7日）")
ax.bar(xs + 0.2, w1["sales_bug"] / 1e6, 0.4, color=ORANGE, label="YEAR(日付) と ISO 週でまとめた「第1週」")
for xi, r in zip(xs, w1.itertuples()):
    ax.text(xi + 0.2, r.sales_bug / 1e6 + 0.15, f"{int(r.days_bug)}日", ha="center", fontsize=9)
ax.set_xticks(xs); ax.set_xticklabels([f"{int(y)}年" for y in w1["y"]]); ax.set_ylabel("第1週の売上（百万円）")
ax.set_title("年と ISO 週を取り違えると、年末の日が「第1週」に混ざる"); ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.1))
save(fig, "a357_year_isoweek_mixup.png", "橙の棒の上は、その「第1週」に入った日数。" + SRC, y=-0.1)

main = {"weeks_total": tot.to_dict("records"), "weeks_per_year": cnt.to_dict("records"), "week_number_differs_pct": diff_num,
        "same_week_yoy": ysum.round(3).to_dict("records"), "aligned_364": aligned_sum, "mixup": bug_sum}
json.dump(main, open(RES / "a357_main.json", "w"), ensure_ascii=False, indent=1)
print(cnt.to_string()); print(tot); print("week no differs %", round(diff_num, 1), "iso-year-other days", iso_other_days)
print(ysum.round(2).T.to_string()); print(aligned_sum); print(bug_sum); print(bugged.round(1).to_string())
