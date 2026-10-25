"""A212 労働分配率は景気の波でどう動くか：四半期の労働分配率をSTLで季節調整し、HPフィルターの循環成分と景気の山・谷の前後（イベントスタディ）で見る"""
from common import *
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.filters.hp_filter import hpfilter

d = load()
G = {"all": "全規模", "all_large": "資本金10億円以上", "all_mid": "1億〜10億円", "all_small": "1千万〜1億円", "mfg": "製造業", "nonmfg": "非製造業"}
LS, SA = {}, {}
for g in G:
    s = labor_share(d, g).dropna()
    LS[g] = s
    SA[g] = s - STL(s.values, period=4, robust=True).fit().seasonal
LS, SA = pd.DataFrame(LS), pd.DataFrame(SA)
prof = (d.ordinary_profit_all)
prof_sa = pd.Series(np.exp(np.log(prof) - STL(np.log(prof).values, period=4, robust=True).fit().seasonal), index=prof.index)
sales_sa = pd.Series(np.exp(np.log(d.sales_all) - STL(np.log(d.sales_all).values, period=4, robust=True).fit().seasonal), index=d.index)
pers_sa = pd.Series(np.exp(np.log(d.personnel_all) - STL(np.log(d.personnel_all).values, period=4, robust=True).fit().seasonal), index=d.index)
pd.concat([LS.add_prefix("ls_raw_"), SA.add_prefix("ls_sa_")], axis=1).round(3).to_csv(RES / "labor_share_quarterly.csv")

out = []
def p(s): out.append(s); print(s)
s = SA["all"]
p(f"期間 {s.index[0]}〜{s.index[-1]}  {len(s)}四半期")
p(f"季節調整済み 全規模: 最高{s.idxmax()} {s.max():.1f}% 最低{s.idxmin()} {s.min():.1f}% 直近{s.index[-1]} {s.iloc[-1]:.1f}%")
for per in ["1960Q1", "1975Q1", "1990Q1", "2000Q1", "2009Q1", "2010Q1", "2019Q4", "2020Q2", "2024Q4", "2026Q2"]:
    p(f"  {per}: {s[pd.Period(per)]:.1f}%")
