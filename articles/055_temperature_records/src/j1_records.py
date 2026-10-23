"""J1：日本の気温は「記録更新」がどれだけ起きているか。気温が変わらない（独立で同じ分布）なら、n年目が最高記録になる確率は1/n。
実際の記録更新の回数を、その期待値と比べる（記録統計）。あわせて月別の上昇率（HAC標準誤差）と世界との比較"""
from common import *
import statsmodels.api as sm

an = read("an_jpn.csv").iloc[:, 0]; mon = read("mon_jpn.csv"); wld = read("an_wld.csv")["世界全体"]
mon.columns = [f"{i}月" for i in range(1, 13)]


def records(x):
    """最高記録・最低記録の更新年と、独立同分布のときの期待回数"""
    x = x.dropna(); hi = x.cummax(); lo = x.cummin()
    is_hi = (x == hi) & (x > hi.shift(1).fillna(-np.inf)); is_lo = (x == lo) & (x < lo.shift(1).fillna(np.inf))
    n = np.arange(1, len(x) + 1)
    return is_hi, is_lo, pd.Series(1 / n, index=x.index)


hi, lo, p = records(an)
rec = pd.DataFrame({"anomaly": an, "record_high": hi, "record_low": lo, "p_iid": p})
rec.to_csv(RES / "j1_annual_records.csv", encoding="utf-8-sig")
last = lambda s, k: s.iloc[-k:].sum()
s = {"n_years": len(an), "hi_total": int(hi.sum()), "hi_expected": p.sum(), "lo_total": int(lo.sum()),
     "hi_last30": int(last(hi, 30)), "hi_last30_expected": last(p, 30), "lo_last30": int(last(lo, 30)),
     "hi_years": ",".join(str(y) for y in an.index[hi.values]), "last_low_year": int(an.index[lo.values][-1]),
     "an_2025": an.iloc[-1], "an_max_year": int(an.idxmax()), "an_max": an.max()}

# 月ごと：最近30年（1996〜2025年、2026年は9月まで）に何回最高記録が出たか
mrows = []
for c in mon.columns:
    x = mon[c].loc[:2025]; h, l, q = records(x)
    mrows.append(dict(month=c, hi_last30=int(h.loc[1996:].sum()), lo_last30=int(l.loc[1996:].sum()), expected_last30=q.loc[1996:].sum(),
                      last_record_year=int(x.index[h.values][-1])))
mr = pd.DataFrame(mrows).set_index("month"); mr.round(3).to_csv(RES / "j1_monthly_records.csv", encoding="utf-8-sig"); print(mr)
s.update({"m_hi_last30_total": int(mr.hi_last30.sum()), "m_expected_last30_total": mr.expected_last30.sum(), "m_lo_last30_total": int(mr.lo_last30.sum())})

# 上昇率（℃/100年）：年・月・世界。HAC 標準誤差
def trend(y, a=None, b=None):
    y = y.loc[a:b].dropna(); X = sm.add_constant((y.index.values - y.index.values.mean()) / 100)
    m = sm.OLS(y.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5}); ci = m.conf_int()[1]
    return m.params[1], ci[0], ci[1]
tr = {"日本（年）": trend(an, 1898, 2025), "世界（年）": trend(wld, 1898, 2025), "日本（1991〜2025年）": trend(an, 1991, 2025), "世界（1991〜2025年）": trend(wld, 1991, 2025)}
for c in mon.columns: tr[c] = trend(mon[c], 1898, 2025)
tr = pd.DataFrame(tr, index=["per100y", "lo", "hi"]).T; tr.round(3).to_csv(RES / "j1_trends.csv", encoding="utf-8-sig"); print(tr.round(2))
s.update({"jp_trend": tr.loc["日本（年）", "per100y"], "jp_lo": tr.loc["日本（年）", "lo"], "jp_hi": tr.loc["日本（年）", "hi"], "wld_trend": tr.loc["世界（年）", "per100y"],
          "jp_recent": tr.loc["日本（1991〜2025年）", "per100y"], "wld_recent": tr.loc["世界（1991〜2025年）", "per100y"],
          "max_month": tr.loc[mon.columns, "per100y"].idxmax(), "max_month_v": tr.loc[mon.columns, "per100y"].max(),
          "min_month": tr.loc[mon.columns, "per100y"].idxmin(), "min_month_v": tr.loc[mon.columns, "per100y"].min()})
