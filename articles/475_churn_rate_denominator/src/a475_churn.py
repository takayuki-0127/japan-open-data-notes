"""475 解約率の分母を4通りに変えると、月次と年率はどれだけ変わるか（架空の会員データ）"""
import json
import numpy as np, pandas as pd, matplotlib.pyplot as plt, duckdb
from common import *

rng = np.random.default_rng(475)
M1, M2, M3 = 0.12, 0.06, 0.025          # 入会30日まで／31〜90日／91日以降の「30日あたり解約確率」
h = [-np.log(1 - x) / 30 for x in (M1, M2, M3)]


def tenure(n, r):
    """解約までの在籍日数（入会からの日数によって解約しやすさが違う）"""
    e = r.exponential(1, n); H1 = h[0] * 30; H2 = H1 + h[1] * 60
    return np.where(e < H1, e / h[0], np.where(e < H2, 30 + (e - H1) / h[1], 90 + (e - H2) / h[2]))


MONTHS = pd.date_range("2023-01-01", "2026-01-01", freq="MS")
START, END = MONTHS[0], MONTHS[-1]


def joins_plan(kind="base"):
    j = []
    for i in range(36):
        if kind == "base":
            if i < 12: v = 2200 + 250 * i                  # 2023年：伸びている
            elif i < 24: v = 2600                          # 2024年：横ばい
            else: v = 2400 - 140 * (i - 24)                # 2025年：新規が減っていく
            if i in (3, 9, 15, 27): v *= 2.2               # キャンペーンの月
        else: v = kind
        j.append(int(v))
    return j


def simulate(plan, r, n0=40000):
    jd = [np.full(n0, -400)]                               # 最初からいる会員（入会から91日以上たっている）
    cd = [np.floor(r.exponential(1, n0) / h[2])]
    for i, n in enumerate(plan):
        d0 = (MONTHS[i] - START).days; dim = (MONTHS[i + 1] - MONTHS[i]).days
        j = d0 + r.integers(0, dim, n); jd.append(j); cd.append(j + np.floor(tenure(n, r)))
    jd = np.concatenate(jd).astype(int); cd = np.concatenate(cd).astype(int)   # cd＝最後に在籍した日
    return jd, cd


def monthly(jd, cd):
    out = []
    horizon = (END - START).days
    for i in range(36):
        a = (MONTHS[i] - START).days; b = (MONTHS[i + 1] - START).days; dim = b - a
        ns = int(((jd < a) & (cd >= a)).sum()); ne = int(((jd < b) & (cd >= b)).sum())
        nj = int(((jd >= a) & (jd < b)).sum()); can = (cd >= a) & (cd < b); nc = int(can.sum()); ncn = int((can & (jd >= a)).sum())
        days = int((np.minimum(cd, b - 1) - np.maximum(jd, a) + 1).clip(0).sum())
        out.append(dict(month=MONTHS[i].strftime("%Y-%m"), n_start=ns, n_end=ne, n_join=nj, n_cancel=nc, n_cancel_new=ncn, member_days=days,
                        churn_start=100 * nc / ns, churn_avg=100 * nc / ((ns + ne) / 2), churn_any=100 * nc / (ns + nj), churn_days=100 * nc / (days / dim),
                        churn_start_only=100 * (nc - ncn) / ns, join_ratio=100 * nj / ns))
    return pd.DataFrame(out)


jd, cd = simulate(joins_plan(), rng)
mem = pd.DataFrame({"member_id": np.arange(len(jd)) + 1, "join_date": START + pd.to_timedelta(jd, "D"), "cancel_date": START + pd.to_timedelta(cd, "D")})
mem.loc[mem.cancel_date >= END, "cancel_date"] = pd.NaT           # 期間の後の解約はまだ起きていない
mem.sample(2000, random_state=0).sort_values("member_id").to_csv(DATA / "members_sample.csv", index=False, encoding="utf-8-sig")
m = monthly(jd, cd)
m.round(3).to_csv(RES / "monthly_four_ways.csv", index=False, encoding="utf-8-sig")
DEF = ["churn_start", "churn_avg", "churn_any", "churn_days"]
NM = {"churn_start": "①期首人数", "churn_avg": "②期首と期末の平均", "churn_any": "③1日でも在籍した人数", "churn_days": "④在籍日数"}