dec = s.groupby((s.index.year // 10) * 10).mean()
p("10年平均: " + " ".join(f"{k}s {v:.1f}" for k, v in dec.items()))

# HPフィルター（λ=1600）で循環成分
c_ls = hpfilter(s, 1600)[0]
c_pr = hpfilter(np.log(prof_sa[s.index]), 1600)[0] * 100
c_sl = hpfilter(np.log(sales_sa[s.index]), 1600)[0] * 100
c_pe = hpfilter(np.log(pers_sa[s.index]), 1600)[0] * 100
p(f"循環成分の相関: 分配率×経常利益 {np.corrcoef(c_ls, c_pr)[0,1]:.2f}  分配率×売上高 {np.corrcoef(c_ls, c_sl)[0,1]:.2f}  人件費×売上高 {np.corrcoef(c_pe, c_sl)[0,1]:.2f}")
p(f"循環成分の標準偏差: 分配率 {c_ls.std():.2f}pt 経常利益 {c_pr.std():.1f}% 人件費 {c_pe.std():.2f}% 売上高 {c_sl.std():.2f}%")
lagc = {k: np.corrcoef(c_ls.shift(k).dropna(), c_sl[c_ls.shift(k).dropna().index])[0, 1] for k in range(-4, 5)}
p("分配率(t+k)と売上高(t)の循環の相関: " + " ".join(f"k={k}:{v:.2f}" for k, v in lagc.items()))

# イベントスタディ：山・谷の四半期を0として、前後8四半期の分配率（季節調整済み）の変化
def event(dates, win=8):
    rows = {}
    for t in dates:
        q = pd.Period(t, freq="Q")
        if q - win < s.index[0] or q + win > s.index[-1]:
            continue
        rows[t] = [s[q + k] - s[q] for k in range(-win, win + 1)]
    return pd.DataFrame(rows, index=range(-win, win + 1))
EP, ET = event(PEAKS), event(TROUGHS)
EP.round(2).to_csv(RES / "event_peaks.csv"); ET.round(2).to_csv(RES / "event_troughs.csv")
p(f"山 {EP.shape[1]}回: 山から4四半期後の変化 平均{EP.loc[4].mean():+.2f}pt 上がった回数{(EP.loc[4]>0).sum()}/{EP.shape[1]}  4四半期前→山 平均{-EP.loc[-4].mean():+.2f}pt")
p(f"谷 {ET.shape[1]}回: 谷から4四半期後 平均{ET.loc[4].mean():+.2f}pt 下がった回数{(ET.loc[4]<0).sum()}/{ET.shape[1]}  谷から8四半期後 平均{ET.loc[8].mean():+.2f}pt")
# 後退期（山→谷）の変化
rec = []
for pk, tr in zip(PEAKS, TROUGHS):
    a, b = pd.Period(pk, freq="Q"), pd.Period(tr, freq="Q")
    if a < s.index[0]: continue
    rec.append({"peak": pk, "trough": tr, "ls_peak": round(s[a], 2), "ls_trough": round(s[b], 2), "change": round(s[b] - s[a], 2),
                "max_in_window": round(s[a:b + 2].max(), 2), "profit_change_pct": round((prof_sa[b] / prof_sa[a] - 1) * 100, 1),
                "personnel_change_pct": round((pers_sa[b] / pers_sa[a] - 1) * 100, 1)})
R = pd.DataFrame(rec); R.to_csv(RES / "recessions.csv", index=False)
p(f"後退期 {len(R)}回: 山→谷で分配率が上がった回数 {(R.change>0).sum()} 平均{R.change.mean():+.2f}pt 中央値{R.change.median():+.2f}pt")
for _, x in R.iterrows(): p(f"  {x.peak}→{x.trough}: {x.ls_peak}→{x.ls_trough} ({x.change:+.2f}) 経常利益{x.profit_change_pct:+.1f}% 人件費{x.personnel_change_pct:+.1f}%")
# 規模別
for g in ["all_large", "all_mid", "all_small", "mfg", "nonmfg"]:
    sg = SA[g].dropna(); cg = hpfilter(sg, 1600)[0]
    p(f"{G[g]}: 平均{sg.mean():.1f}% 2015年以降平均{sg[sg.index >= pd.Period('2015Q1')].mean():.1f}% 直近{sg.iloc[-1]:.1f}% 循環の標準偏差{cg.std():.2f}pt")
(RES / "summary.txt").write_text("\n".join(out), encoding="utf-8")

# 図1：季節調整済みの分配率と景気後退期
def shade(ax):
    for pk, tr in zip(PEAKS, TROUGHS):
        ax.axvspan(pd.Period(pk, freq="Q").to_timestamp(), pd.Period(tr, freq="Q").to_timestamp(), color="#e8e7e2", lw=0)
x = s.index.to_timestamp()
fig, ax = plt.subplots(figsize=(8.5, 4.8))
shade(ax)
ax.plot(LS["all"].index.to_timestamp(), LS["all"], color=LIGHT, lw=0.8, label="原数値")
ax.plot(x, s, color=BLUE, lw=1.8, label="季節調整済み（STL）")
ax.set_ylabel("労働分配率（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("労働分配率は景気後退期（灰色）に上がり、回復期に下がる")
save(fig, "a212_share.png")

# 図2：山・谷の前後
fig, axs = plt.subplots(1, 2, figsize=(8.5, 4.2), sharey=True)
for ax, E, lab in [(axs[0], EP, "景気の山"), (axs[1], ET, "景気の谷")]:
    for c in E: ax.plot(E.index, E[c], color=LIGHT, lw=0.9)
    ax.plot(E.index, E.mean(axis=1), color=ORANGE if lab == "景気の山" else BLUE, lw=2.5, label=f"平均（{E.shape[1]}回）")
    ax.axvline(0, color=GRAY, lw=1); ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xlabel(f"{lab}からの四半期"); ax.set_title(lab); ax.legend(frameon=False, fontsize=9)
axs[0].set_ylabel("山・谷の四半期との差（ポイント）")
fig.suptitle("山のあと分配率は上がり、谷のあと下がる", y=1.02)
save(fig, "a212_event.png")

# 図3：規模別
fig, ax = plt.subplots(figsize=(8.5, 4.8))
shade(ax)
for g, col in [("all_large", BLUE), ("all_mid", GREEN), ("all_small", ORANGE)]:
    sg = SA[g].dropna(); ax.plot(sg.index.to_timestamp(), sg, color=col, lw=1.5, label=G[g])
ax.set_ylabel("労働分配率（季節調整済み、%）"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title("資本金10億円以上の分配率は2010年代から下がり、中小企業との差が開いた")
save(fig, "a212_size.png")
