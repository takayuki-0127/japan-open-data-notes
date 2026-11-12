"""415 月の途中の実績から、月末の着地をどう見込むか。4つの方法の外れ方
架空の日次売上（小売型40本・法人向け型40本、2022〜2025年）。2023〜2025年の36か月で、5日・10日・20日時点の見込みを比べる。乱数の種は415。"""
import json, calendar
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(415)
days = pd.date_range("2022-01-01", "2025-12-31")
H = pd.read_csv(DATA / "holidays_2022_2025.csv", parse_dates=["日付"])
hol = days.isin(H["日付"])
wd = days.weekday.values
typ = np.where(hol, 7, wd)                                  # 0〜6：月〜日、7：祝日
dom = days.day.values; dim = days.days_in_month.values
ym = days.year.values * 100 + days.month.values
NS = 40
WK = {"小売型": np.array([0.85, 0.85, 0.90, 0.90, 1.05, 1.30, 1.25, 1.20]),
      "法人向け型": np.array([1.10, 1.05, 1.05, 1.05, 1.15, 0.15, 0.05, 0.08])}
# 月の中の波：小売型は25日からやや多い。法人向け型は、月初が少なく、月の最後の5営業日に集まる
biz = (wd < 5) & ~hol
rank_from_end = np.zeros(len(days), int)
for k in np.unique(ym):
    i = np.where((ym == k) & biz)[0]
    rank_from_end[i] = np.arange(len(i), 0, -1)             # その月の営業日を、後ろから数えた番号
WAVE = {"小売型": np.where(dom >= 25, 1.08, 1.0),
        "法人向け型": np.where(biz & (rank_from_end <= 5), 1.6, np.where(dom <= 5, 0.8, 1.0))}

rows = []
for kind in WK:
    for s in range(NS):
        base = np.exp(rng.normal(np.log(1000), 0.5))
        seas = 1 + rng.normal(0, 0.08, 12)                 # 月ごとの季節の強さ
        trend = (1 + rng.normal(0.02, 0.03)) ** ((days - days[0]).days.values / 365)
        mshock = dict(zip(np.unique(ym), np.exp(rng.normal(0, 0.04, len(np.unique(ym))))))
        y = base * WK[kind][typ] * WAVE[kind] * seas[days.month.values - 1] * trend \
            * np.array([mshock[k] for k in ym]) * np.exp(rng.normal(0, 0.10, len(days)))
        rows.append(pd.DataFrame({"系列": f"{kind}{s + 1:02d}", "型": kind, "日付": days, "売上": np.round(y).astype(int)}))
D = pd.concat(rows, ignore_index=True)
D.to_csv(DATA / "daily_sales.csv", index=False)

CUT = (5, 10, 20)
METH = ["①日割りで延ばす", "②前年同月の進み方で延ばす", "③曜日の型で延ばす", "④直近12か月の進み方の平均で延ばす"]
months = [k for k in np.unique(ym) if k >= 202301]
wk_hol = {k: int((hol & (wd < 5) & (ym == k)).sum()) for k in months}       # 平日に当たる祝日の数
out = []
for (sid, kind), g in D.groupby(["系列", "型"], sort=False):
    y = g["売上"].to_numpy(float)
    for k in months:
        i = np.where(ym == k)[0]; n = len(i); act = y[i].sum()
        kp = k - 100; ip = np.where(ym == kp)[0]                             # 前年の同じ月
        hist = [np.where(ym == q)[0] for q in np.unique(ym) if q < k][-12:]  # 直近の12か月
        w_i = np.arange(i[0] - 56, i[0])                                     # 直前の8週間
        w = np.array([y[w_i][typ[w_i] == t].mean() if (typ[w_i] == t).any() else np.nan for t in range(8)])
        w[7] = w[6] if np.isnan(w[7]) else w[7]                              # 直前に祝日がなければ、日曜の型で代える
        for d in CUT:
            mtd = y[i[:d]].sum()
            f1 = mtd * n / d
            f2 = mtd / (y[ip[:d]].sum() / y[ip].sum())
            f3 = mtd + (mtd / w[typ[i[:d]]].sum()) * w[typ[i[d:]]].sum()
            f4 = mtd / np.mean([y[h[:d]].sum() / y[h].sum() for h in hist])
            for name, f in zip(METH, (f1, f2, f3, f4)):
                out.append((sid, kind, k, d, name, act, f, 100 * (f / act - 1), wk_hol[k]))