# ---- SQL と一致するか
con = duckdb.connect()
con.register("members", mem)
con.register("months", pd.DataFrame({"month_start": MONTHS[:-1], "next_start": MONTHS[1:], "days_in_month": [(MONTHS[i + 1] - MONTHS[i]).days for i in range(36)]}))
con.register("days", pd.DataFrame({"d": pd.date_range(START, END - pd.Timedelta(days=1))}))
sq = con.execute(open(SQL / "01_churn_tsql.sql", encoding="utf-8").read()).df()
for c in ["n_start", "n_end", "n_join", "n_cancel", "n_cancel_new", "member_days"] + DEF:
    assert np.allclose(sq[c].astype(float).values, m[c].values), c
print("SQL 一致", len(sq))

# ---- 月次の差
m["year"] = m.month.str[:4]
gap = m.assign(g13=m.churn_start - m.churn_any, g12=m.churn_start - m.churn_avg, g14=m.churn_start - m.churn_days, ratio13=m.churn_start / m.churn_any)
by_year = gap.groupby("year").agg(期首人数=("churn_start", "mean"), 平均=("churn_avg", "mean"), 在籍あり=("churn_any", "mean"), 在籍日数=("churn_days", "mean"),
                                  期首にいた人だけ=("churn_start_only", "mean"), 入会の比率=("join_ratio", "mean"), 差_1と3=("g13", "mean"), 最大差_1と3=("g13", "max")).round(2)
print(by_year.to_string())
d = m[DEF].diff().iloc[1:]
flips = {f"{NM[a]}×{NM[b]}": int((np.sign(d[a]) != np.sign(d[b])).sum()) for i, a in enumerate(DEF) for b in DEF[i + 1:]}
any_flip = int((np.sign(d).nunique(axis=1) > 1).sum())
worst = {NM[c]: m.month[m[c].idxmax()] for c in DEF}; best = {NM[c]: m.month[m[c].idxmin()] for c in DEF}
rank_corr = m[DEF].corr(method="spearman").round(3)
camp = m.iloc[[3, 9, 15, 27]]; noncamp = m.drop(index=[3, 9, 15, 27])
print(flips, any_flip, worst, best); print(rank_corr.to_string())
print(camp[["month", "join_ratio"] + DEF + ["churn_start_only"]].round(2).to_string())
corr_gap = float(np.corrcoef(gap.join_ratio, gap.g13)[0, 1])

# ---- 年率
ann = []
for y in (2023, 2024, 2025):
    a = (pd.Timestamp(f"{y}-01-01") - START).days; b = (pd.Timestamp(f"{y+1}-01-01") - START).days
    at = (jd < a) & (cd >= a); n0 = at.sum(); left = (at & (cd < b)).sum(); allc = ((cd >= a) & (cd < b)).sum()
    mm = m[m.year == str(y)]
    row = dict(year=y, 年初の会員=int(n0), 年初の会員のうち年末までに解約_pct=100 * left / n0, 年間の解約数を年初の会員で割る_pct=100 * allc / n0,
               年間の解約数を平均会員数で割る_pct=100 * allc / mm[["n_start", "n_end"]].mean().mean())
    for c in DEF:
        mu = mm[c].mean() / 100
        row[f"{NM[c]}_月平均_pct"] = 100 * mu; row[f"{NM[c]}_12倍_pct"] = 1200 * mu; row[f"{NM[c]}_複利_pct"] = 100 * (1 - (1 - mu) ** 12)
        row[f"{NM[c]}_各月の積_pct"] = 100 * (1 - np.prod(1 - mm[c].values / 100))
    ann.append(row)
A = pd.DataFrame(ann); A.round(2).to_csv(RES / "annual_rates.csv", index=False, encoding="utf-8-sig")
print(A.round(1).T.to_string())

