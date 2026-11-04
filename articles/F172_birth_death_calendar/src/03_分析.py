"""分析：曜日・祝日・時刻の偏り（日別の出生、2018〜2025年）と、季節の偏り（月別の出生・死亡、1947〜2025年）を円周統計で測る。"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import DATA, RES, WD

rng = np.random.default_rng(172)
d = pd.read_csv(DATA / "births_daily_place_hour.csv", parse_dates=["date"])
mo = pd.read_csv(DATA / "births_deaths_monthly.csv")
out = {}


def daytype(r):
    if r.newyear:
        return "年末年始"
    if r.holiday:
        return "祝日"
    return WD[r.weekday]


d["type"] = d.apply(daytype, axis=1)
TYPES = WD + ["祝日", "年末年始"]

# ---------- A. 曜日の指数（その年の1日平均=100）----------
def index_table(df):
    m = df.groupby("year").births.transform("mean")
    df = df.assign(idx=df.births / m * 100)
    return df.groupby(["year", "type"]).idx.mean().unstack()[TYPES]


tot = d[d.place == "総数"].copy()
it = index_table(tot)
it.round(2).to_csv(RES / "weekday_index_by_year.csv")
pooled = it.mean()
out["weekday_index_pooled"] = pooled.round(1).to_dict()
out["weekday_index_range"] = {t: [round(it[t].min(), 1), round(it[t].max(), 1)] for t in TYPES}
wk = tot[tot.type.isin(WD[:5])].births.mean()
out["sun_vs_weekday_pct"] = round((tot[tot.type == "日"].births.mean() / wk - 1) * 100, 1)
out["sat_vs_weekday_pct"] = round((tot[tot.type == "土"].births.mean() / wk - 1) * 100, 1)
out["hol_vs_weekday_pct"] = round((tot[tot.type == "祝日"].births.mean() / wk - 1) * 100, 1)
out["ny_vs_weekday_pct"] = round((tot[tot.type == "年末年始"].births.mean() / wk - 1) * 100, 1)

# 回帰（年×月の固定効果、log 出生数、HC3）：基準は火曜
tot["ym"] = tot.year.astype(str) + "-" + tot.month.astype(str)
tot["t2"] = pd.Categorical(tot.type, categories=["火"] + [t for t in TYPES if t != "火"])
f = smf.ols("np.log(births) ~ C(t2) + C(ym)", data=tot).fit(cov_type="HC3")
reg = {}
for t in TYPES:
    if t == "火":
        continue
    k = f"C(t2)[T.{t}]"
    b, se = f.params[k], f.bse[k]
    reg[t] = [round((np.exp(b) - 1) * 100, 1), round((np.exp(b - 1.96 * se) - 1) * 100, 1),
              round((np.exp(b + 1.96 * se) - 1) * 100, 1)]
out["reg_vs_tue_pct"] = reg
out["reg_r2"] = round(f.rsquared, 3)

# 週末に「足りない」出生：土日祝・年末年始が平日（月〜金）並みだったら
gap = []
for y, g in tot.groupby("year"):
    wkm = g[g.type.isin(WD[:5])].births.mean()
    lo = g[~g.type.isin(WD[:5])]
    gap.append([y, round((wkm * len(lo) - lo.births.sum()) / g.births.sum() * 100, 1)])
out["weekend_gap_share_pct"] = dict(gap)

# ---------- B. 出生の場所別 ----------
pl = {}
share = d[d.place != "総数"].groupby("place").births.sum()
out["place_share_pct"] = (share / share.sum() * 100).round(2).to_dict()
for p in ["病院", "診療所", "助産所", "自宅"]:
    g = d[d.place == p]
    w = g[g.type.isin(WD[:5])].births.mean()
    pl[p] = {t: round(g[g.type == t].births.mean() / w * 100, 1) for t in TYPES}
pd.DataFrame(pl).T[TYPES].to_csv(RES / "weekday_index_by_place.csv")
out["place_index_vs_weekday"] = pl
# 自宅は1日あたりの件数が少ないので、年ごとの日曜指数の幅も見る
home_sun = []
for y, g in d[d.place == "自宅"].groupby("year"):
    w = g[g.type.isin(WD[:5])].births.mean()
    home_sun.append(round(g[g.type == "日"].births.mean() / w * 100, 1))
out["home_sun_index_by_year"] = home_sun
# 自宅：日曜と平日の差の並べ替え検定（2018〜2025年まとめて、年で層別）
g = d[(d.place == "自宅") & d.type.isin(WD[:5] + ["日"])].copy()
obs = g[g.type == "日"].births.mean() / g[g.type != "日"].births.mean()
sims = []
for _ in range(2000):
    lab = g.groupby("year").type.transform(lambda s: rng.permutation(s.values))
    sims.append(g.births[lab == "日"].mean() / g.births[lab != "日"].mean())
sims = np.array(sims)
out["home_sun_ratio_perm"] = {"obs": round(obs, 3), "p_two_sided": round(float(np.mean(np.abs(sims - 1) >= abs(obs - 1))), 3)}

# ---------- C. 時刻 ----------
H = [f"h{h:02d}" for h in range(24)]
day_hours = [f"h{h:02d}" for h in range(9, 17)]  # 9時台〜16時台
hr = {}
for p in ["総数", "病院", "診療所", "助産所", "自宅"]:
    g = d[d.place == p]
    r = {}
    for lab, mask in [("平日", g.type.isin(WD[:5])), ("日曜・祝日", g.type.isin(["日", "祝日"]))]:
        s = g.loc[mask, H].sum()
        r[lab] = round(s[day_hours].sum() / s.sum() * 100, 1)
    hr[p] = r
out["share_9to16_pct"] = hr
hp = []
for lab, mask in [("平日", tot.type.isin(WD[:5])), ("日曜・祝日", tot.type.isin(["日", "祝日"]))]:
    s = tot.loc[mask, H].sum()
    n = mask.sum()
    hp.append(pd.Series((s / n).values, name=lab))
pd.concat(hp, axis=1).round(1).to_csv(RES / "births_per_hour_per_day.csv", index_label="hour")
# 平日と日曜の差がどの時間帯に集中しているか
diff = (hp[0] - hp[1])
out["weekday_minus_sunday_per_day"] = round(float(diff.sum()), 0)
out["weekday_minus_sunday_share_9to16_pct"] = round(float(diff[9:17].sum() / diff.sum() * 100), 1)
out["night_0to6_ratio_sun_vs_wk"] = round(float(hp[1][0:7].sum() / hp[0][0:7].sum()), 3)


# ---------- D. 季節：円周統計 ----------
def circ(rates, days_mid, ylen=365.25):
    th = 2 * np.pi * np.asarray(days_mid) / ylen
    w = np.asarray(rates, float)
    C, S = (w * np.cos(th)).sum(), (w * np.sin(th)).sum()
    R = np.hypot(C, S) / w.sum()
    mu = (np.arctan2(S, C) % (2 * np.pi)) * ylen / (2 * np.pi)
    return R, mu


def month_info(y):
    import calendar
    days = np.array([calendar.monthrange(y, m)[1] for m in range(1, 13)])
    start = np.concatenate([[0], np.cumsum(days)[:-1]])
    ylen = days.sum()
    return days, start + days / 2, ylen


def doy_to_md(x):
    t = pd.Timestamp("2001-01-01") + pd.Timedelta(days=float(x))
    return f"{t.month}月{t.day}日"


rows = []
for kind in ["births", "deaths"]:
    for y, g in mo.dropna(subset=[kind]).groupby("year"):
        g = g.sort_values("month")
        days, mid, ylen = month_info(int(y))
        rate = g[kind].values / days
        R, mu = circ(rate, mid, ylen)
        Rr, mur = circ(g[kind].values, mid, ylen)  # 月の日数で割らない
        amp = rate.max() / rate.min()
        rows.append([kind, int(y), round(R, 4), round(mu, 1), doy_to_md(mu), round(Rr, 4), round(mur, 1),
                     round(amp, 3), int(np.argmax(rate)) + 1, int(np.argmin(rate)) + 1])
cs = pd.DataFrame(rows, columns=["kind", "year", "R", "mean_doy", "mean_date", "R_raw", "mean_doy_raw",
                                 "max_min_ratio", "peak_month", "low_month"])
cs.to_csv(RES / "season_circular_by_year.csv", index=False)
out["season_sel"] = cs[cs.year.isin([1947, 1960, 1975, 1990, 2005, 2019, 2024, 2025])].to_dict("records")


def era(kind, a, b):
    s = cs[(cs.kind == kind) & cs.year.between(a, b)]
    return {"R_mean": round(s.R.mean(), 4), "R_range": [round(s.R.min(), 4), round(s.R.max(), 4)],
            "n_years": len(s), "peak_months": s.peak_month.value_counts().to_dict()}


out["season_eras"] = {k: {f"{a}-{b}": era(k, a, b) for a, b in [(1947, 1965), (1970, 1995), (2000, 2019), (2020, 2025)]}
                      for k in ["births", "deaths"]}

# 日別（2018〜2025年）の出生で、季節の集中度を測る（月より細かい単位）
dr = []
for y, g in tot.groupby("year"):
    g = g.sort_values("date")
    doy = g.date.dt.dayofyear.values - 0.5
    ylen = len(g)
    Rd, mud = circ(g.births.values, doy, ylen)
    # 曜日の効果を除いた版：曜日・祝日の指数で割る
    adj = g.births.values / g.type.map(pooled / 100).values
    Ra, mua = circ(adj, doy, ylen)
    m = cs[(cs.kind == "births") & (cs.year == y)].iloc[0]
    dr.append([y, round(Rd, 4), doy_to_md(mud), round(Ra, 4), doy_to_md(mua), m.R, m.mean_date])
dr = pd.DataFrame(dr, columns=["year", "R_daily", "mean_daily", "R_daily_wdadj", "mean_daily_wdadj", "R_monthly", "mean_monthly"])
dr.to_csv(RES / "season_daily_vs_monthly_births.csv", index=False)
out["season_daily_vs_monthly"] = dr.to_dict("records")

# 曜日の円（7日周期）の集中度：場所別
wr = {}
for p in ["総数", "病院", "診療所", "助産所", "自宅"]:
    g = d[(d.place == p) & d.type.isin(WD)]
    m = g.groupby("weekday").births.mean().values
    R, _ = circ(m, np.arange(7) + 0.5, 7)
    wr[p] = round(R, 4)
out["weekday_circle_R"] = wr

# 「季節の偏り」と「曜日の偏り」の大きさ比べ（2018〜2025年、出生総数）
out["compare_scale"] = {"season_R_monthly_mean": round(cs[(cs.kind == "births") & cs.year.between(2018, 2025)].R.mean(), 4),
                        "weekday_R_total": wr["総数"]}

# 季節の集中度が「偶然」で出る大きさ：月の値を年の中で並べ替えたとき
null = {}
for kind in ["births", "deaths"]:
    s = cs[(cs.kind == kind) & cs.year.between(2015, 2025)]
    Rs = []
    for y in s.year:
        g = mo[mo.year == y].sort_values("month")
        days, mid, ylen = month_info(int(y))
        rate = g[kind].values / days
        for _ in range(200):
            Rs.append(circ(rng.permutation(rate), mid, ylen)[0])
    null[kind] = {"obs_mean": round(s.R.mean(), 4), "perm_p95": round(float(np.quantile(Rs, 0.95)), 4)}
out["season_perm"] = null

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:9000])