R = pd.DataFrame(out, columns=["系列", "型", "年月", "時点", "方法", "実績", "見込み", "誤差%", "平日の祝日"])
R["絶対誤差%"] = R["誤差%"].abs()
R.to_csv(RES / "forecasts_all.csv", index=False)

summ = R.groupby(["型", "時点", "方法"]).agg(絶対誤差の中央値=("絶対誤差%", "median"), 絶対誤差の平均=("絶対誤差%", "mean"),
                                         偏り=("誤差%", "mean"), 誤差5パーセント以上の割合=("絶対誤差%", lambda x: 100 * (x >= 5).mean())).round(2).reset_index()
summ.to_csv(RES / "error_summary.csv", index=False)
R["祝日の多い月"] = np.where(R["平日の祝日"] >= 2, "平日の祝日が2日以上", "1日以下")
hs = R[R["時点"] == 10].groupby(["型", "祝日の多い月", "方法"])["絶対誤差%"].median().round(2).reset_index()
hs.to_csv(RES / "error_by_holiday_months_day10.csv", index=False)
n_hol_months = int(sum(v >= 2 for v in wk_hol.values()))
bym = R[R["時点"] == 10].groupby(["型", "方法", R["年月"] % 100])["誤差%"].mean().round(2).reset_index().rename(columns={"年月": "月"})
bym.to_csv(RES / "bias_by_calendar_month_day10.csv", index=False)

# 月の中の進み方（累計の割合）の例：法人向け型01 の 2025年6月と、その前年
ex = D[D["系列"] == "法人向け型01"]["売上"].to_numpy(float)
i, ip = np.where(ym == 202506)[0], np.where(ym == 202406)[0]
prog = pd.DataFrame({"日": np.arange(1, 31), "2025年6月の累計%": 100 * ex[i].cumsum() / ex[i].sum(),
                     "前年6月の累計%": 100 * ex[ip].cumsum() / ex[ip].sum(), "日割り%": 100 * np.arange(1, 31) / 30}).round(2)
prog.to_csv(RES / "progress_example.csv", index=False)

# ---------------- SQL（DuckDB）で①と②（10日時点）を出して、Python と比べる ----------------
db = duckdb.connect(); db.execute("SET threads=1"); db.register("d", D)
q = db.execute("""
WITH m AS (
  SELECT 系列, year(日付) * 100 + month(日付) AS ym, day(last_day(日付)) AS n,
         SUM(売上) AS total, SUM(CASE WHEN day(日付) <= 10 THEN 売上 ELSE 0 END) AS mtd
  FROM d GROUP BY ALL)
SELECT a.系列, a.ym, a.mtd * a.n / 10.0 AS f1, a.mtd / (CAST(p.mtd AS DOUBLE) / p.total) AS f2
FROM m a JOIN m p ON p.系列 = a.系列 AND p.ym = a.ym - 100
WHERE a.ym >= 202301 ORDER BY a.系列, a.ym""").df()
py = R[R["時点"] == 10].pivot_table(index=["系列", "年月"], columns="方法", values="見込み").reset_index().sort_values(["系列", "年月"])
sql_ok = {"①日割り": bool(np.allclose(q.f1.values, py["①日割りで延ばす"].values)), "②前年同月": bool(np.allclose(q.f2.values, py["②前年同月の進み方で延ばす"].values))}
assert all(sql_ok.values()), sql_ok
pd.DataFrame([sql_ok]).to_csv(RES / "sql_check_duckdb.csv", index=False)

