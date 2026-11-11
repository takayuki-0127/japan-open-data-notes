"""A247 日本人の泊まりがけ旅行は、平日に移ったのか（月の休日の数で回帰）
月の延べ宿泊者数（1日あたり、対数）を、その月の休日（土日・祝日・振替休日）の日数で説明する。
月の違い（季節）と年の違い（景気・コロナ後の戻り）は、月と年のダミーで取り除く。"""
import json, datetime as dt
import numpy as np, pandas as pd, jpholiday
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from common import table, DATA, RES, FIG, GRAY, days, note
from common import C as COL


def offdays(y, m, holidays=True):
    k = 0
    for d in range(1, days(y, m) + 1):
        x = dt.date(y, m, d)
        if x.weekday() >= 5 or (holidays and jpholiday.is_holiday(x)):
            k += 1
    return k


t2 = table(2); m = t2[t2.month > 0].copy()
m["days"] = [days(y, mo) for y, mo in zip(m.year, m.month)]
m["off"] = [offdays(y, mo) for y, mo in zip(m.year, m.month)]
m["off_we"] = [offdays(y, mo, False) for y, mo in zip(m.year, m.month)]
m["jp"] = m.total - m.foreign                 # 日本人（全施設）
m["jp_tour"] = m.tour - m.foreign_tour        # 日本人（観光目的の宿泊者が50%以上の施設）
m["jp_biz"] = m.biz - m.foreign_biz           # 日本人（観光目的の宿泊者が50%未満の施設）
m["fr"] = m.foreign
m[["year", "month", "days", "off", "off_we"]].to_csv(RES / "a247_calendar.csv", index=False)

PER = {"2015〜2019年": (2015, 2019), "2023〜2025年": (2023, 2025)}
VARS = {"jp": "日本人（全施設）", "jp_tour": "日本人・観光の宿", "jp_biz": "日本人・出張などの宿", "fr": "外国人（全施設）"}


def fit(d, v, x="off", extra=""):
    d = d.copy(); d["l"] = np.log(d[v] / d["days"])
    r = smf.ols(f"l~{x}+C(month)+C(year){extra}", d).fit(cov_type="HC1")
    return 100 * r.params[x], 100 * 1.96 * r.bse[x], r.pvalues[x], len(d)


rows = []
for v, vn in VARS.items():
    for p, (a, b) in PER.items():
        e, ci, pv, n = fit(m[(m.year >= a) & (m.year <= b)], v)
        rows.append({"series": v, "label": vn, "period": p, "pct_per_offday": round(e, 2), "ci95": round(ci, 2), "p": round(pv, 3), "n": n})
main = pd.DataFrame(rows); main.to_csv(RES / "a247_main.csv", index=False)

# 差の検定（2つの期間をまとめ、休日×後の期間の交差項）
diff = []
q = m[(m.year <= 2019) | (m.year >= 2023)].copy(); q["post"] = (q.year >= 2023).astype(int)
for v in VARS:
    q["l"] = np.log(q[v] / q["days"])
    r = smf.ols("l~off+off:post+C(month)+C(year)", q).fit(cov_type="HC1")
    diff.append({"series": v, "diff_pct": round(100 * r.params["off:post"], 2), "ci95": round(100 * 1.96 * r.bse["off:post"], 2), "p": round(r.pvalues["off:post"], 3)})
diff = pd.DataFrame(diff); diff.to_csv(RES / "a247_diff_test.csv", index=False)

# 頑健性
rob = []
s = pd.read_csv(DATA / "suii_national_monthly_2011_2025.csv")
s["days"] = [days(y, mo) for y, mo in zip(s.year, s.month)]
s["off"] = [offdays(y, mo) for y, mo in zip(s.year, s.month)]
for p, (a, b) in {"2011〜2019年（推移表）": (2011, 2019), "2012〜2019年（推移表・震災の年を除く）": (2012, 2019), "2023〜2025年（推移表）": (2023, 2025)}.items():
    e, ci, pv, n = fit(s[(s.year >= a) & (s.year <= b)], "japanese")
    rob.append({"check": "日本人（全施設）" + p, "pct_per_offday": round(e, 2), "ci95": round(ci, 2), "p": round(pv, 3), "n": n})
for p, (a, b) in PER.items():
    d = m[(m.year >= a) & (m.year <= b)]
    e, ci, pv, n = fit(d, "jp_tour", x="off_we")
    rob.append({"check": f"日本人・観光の宿 {p}：土日だけ数える", "pct_per_offday": round(e, 2), "ci95": round(ci, 2), "p": round(pv, 3), "n": n})
    e, ci, pv, n = fit(d[~d.month.isin([1, 5, 8, 12])], "jp_tour")
    rob.append({"check": f"日本人・観光の宿 {p}：1・5・8・12月を除く", "pct_per_offday": round(e, 2), "ci95": round(ci, 2), "p": round(pv, 3), "n": n})
