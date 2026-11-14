"""753 1年が53週ある年に「第N週」で前年同週比を出すと、何週が別の季節の週と比べられるのか

架空のチェーンの日次売上（2024-01-01〜2027-01-03）。毎年ちょうど3%伸びるように作り、曜日の波・年末年始・
お盆・大型連休・12月の山を置いた。週番号の決め方を3つ変えて、同じ週番号どうしで前年同週比を出す。
  A 1月1日から7日ずつ区切る週、B 日曜始まり・1月1日を含む週が第1週（DATEPART(week) の既定と同じ）、C ISO 週
本当の伸び（+3%）から5ポイント以上ずれた週の数と、53週目の扱いを数える。DuckDB（1スレッド）と pandas で一致を確かめる。seed 753。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空のチェーンの日次売上（作成者が乱数で作成、seed 753）"
rng = np.random.default_rng(753)
days = pd.date_range("2024-01-01", "2027-01-03", freq="D")
wd = np.array([0.92, 0.9, 0.93, 0.97, 1.08, 1.3, 1.25])  # 月〜日
v = []
for d in days:
    f = wd[d.dayofweek] * (1.03 ** (d.year - 2024))
    if d.month == 12 and 20 <= d.day <= 31: f *= 1.35
    if d.month == 1 and d.day <= 3: f *= 0.55
    if (d.month == 4 and d.day >= 29) or (d.month == 5 and d.day <= 5): f *= 1.3
    if d.month == 8 and 13 <= d.day <= 16: f *= 1.25
    f *= 1 + 0.08 * np.sin(2 * np.pi * (d.dayofyear - 100) / 365)
    v.append(int(round(5_000_000 * f * rng.lognormal(0, 0.03), -3)))
D = pd.DataFrame({"d": days, "sales": v})
D.assign(d=D.d.dt.strftime("%Y-%m-%d")).to_csv(DATA / "daily.csv", index=False)

# pandas で週番号
P = D.copy()
P["y"] = P.d.dt.year
P["wk_a"] = (P.d.dt.dayofyear - 1) // 7 + 1
jan1_sun = P.y.map(lambda y: pd.Timestamp(y, 1, 1).dayofweek == 6)
P["wk_b"] = P.d.dt.strftime("%U").astype(int) + np.where(jan1_sun, 0, 1)
iso = P.d.dt.isocalendar()
P["iy"] = iso.year.astype(int); P["wk_c"] = iso.week.astype(int)
W = pd.concat([P.groupby(["y", k]).agg(days=("sales", "size"), sales=("sales", "sum")).reset_index().rename(columns={"y": "yr", k: "wk"}).assign(method=m)
               for m, k in [("A", "wk_a"), ("B", "wk_b")]] +
              [P.groupby(["iy", "wk_c"]).agg(days=("sales", "size"), sales=("sales", "sum")).reset_index().rename(columns={"iy": "yr", "wk_c": "wk"}).assign(method="C")])
W = W[W.yr.between(2024, 2026)]
# DuckDB
con = duckdb.connect(); con.execute("SET threads=1"); con.register("daily", D)
q = [x for x in (SQL / "02_week_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
DW = con.execute(q[0]).df(); DW = DW[DW.yr.between(2024, 2026)]
m1 = W.merge(DW, on=["method", "yr", "wk"], suffixes=("", "_db"))
assert len(m1) == len(W) == len(DW) and (m1.sales == m1.sales_db).all() and (m1.days == m1.days_db).all()
con.register("weekly", DW)
Y = con.execute(q[1]).df()
# pandas の前年同週比
Wp = W.merge(W[["method", "yr", "wk", "days", "sales"]].assign(yr=W.yr + 1), on=["method", "yr", "wk"], how="left", suffixes=("", "_p"))
Wp = Wp[Wp.yr.isin([2025, 2026])].copy()
Wp["yoy"] = (Wp.sales / Wp.sales_p - 1) * 100
chk = Wp.merge(Y, left_on=["method", "yr", "wk"], right_on=["method", "t.yr" if "t.yr" in Y.columns else "yr", "wk"])
assert np.allclose(chk.yoy.round(1).fillna(-999), chk.yoy_pct.astype(float).fillna(-999))
Wp["dev"] = Wp.yoy - 3.0
TH = 5.0
out = {"days": len(D), "true_growth_pct": 3.0, "threshold_pt": TH, "methods": {}}
for m, lab in [("A", "1月1日から7日ずつ"), ("B", "日曜始まり・1月1日を含む週が第1週"), ("C", "ISO 週")]:
    r = {"label": lab}
    for y in [2025, 2026]:
        s = Wp[(Wp.method == m) & (Wp.yr == y)]
        r[str(y)] = {"weeks": int(len(s)), "weeks_no_prev": int(s.yoy.isna().sum()),
                     "weeks_off_5pt": int((s.dev.abs() > TH).sum()),
                     "weeks_short_or_mismatched_days": int(((s.days != 7) | (s.days != s.days_p)).sum()),
                     "max_abs_dev_pt": round(float(s.dev.abs().max()), 1),
                     "last_week": int(s.wk.max()),
                     "last_week_days": int(s[s.wk == s.wk.max()].days.iloc[0]),
                     "last_week_yoy": None if pd.isna(s[s.wk == s.wk.max()].yoy.iloc[0]) else round(float(s[s.wk == s.wk.max()].yoy.iloc[0]), 1),
                     "first_week_yoy": round(float(s[s.wk == 1].yoy.iloc[0]), 1)}
    out["methods"][m] = r
# 364日前（毎日）との比較の参考：ISO 週の 2026-W53 は 2025 年の何と比べればよいか
c53 = P[(P.iy == 2026) & (P.wk_c == 53)]
prev364 = D.set_index("d").sales.reindex(c53.d - pd.Timedelta(days=364)).values
out["iso_2026_w53_dates"] = f"{c53.d.min():%Y-%m-%d}〜{c53.d.max():%Y-%m-%d}"
out["iso_2026_w53_yoy_vs_364days_before"] = round((c53.sales.sum() / prev364.sum() - 1) * 100, 1)
out["iso_2026_w53_vs_2025_w52_pct"] = round((c53.sales.sum() / W[(W.method == "C") & (W.yr == 2025) & (W.wk == 52)].sales.iloc[0] - 1) * 100, 1)
out["iso_2026_w53_vs_2025_w01_pct"] = round((c53.sales.sum() / W[(W.method == "C") & (W.yr == 2025) & (W.wk == 1)].sales.iloc[0] - 1) * 100, 1)
json.dump(out, open(RES / "a753_main.json", "w"), ensure_ascii=False, indent=1)
Wp[["method", "yr", "wk", "days", "days_p", "sales", "sales_p", "yoy"]].round(2).to_csv(RES / "weekly_yoy.csv", index=False)

# 図1：2026年の週ごとの前年同週比（3つの決め方）
fig, ax = plt.subplots(figsize=(9, 4))
for m, c, lab in [("A", GRAY, "A 1月1日から7日ずつ"), ("B", ORANGE, "B 日曜始まり（DATEPART(week)）"), ("C", BLUE, "C ISO 週")]:
    s = Wp[(Wp.method == m) & (Wp.yr == 2026)].sort_values("wk")
    ax.plot(s.wk, s.yoy, marker="o", ms=3, lw=1.3, color=c, label=lab)
ax.axhline(3, color=GREEN, lw=1, ls="--"); ax.text(22, 8, "本当の伸び +3%", color=GREEN, fontsize=9)
ax.set_xlabel("週番号（2026年）"); ax.set_ylabel("前年同週比（%）"); ax.legend(frameon=False, fontsize=8.5, loc="lower center", ncol=3)
ax.set_ylim(-45, 45)
ax.set_title("日曜始まりの週番号では、年の最初と最後の短い週が大きくずれる")
save(fig, "a753_yoy_2026.png", SRC)
# 図2：5ポイント以上ずれた週の数
fig, ax = plt.subplots(figsize=(7.5, 3.6))
labs = ["A 7日ずつ", "B 日曜始まり", "C ISO 週"]; x = np.arange(3)
v25 = [out["methods"][m]["2025"]["weeks_off_5pt"] for m in "ABC"]; v26 = [out["methods"][m]["2026"]["weeks_off_5pt"] for m in "ABC"]
ax.bar(x - 0.18, v25, 0.36, color=LIGHT, label="2025年（前年はうるう年）"); ax.bar(x + 0.18, v26, 0.36, color=BLUE, label="2026年（ISO で53週の年）")
for i in range(3):
    ax.text(i - 0.18, v25[i] + 0.2, str(v25[i]), ha="center"); ax.text(i + 0.18, v26[i] + 0.2, str(v26[i]), ha="center")
ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylabel("本当の伸びから5ポイント以上ずれた週の数")
ax.legend(frameon=False, fontsize=9); ax.set_title("ずれた週の数は少ないが、ずれる週は年の端に集まる")
save(fig, "a753_off_weeks.png", SRC)
# 図3：ISO 2026-W53 を何と比べるか
fig, ax = plt.subplots(figsize=(7.5, 3.6))
labs = ["364日前の7日間", "2025年の第52週", "2025年の第1週"]
vals = [out["iso_2026_w53_yoy_vs_364days_before"], out["iso_2026_w53_vs_2025_w52_pct"], out["iso_2026_w53_vs_2025_w01_pct"]]
ax.bar(labs, vals, color=[BLUE, ORANGE, ORANGE])
for i, val in enumerate(vals):
    ax.text(i, val + (1 if val >= 0 else -4), f"{val:+.1f}%", ha="center")
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_ylabel("2026年の第53週の伸び（%）")
ax.set_title(f"ISO 2026年の第53週（{out['iso_2026_w53_dates']}）は、比べる相手で答えが変わる")
save(fig, "a753_week53.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
