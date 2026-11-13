"""603 日次の前年比を「前年の同じ日」と比べるか「前年の同じ曜日」と比べるかで、どれだけ違って見えるのか

架空の店の日次売上（2024〜2025年）を作る。曜日の波（土日は平日の1.5倍前後）と祝日（日曜と同じ扱い）があり、
本当の伸びは毎日 +3%（それに日々の振れ）。2025年の各日の前年比を3通りで出す。
  D1 前年の同じ日付（2025-03-10 と 2024-03-10）
  D2 364日前（同じ曜日）
  D3 364日前で、どちらかだけが祝日の日を除く
日ごとの前年比の散らばり・マイナスに見える日の数・本当の伸びとのずれを数え、7日・月で足した場合も比べる。
数字は置いた曜日の波と振れで決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空の店の日次売上（作成者が乱数で作成、seed 603）。祝日は2024・2025年の国民の祝日と振替休日"
rng = np.random.default_rng(603)
HOL = pd.to_datetime([
    "2024-01-01", "2024-01-08", "2024-02-11", "2024-02-12", "2024-02-23", "2024-03-20", "2024-04-29", "2024-05-03", "2024-05-04",
    "2024-05-05", "2024-05-06", "2024-07-15", "2024-08-11", "2024-08-12", "2024-09-16", "2024-09-22", "2024-09-23", "2024-10-14",
    "2024-11-03", "2024-11-04", "2024-11-23",
    "2025-01-01", "2025-01-13", "2025-02-11", "2025-02-23", "2025-02-24", "2025-03-20", "2025-04-29", "2025-05-03", "2025-05-04",
    "2025-05-05", "2025-05-06", "2025-07-21", "2025-08-11", "2025-09-15", "2025-09-23", "2025-10-13", "2025-11-03", "2025-11-23",
    "2025-11-24"])
days = pd.date_range("2024-01-01", "2025-12-31")
WD = np.array([1.00, 0.95, 0.97, 1.02, 1.18, 1.55, 1.45])  # 月〜日
df = pd.DataFrame({"date": days})
df["holiday"] = df.date.isin(HOL)
df["dow"] = df.date.dt.dayofweek
eff = np.where(df.holiday, 6, df.dow)  # 祝日は日曜と同じ
season = 1 + 0.08 * np.sin(2 * np.pi * (df.date.dt.dayofyear - 80) / 365)
growth = np.where(df.date.dt.year == 2025, 1.03, 1.0)
noise = rng.lognormal(0, 0.03, len(df))
df["sales"] = np.round(300000 * WD[eff] * season * growth * noise, -2)
df.to_csv(RES / "daily_sales.csv", index=False)
s = df.set_index("date").sales
h = df.set_index("date").holiday

d25 = pd.date_range("2025-01-01", "2025-12-31")
rows = []
for d in d25:
    p1 = pd.Timestamp(2024, d.month, d.day)
    p2 = d - pd.Timedelta(days=364)
    rows.append({"date": d, "D1": s[d] / s[p1] - 1, "D2": s[d] / s[p2] - 1, "hol_mismatch": bool(h[d] != h[p2]),
                 "dow_mismatch": p1.dayofweek != d.dayofweek})
y = pd.DataFrame(rows).set_index("date")
y["D3"] = y.D2.where(~y.hol_mismatch)
y.round(5).to_csv(RES / "daily_yoy.csv")
TRUE = 0.03
summ = {}
for k in ["D1", "D2", "D3"]:
    v = y[k].dropna() * 100
    summ[k] = {"days": int(len(v)), "sd_pt": round(float(v.std()), 2), "p10": round(float(v.quantile(0.1)), 1), "p90": round(float(v.quantile(0.9)), 1),
               "minus_days": int((v < 0).sum()), "minus_pct": round(float((v < 0).mean() * 100), 1),
               "abs_err_over_10pt": int(((v - 3).abs() > 10).sum()), "mean": round(float(v.mean()), 2)}
# 7日の合計・月の合計で比べる
agg = {}
for k, per in [("week", 7), ("month", None)]:
    if per:
        idx = (np.arange(len(d25)) // 7)
        cur = s[d25].groupby(idx).sum()[:52]
        prv1 = pd.Series([s[pd.Timestamp(2024, d.month, d.day)] for d in d25]).groupby(idx).sum()[:52]
        prv2 = s[d25 - pd.Timedelta(days=364)].reset_index(drop=True).groupby(idx).sum()[:52]
    else:
        cur = s[d25].groupby(d25.month).sum()
        prv1 = s[pd.date_range("2024-01-01", "2024-12-31")].groupby(pd.date_range("2024-01-01", "2024-12-31").month).sum()
        prv2 = s[d25 - pd.Timedelta(days=364)].groupby(d25.month).sum()
    a1 = (cur.values / prv1.values - 1) * 100; a2 = (cur.values / prv2.values - 1) * 100
    agg[k] = {"D1_sd": round(float(a1.std(ddof=1)), 2), "D2_sd": round(float(a2.std(ddof=1)), 2),
              "D1_minus": int((a1 < 0).sum()), "D2_minus": int((a2 < 0).sum()), "n": int(len(a1)),
              "D1_range": [round(float(a1.min()), 1), round(float(a1.max()), 1)], "D2_range": [round(float(a2.min()), 1), round(float(a2.max()), 1)]}
    if k == "month":
        mon = pd.DataFrame({"D1": a1, "D2": a2}, index=range(1, 13)); mon.round(2).to_csv(RES / "monthly_yoy.csv")
# 符号が逆
opp = int(((y.D1 < 0) != (y.D2 < 0)).sum())
# 曜日がずれる組み合わせごとの D1 の平均（2025年は前年の同じ日付より曜日が1つ後ろ…2024年はうるう年なので3/1以降は2つ）
y["shift"] = [(d.dayofweek - pd.Timestamp(2024, d.month, d.day).dayofweek) % 7 for d in y.index]
by_dow = (y.assign(dow=y.index.dayofweek).groupby("dow")[["D1", "D2"]].mean() * 100).round(2)
by_dow.to_csv(RES / "by_weekday.csv")
out = {"true_growth_pct": 3.0, "summary": summ, "aggregated": agg, "days_opposite_sign_D1_D2": opp,
       "days_holiday_mismatch_D2": int(y.hol_mismatch.sum()), "by_weekday_D1_mean": by_dow.D1.to_dict(), "by_weekday_D2_mean": by_dow.D2.to_dict(),
       "weekday_shift_counts": y["shift"].value_counts().sort_index().to_dict()}
json.dump(out, open(RES / "a603_main.json", "w"), ensure_ascii=False, indent=1, default=int)

# 図1：3月の日ごとの前年比
m = y.loc["2025-03-01":"2025-04-30"]
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(m.index, m.D1 * 100, color=ORANGE, marker="o", ms=3, lw=1, label="前年の同じ日付と比べる")
ax.plot(m.index, m.D2 * 100, color=BLUE, marker="s", ms=3, lw=1, label="364日前（同じ曜日）と比べる")
ax.axhline(3, color=GREEN, ls="--", lw=1, label="本当の伸び +3%"); ax.axhline(0, color=GRAY, lw=0.8)
ax.set_ylabel("前年比（%）"); ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13))
ax.set_title("2025年3〜4月の日ごとの前年比", pad=28)
fig.autofmt_xdate()
save(fig, "a603_daily_mar_apr.png", SRC, y=-0.06)
# 図2：分布の比較
fig, ax = plt.subplots(figsize=(8, 3.8))
data = [y[k].dropna() * 100 for k in ["D1", "D2", "D3"]]
lab = ["前年の同じ日付", "364日前\n（同じ曜日）", "364日前、祝日の\n有無が違う日を除く"]
bp = ax.boxplot(data, orientation="horizontal", tick_labels=lab, widths=0.5, patch_artist=True, showfliers=True, flierprops={"markersize": 3})
for b, c in zip(bp["boxes"], [ORANGE, BLUE, GREEN]):
    b.set_facecolor(c); b.set_alpha(0.6)
ax.axvline(3, color=GREEN, ls="--", lw=1); ax.axvline(0, color=GRAY, lw=0.8)
for i, k in enumerate(["D1", "D2", "D3"]):
    ax.text(ax.get_xlim()[1], i + 1, f" マイナス {summ[k]['minus_days']}日", va="center", fontsize=9)
ax.set_xlabel("2025年の日ごとの前年比（%）。本当の伸びは +3%"); ax.invert_yaxis()
ax.set_title("日ごとの前年比の散らばり")
save(fig, "a603_yoy_spread.png", SRC, y=-0.08)
# 図3：曜日ごとの平均
fig, ax = plt.subplots(figsize=(8, 3.6))
x = np.arange(7); wdl = ["月", "火", "水", "木", "金", "土", "日"]
ax.bar(x - 0.2, by_dow.D1, 0.4, color=ORANGE, label="前年の同じ日付")
ax.bar(x + 0.2, by_dow.D2, 0.4, color=BLUE, label="364日前（同じ曜日）")
ax.axhline(3, color=GREEN, ls="--", lw=1); ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{w}曜" for w in wdl]); ax.set_ylabel("前年比の平均（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("曜日ごとの前年比の平均：同じ日付で比べると、曜日で偏る")
save(fig, "a603_by_weekday.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))