rob = pd.DataFrame(rob); rob.to_csv(RES / "a247_robustness.csv", index=False)
# 推移表と年の確定値（第2表）の全国の月の値（総数）が一致するか
mm = s.merge(m[["year", "month", "total"]], on=["year", "month"], suffixes=("_suii", "_t2"))
match = {"months": int(len(mm)), "max_abs_diff": float((mm.total_suii - mm.total_t2).abs().max())}

# 休日の日数の範囲
rng = m.groupby("month").off.agg(["min", "max"])
summary = {"main": main.to_dict(orient="records"), "diff": diff.to_dict(orient="records"), "robust": rob.to_dict(orient="records"),
           "suii_vs_table2_total": match, "offdays_range_overall": [int(m.off.min()), int(m.off.max())], "offdays_minmax_by_month": rng.to_dict(orient="index")}
json.dump(summary, open(RES / "a247_summary.json", "w"), ensure_ascii=False, indent=1)

# 図1：休日が1日多い月の増え方（95%区間）
fig, ax = plt.subplots(figsize=(8, 4.6))
labs = list(VARS.values()); y = np.arange(len(labs))
for j, (p, col) in enumerate(zip(PER, [GRAY, COL[0]])):
    d = main[main.period == p].set_index("label").loc[labs]
    ax.errorbar(d.pct_per_offday, y + (0.15 if j == 0 else -0.15), xerr=d.ci95, fmt="o", color=col, capsize=3, label=p, lw=2)
    for yy, v in zip(y + (0.15 if j == 0 else -0.15), d.pct_per_offday):
        ax.text(v, yy + 0.12, f"{v:+.1f}%", ha="center", fontsize=8, color=col)
ax.axvline(0, color="#888", lw=0.8); ax.set_yticks(y); ax.set_yticklabels(labs); ax.invert_yaxis()
ax.set_xlabel("休日が1日多い月の、1日あたり延べ宿泊者数の違い（%、線は95%区間）")
ax.set_title("休日が1日多い月に、宿泊はどれだけ増えるか"); ax.legend(frameon=False, fontsize=9, loc="lower right")
note(ax, y=-0.04); fig.savefig(FIG / "a247_coef.png"); plt.close(fig)

# 図2：観光の宿の日本人（季節と年を除いた残り）と休日の日数
fig, axs = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
for ax, (p, (a, b)), col in zip(axs, PER.items(), [GRAY, COL[0]]):
    d = m[(m.year >= a) & (m.year <= b)].copy(); d["l"] = np.log(d.jp_tour / d.days)
    res = smf.ols("l~C(month)+C(year)", d).fit().resid * 100
    offr = smf.ols("off~C(month)+C(year)", d).fit().resid
    ax.scatter(offr, res, color=col, s=22)
    b1 = np.polyfit(offr, res, 1); xs = np.linspace(offr.min(), offr.max(), 10)
    ax.plot(xs, np.polyval(b1, xs), color=COL[1], lw=1.5)
    ax.set_title(f"{p}（傾き {b1[0]:+.1f}%／日）", fontsize=11); ax.axhline(0, color="#ccc", lw=0.8)
    ax.set_xlabel("休日の日数（同じ月・同じ年の平均との差）")
axs[0].set_ylabel("1日あたり延べ宿泊者数\n（季節と年の平均との差、%）")
fig.suptitle("観光の宿の日本人：休日の多い月ほど多いか", y=1.02); note(axs[0], y=-0.06)
fig.savefig(FIG / "a247_scatter_tour.png"); plt.close(fig)

# 図3：頑健性
fig, ax = plt.subplots(figsize=(9, 4.8))
yy = np.arange(len(rob))
ax.errorbar(rob.pct_per_offday, yy, xerr=rob.ci95, fmt="o", color=COL[3], capsize=3)
ax.set_yticks(yy); ax.set_yticklabels(rob.check, fontsize=9.5); ax.invert_yaxis(); ax.axvline(0, color="#888", lw=0.8)
ax.set_xlabel("休日が1日多い月の違い（%、線は95%区間）"); ax.set_title("数え方や期間を変えても")
note(ax, y=-0.06); fig.savefig(FIG / "a247_robustness.png"); plt.close(fig)
print(main.to_string()); print(diff.to_string()); print(rob.to_string())
