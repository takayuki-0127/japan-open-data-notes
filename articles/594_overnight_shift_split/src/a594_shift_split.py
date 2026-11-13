"""594 日をまたぐ夜のシフトを、開始日で数えるか日ごとに分けるかで、日ごとの労働時間はどれだけ違うのか。
架空の勤務記録（22時〜翌6時の夜勤を含む、2025年の1年分。seed 594）。休憩の差し引きは扱わない"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "出典：架空の勤務記録（作成者が乱数で作成、seed 594）"
rng = np.random.default_rng(594)
days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
gen_days = pd.date_range("2024-12-31", "2025-12-31", freq="D")   # 12/31 の夜勤が 1/1 にかかるので、前日から作る
# シフトの型：開始時刻と長さ（時間）
TYPES = {"日勤": (9, 9), "遅番": (14, 8), "準夜": (17, 8), "夜勤": (22, 8), "長い夜勤": (20, 12)}
need = {"日勤": 14, "遅番": 6, "準夜": 4, "夜勤": 5, "長い夜勤": 2}      # 1日に入る人数の目安
rows = []
sid = 0
for d in gen_days:
    wk = d.dayofweek >= 5
    for t, (h, L) in TYPES.items():
        n = rng.poisson(need[t] * (0.7 if wk and t in ("日勤", "遅番") else 1.0))
        for _ in range(n):
            sid += 1
            st = d + pd.Timedelta(hours=h) + pd.Timedelta(minutes=int(rng.choice([0, 0, 0, 15, 30, -15])))
            en = st + pd.Timedelta(hours=L) + pd.Timedelta(minutes=int(rng.choice([0, 0, 0, 15, 30, 45, 60])))
            rows.append((sid, f"E{int(rng.integers(1, 81)):03d}", t, st, en))
sh = pd.DataFrame(rows, columns=["shift_id", "staff_id", "shift_type", "start_at", "end_at"])
sh.to_csv(DATA / "shifts.csv", index=False, date_format="%Y-%m-%d %H:%M")
# 時刻だけで持つ表（日付は開始日だけ）
tonly = pd.DataFrame({"shift_id": sh.shift_id, "work_date": sh.start_at.dt.date, "start_time": sh.start_at.dt.strftime("%H:%M"), "end_time": sh.end_at.dt.strftime("%H:%M")})
tonly.to_csv(DATA / "shifts_time_only.csv", index=False)

# ---- 1. 開始日に全部つける ／ 日ごとに分ける ----
hrs = (sh.end_at - sh.start_at).dt.total_seconds() / 3600
by_start = hrs.groupby(sh.start_at.dt.normalize()).sum().reindex(days, fill_value=0)
mid = sh.start_at.dt.normalize() + pd.Timedelta(days=1)
first = (np.minimum(sh.end_at, mid) - sh.start_at).dt.total_seconds() / 3600
second = ((sh.end_at - mid).dt.total_seconds() / 3600).clip(lower=0)
split = first.groupby(sh.start_at.dt.normalize()).sum().add(second.groupby(mid).sum(), fill_value=0)
split_in = split.reindex(days, fill_value=0)
spill_2026 = float(split.loc[split.index > days[-1]].sum())
d = pd.DataFrame({"by_start": by_start, "split": split_in})
d["diff"] = d.by_start - d.split
d["diff_pct"] = d["diff"] / d.split * 100
d.to_csv(RES / "daily.csv", float_format="%.3f", index_label="date")
m = d.groupby(d.index.to_period("M"))[["by_start", "split"]].sum()
m["diff"] = m.by_start - m.split; m["diff_pct"] = m["diff"] / m.split * 100
m.to_csv(RES / "monthly.csv", float_format="%.3f")
w = d.groupby(d.index.dayofweek)[["by_start", "split"]].mean()
w["diff_pct"] = (w.by_start / w.split - 1) * 100
w.index = list("月火水木金土日")
w.to_csv(RES / "by_weekday.csv", float_format="%.3f")

# ---- 2. 時刻だけの表で、終了 − 開始 をそのまま引くと ----
toh = lambda s: s.str[:2].astype(int) + s.str[3:].astype(int) / 60
naive = toh(tonly.end_time) - toh(tonly.start_time)
fixed = np.where(naive < 0, naive + 24, naive)

cross = sh.end_at.dt.normalize() > sh.start_at.dt.normalize()
nights = sh[sh.shift_type.isin(["夜勤", "長い夜勤"])]
res = {"note": "2024-12-31 に始まった勤務も含めて作り、集計は2025年の日付だけ", "n_shifts": int(len(sh)), "n_staff": int(sh.staff_id.nunique()), "n_cross_midnight": int(cross.sum()), "cross_share_pct": round(float(cross.mean() * 100), 1),
       "hours_total": round(float(hrs.sum()), 1), "hours_into_2026_when_split": round(spill_2026, 2),
       "daily_diff": {"mean_abs_h": round(float(d["diff"].abs().mean()), 1), "max_abs_h": round(float(d["diff"].abs().max()), 1),
                      "mean_abs_pct": round(float(d.diff_pct.abs().mean()), 1), "max_abs_pct": round(float(d.diff_pct.abs().max()), 1),
                      "n_days_abs_over_5pct": int((d.diff_pct.abs() > 5).sum()), "corr_by_start_split": round(float(d.by_start.corr(d.split)), 3)},
       "monthly_diff_h": {str(k): round(float(v), 2) for k, v in m["diff"].items()},
       "monthly_diff_pct_range": [round(float(m.diff_pct.min()), 3), round(float(m.diff_pct.max()), 3)],
       "weekday_diff_pct": {k: round(float(v), 1) for k, v in w.diff_pct.items()},
       "time_only": {"n_negative": int((naive < 0).sum()), "naive_total_h": round(float(naive.sum()), 1), "fixed_total_h": round(float(fixed.sum()), 1),
                     "naive_vs_true_pct": round(float((naive.sum() / hrs.sum() - 1) * 100), 1),
                     "fixed_matches": bool(np.allclose(fixed, hrs.values)),
                     "night_shift_naive_hours_example": sorted(set(np.round(naive[sh.shift_type == "夜勤"], 2)))[:3]}}

# ---- 3. SQL（DuckDB、1スレッド） ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE shifts AS SELECT shift_id, staff_id, shift_type, CAST(start_at AS TIMESTAMP) AS start_at, CAST(end_at AS TIMESTAMP) AS end_at FROM read_csv_auto('{DATA / 'shifts.csv'}', all_varchar=true)")
sq = con.execute((SQL / "02_split_duckdb.sql").read_text()).df().set_index("work_date")
sq.index = pd.to_datetime(sq.index)
sq.to_csv(RES / "sql_daily.csv", float_format="%.4f")
res["sql_match_python"] = bool(np.allclose(sq.hours_split.reindex(split.index).values, split.values))
json.dump(res, open(RES / "a594_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 4. 図 ----
seg = d.loc["2025-03-24":"2025-04-06"]
fig, ax = plt.subplots(figsize=(9, 4.2))
x = np.arange(len(seg))
ax.bar(x - 0.2, seg.by_start, 0.4, color=ORANGE, label="開始日に全部つける")
ax.bar(x + 0.2, seg.split, 0.4, color=BLUE, label="0時で日ごとに分ける")
ax.set_xticks(x, [f"{i.month}/{i.day}\n{'月火水木金土日'[i.dayofweek]}" for i in seg.index], fontsize=8)
ax.set_ylabel("その日の労働時間の合計（時間）"); ax.set_ylim(0, seg.max().max() * 1.15)
ax.set_title("日ごとの時間は、夜勤をどの日に数えるかで変わる（3/24〜4/6）")
ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
save(fig, "a594_daily.png", SRC)

fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.bar(range(12), m["diff"], color=[ORANGE if v > 0 else BLUE for v in m["diff"]])
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(range(12), [f"{p.month}月" for p in m.index])
for i, (v, pc) in enumerate(zip(m["diff"], m.diff_pct)):
    ax.text(i, v + (2 if v >= 0 else -2), f"{pc:+.2f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=8, color=INK)
ax.set_ylim(m["diff"].min() - 12, m["diff"].max() + 12)
ax.set_ylabel("開始日につけた場合 − 日ごとに分けた場合（時間）", fontsize=9)
ax.set_title("月の合計では、月をまたぐ夜勤の分だけ動く（数字は月の合計に対する%）")
save(fig, "a594_monthly.png", SRC)

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.hist(naive, bins=np.arange(-18, 14, 0.5), color=GRAY, label="終了 − 開始 をそのまま")
ax.hist(fixed, bins=np.arange(-18, 14, 0.5), histtype="step", lw=2, color=BLUE, label="終了が開始より前なら24時間を足す")
ax.set_xlabel("1回の勤務の時間（時間）"); ax.set_ylabel("勤務の回数")
ax.set_title("時刻だけで持つ表では、夜勤がマイナスの時間になる")
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a594_time_only.png", SRC)