# ---- 新規の多さを変える（解約のしやすさは同じ。最初の会員4万人、最初の12か月）
sw = []
for jr in [0, 2, 5, 10, 20, 30, 50]:
    res = []
    for s in range(20):
        r = np.random.default_rng(5000 + 100 * jr + s)
        j2, c2 = simulate([int(40000 * jr / 100)] * 36, r); mm = monthly(j2, c2).iloc[0:12]
        res.append([mm[c].mean() for c in DEF] + [mm.churn_start_only.mean(), mm.join_ratio.mean()])
    res = np.array(res).mean(0)
    sw.append(dict(毎月の入会_期首比pct=round(res[5], 1), 期首人数=round(res[0], 2), 平均=round(res[1], 2), 在籍あり=round(res[2], 2), 在籍日数=round(res[3], 2), 期首にいた人だけ=round(res[4], 2),
                   最大と最小の差pt=round(res[:4].max() - res[:4].min(), 2), 最大は最小の何倍=round(res[:4].max() / res[:4].min(), 2)))
SW = pd.DataFrame(sw); SW.to_csv(RES / "sweep_join_ratio.csv", index=False, encoding="utf-8-sig"); print(SW.to_string())

J = dict(members=int(len(jd)), initial=40000, joined=int(len(jd) - 40000), cancelled_in_period=int(mem.cancel_date.notna().sum()), hazards_30d_pct=[12, 6, 2.5],
         mean_by_def={NM[c]: round(m[c].mean(), 2) for c in DEF}, mean_start_only=round(m.churn_start_only.mean(), 2),
         new_cancel_share_pct=round(100 * m.n_cancel_new.sum() / m.n_cancel.sum(), 1),
         gap13_mean=round(gap.g13.mean(), 2), gap13_max=round(gap.g13.max(), 2), gap13_max_month=gap.month[gap.g13.idxmax()], gap13_min=round(gap.g13.min(), 2),
         ratio13_mean=round(gap.ratio13.mean(), 3), ratio13_max=round(gap.ratio13.max(), 3), gap12_mean=round(gap.g12.mean(), 2), gap12_max=round(gap.g12.max(), 2), gap14_mean=round(gap.g14.mean(), 2), gap14_max=round(gap.g14.max(), 2),
         max_min_range_mean=round((m[DEF].max(axis=1) - m[DEF].min(axis=1)).mean(), 2), max_min_range_max=round((m[DEF].max(axis=1) - m[DEF].min(axis=1)).max(), 2),
         corr_gap_joinratio=round(corr_gap, 3), by_year=by_year.reset_index().to_dict(orient="records"), flips=flips, months_any_flip=any_flip, months_compared=35,
         worst_month=worst, best_month=best, campaign=camp[["month", "join_ratio"] + DEF + ["churn_start_only"]].round(2).to_dict(orient="records"),
         annual=A.round(2).to_dict(orient="records"), sweep=sw)