g = lambda kind, d, name, col="絶対誤差の中央値": float(summ[(summ["型"] == kind) & (summ["時点"] == d) & (summ["方法"] == name)][col].iloc[0])
main = {"系列の数": {"小売型": NS, "法人向け型": NS}, "見込みを出した月": len(months), "時点": list(CUT),
        "絶対誤差の中央値%": {kind: {str(d): {name: g(kind, d, name) for name in METH} for d in CUT} for kind in WK},
        "偏り（誤差の平均）%": {kind: {str(d): {name: g(kind, d, name, "偏り") for name in METH} for d in CUT} for kind in WK},
        "誤差が5%以上の割合%": {kind: {str(d): {name: g(kind, d, name, "誤差5パーセント以上の割合") for name in METH} for d in CUT} for kind in WK},
        "平日の祝日が2日以上の月の数": n_hol_months, "10日時点・祝日の多い月と少ない月": hs.to_dict("records"),
        "SQLとPythonの一致": sql_ok}
json.dump(main, open(RES / "a415_main.json", "w"), ensure_ascii=False, indent=1)

# ---------------- 図 ----------------
SRC = "架空の日次売上80本（作成者が乱数で作成、seed 415）。祝日は内閣府「国民の祝日」"
COL = dict(zip(METH, (GRAY, BLUE, ORANGE, GREEN)))
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
for a, kind in zip(ax, WK):
    for name in METH:
        a.plot(CUT, [g(kind, d, name) for d in CUT], marker="o", color=COL[name], label=name)
    a.set_xticks(CUT); a.set_xticklabels([f"{d}日時点" for d in CUT]); a.set_title(kind); a.set_ylabel("着地の見込みの誤差（絶対値の中央値、%）"); a.set_ylim(0)
ax[1].legend(frameon=False, fontsize=9)
save(fig, "a415_error_by_day.png", SRC)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for a, kind in zip(ax, WK):
    x = np.arange(len(METH)); w = 0.38
    for j, (lab, c) in enumerate((("1日以下", LIGHT), ("平日の祝日が2日以上", BLUE))):
        v = [float(hs[(hs["型"] == kind) & (hs["祝日の多い月"] == lab) & (hs["方法"] == name)]["絶対誤差%"].iloc[0]) for name in METH]
        b = a.bar(x + (j - 0.5) * w, v, w, color=c, label=f"平日の祝日が{lab}" if lab == "1日以下" else lab)
        for r_, yv in zip(b, v): a.text(r_.get_x() + r_.get_width() / 2, yv, f"{yv:.1f}", ha="center", va="bottom", fontsize=8)
    a.set_xticks(x); a.set_xticklabels(["①日割り", "②前年同月", "③曜日の型", "④12か月平均"]); a.set_title(f"{kind}（10日時点）"); a.set_ylabel("誤差（絶対値の中央値、%）"); a.set_ylim(0, a.get_ylim()[1] * 1.18)
ax[0].legend(frameon=False, fontsize=9, loc="upper left", ncol=2)
save(fig, "a415_holiday_months.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(prog["日"], prog["2025年6月の累計%"], color=BLUE, label="2025年6月の実績")
ax.plot(prog["日"], prog["前年6月の累計%"], color=ORANGE, ls="--", label="前年6月の実績")
ax.plot(prog["日"], prog["日割り%"], color=GRAY, ls=":", label="日割り（毎日同じだけ進むとした線）")
for d in CUT: ax.axvline(d, color=GRAY, lw=0.6)
ax.set_xlabel("日"); ax.set_ylabel("月の売上に対する累計（%）"); ax.set_title("月の中の進み方の例（法人向け型の1本）"); ax.legend(frameon=False)
save(fig, "a415_progress_example.png", SRC)
print(summ.to_string()); print(hs.to_string()); print(n_hol_months)