# 気温が変わらない世界での記録回数の分布（並べ替えで1万回）
rng = np.random.default_rng(0); sims = []
v = an.values
for _ in range(10000):
    z = rng.permutation(v); sims.append((z[-30:] > np.maximum.accumulate(np.r_[-np.inf, z[:-1]])[-30:]).sum())
sims = np.array(sims); s["perm_p_last30"] = (sims >= s["hi_last30"]).mean(); s["perm_max_last30"] = int(sims.max())
pd.Series(s).to_csv(RES / "j1_summary.csv", header=["value"]); print(pd.Series(s))

fig, ax = plt.subplots(figsize=(11, 4.6))
ax.bar(an.index, an.values, color=[ORANGE if v > 0 else BLUE for v in an.values], width=0.8, alpha=0.55)
ax.scatter(an.index[hi.values], an[hi.values], color=ORANGE, edgecolor=INK, s=40, zorder=3, label="その年までの最高記録")
ax.scatter(an.index[lo.values], an[lo.values], color=BLUE, edgecolor=INK, s=40, zorder=3, label="その年までの最低記録")
ax.plot(an.index, an.rolling(11, center=True).mean(), color=INK, lw=1.4, label="11年移動平均")
ax.axhline(0, color=GRAY, lw=0.6); ax.set_ylabel("平年差（℃、1991〜2020年平均との差）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title(f"日本の年平均気温：最高記録の更新{s['hi_total']}回のうち{s['hi_last30']}回が最近30年")
fig.text(0.01, -0.06, SOURCE + "\n（日本の年平均気温偏差。都市化の影響が少ない15地点の平均）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "j1_records.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.4))
xs = np.arange(12)
ax.bar(xs - 0.2, mr.hi_last30, width=0.4, color=ORANGE, label="最高記録の更新（実際）")
ax.bar(xs + 0.2, mr.lo_last30, width=0.4, color=BLUE, label="最低記録の更新（実際）")
ax.plot(xs, mr.expected_last30, color=INK, marker="o", ms=4, lw=1, label="気温が変わらない場合の期待回数")
ax.set_xticks(xs); ax.set_xticklabels(mr.index); ax.set_ylabel("1996〜2025年の回数"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"月別：最近30年の最高記録 {s['m_hi_last30_total']}回（期待値は約{s['m_expected_last30_total']:.0f}回）、最低記録 {s['m_lo_last30_total']}回")
fig.text(0.01, -0.06, SOURCE + "\n（日本の月平均気温偏差。期待回数は、各年の値が独立で同じ分布に従うとき n 年目が記録になる確率 1/n の合計）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "j1_monthly_records.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.4))
t2 = tr.loc[mon.columns]
ax.errorbar(xs, t2.per100y, yerr=[t2.per100y - t2.lo, t2.hi - t2.per100y], fmt="o", color=ORANGE, capsize=3, label="月別")
ax.axhline(s["jp_trend"], color=ORANGE, ls="--", lw=1, label=f"日本・年平均 {s['jp_trend']:.2f}℃/100年")
ax.axhline(s["wld_trend"], color=GRAY, ls="--", lw=1, label=f"世界・年平均 {s['wld_trend']:.2f}℃/100年")
ax.set_xticks(xs); ax.set_xticklabels(mon.columns); ax.set_ylabel("上昇率（℃/100年）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("1898〜2025年の上昇率：日本は世界の約1.7倍")
fig.text(0.01, -0.06, SOURCE + "\n（最小二乗法の傾き。誤差棒は95%区間（HAC標準誤差、ラグ5））", fontsize=7, color="#8a8984")
fig.savefig(FIG / "j1_trends.png"); plt.close(fig)