json.dump(J, open(RES / "a475_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1 月次
COL = {"churn_start": ORANGE, "churn_avg": GREEN, "churn_any": BLUE, "churn_days": INK}
x = np.arange(36)
fig, ax = plt.subplots(figsize=(10.4, 4.8))
for c in DEF: ax.plot(x, m[c], color=COL[c], lw=1.8 if c != "churn_days" else 1.2, ls="-" if c != "churn_days" else "--", label=NM[c], marker="o", ms=2.5)
ax.plot(x, m.churn_start_only, color=GRAY, lw=1.2, ls=":", label="（参考）期首にいた人の解約だけを期首人数で割る")
for i in (3, 9, 15, 27): ax.axvline(i, color=LIGHT, lw=6, alpha=0.5, zorder=0)
ax.text(3.3, m[DEF].values.max() * 1.04, "薄い帯＝キャンペーンで入会が多い月", fontsize=8.5, color=GRAY)
for a, t in ((0, "2023年：入会が増えていく"), (12, "2024年：横ばい"), (24, "2025年：入会が減っていく")):
    ax.axvline(a - 0.5, color=GRAY, lw=0.6); ax.text(a, m[DEF].values.min() * 0.80, t, fontsize=8.5, color=GRAY)
ax.set_xticks(x[::3]); ax.set_xticklabels(m.month[::3], fontsize=8, rotation=30); ax.set_ylabel("月次の解約率（%）"); ax.set_ylim(m[DEF].values.min() * 0.75, m[DEF].values.max() * 1.1)
ax.legend(fontsize=8.5, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18)); ax.set_title("同じ会員データの月次解約率：分母を4通りに変えると", loc="left")
save(fig, "a475_monthly.png", "架空データ（乱数の種475、会員 約14万人・36か月）。解約の数（分子）は4つとも同じ", y=-0.14)

# ---- 図2 差と入会の比率
fig, axs = plt.subplots(1, 2, figsize=(10.6, 4.5))
axs[0].scatter(gap.join_ratio, gap.g13, color=BLUE, s=22, label="①期首人数 − ③1日でも在籍")
axs[0].scatter(gap.join_ratio, gap.g12, color=GREEN, s=22, marker="s", label="①期首人数 − ②平均")
axs[0].axhline(0, color=GRAY, lw=0.8); axs[0].set_xlabel("その月の入会数 ÷ 期首の会員数（%）"); axs[0].set_ylabel("解約率の差（ポイント）"); axs[0].legend(fontsize=8.5, frameon=False)
axs[0].set_title("入会が多い月ほど差が開く（36か月）", loc="left", fontsize=11)
xs = SW["毎月の入会_期首比pct"]
for c, k in (("期首人数", "churn_start"), ("平均", "churn_avg"), ("在籍あり", "churn_any"), ("在籍日数", "churn_days")):
    axs[1].plot(xs, SW[c], color=COL[k], marker="o", ms=3.5, ls="--" if k == "churn_days" else "-", label=NM[k])
axs[1].plot(xs, SW["期首にいた人だけ"], color=GRAY, ls=":", label="（参考）期首にいた人だけ")
axs[1].set_xlabel("毎月の入会数 ÷ 期首の会員数（%）"); axs[1].set_ylabel("月次の解約率（%）、12か月の平均"); axs[1].legend(fontsize=8, frameon=False)
axs[1].set_title("入会の多さだけを変えたとき", loc="left", fontsize=11)
fig.suptitle("分母による差は、新しく入った人の多さで決まる", x=0.01, ha="left", fontsize=13); fig.tight_layout()
save(fig, "a475_gap_vs_joins.png", "架空データ。右は会員4万人・解約のしやすさは同じにして、入会の数だけを変えた20回ずつの平均")

# ---- 図3 年率
fig, ax = plt.subplots(figsize=(10.4, 4.8))
yrs = [2023, 2024, 2025]; w = 0.105; k = 0
series = [("①期首人数_12倍_pct", ORANGE, "①を12倍"), ("①期首人数_複利_pct", "#f3a98c", "①を複利で1年分"), ("③1日でも在籍した人数_12倍_pct", BLUE, "③を12倍"), ("③1日でも在籍した人数_複利_pct", LIGHT, "③を複利で1年分"),
          ("④在籍日数_12倍_pct", INK, "④を12倍"), ("年間の解約数を年初の会員で割る_pct", GRAY, "年間の解約数 ÷ 年初の会員"), ("年初の会員のうち年末までに解約_pct", GREEN, "年初にいた会員のうち\n年末までに解約した割合")]
for k, (c, colr, nm) in enumerate(series):
    xx = np.arange(3) + (k - 3) * w * 1.15
    ax.bar(xx, A[c], w, color=colr, label=nm)
    for a, v in zip(xx, A[c]): ax.text(a, v + 0.8, f"{v:.0f}", ha="center", fontsize=7.5)
ax.set_xticks(np.arange(3)); ax.set_xticklabels([f"{y}年" for y in yrs]); ax.set_ylabel("年率（%）"); ax.set_ylim(0, A[[s[0] for s in series]].values.max() * 1.18)
ax.legend(fontsize=8, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08)); ax.set_title("月次の解約率を年率に直すと：分母と直し方でどれだけ違うか", loc="left")
save(fig, "a475_annual.png", "架空データ（乱数の種475）。月次は各年12か月の平均を使った", y=-0.2)
