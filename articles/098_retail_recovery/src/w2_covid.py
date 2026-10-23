"""W2：コロナ前後で売上が戻った業態・戻らない業態

- 2019年比：公表の前年比をつないで「2019年＝100」にする（年は年の前年比、2026年1〜8月は月の前年同月比を使う）
- 月次の水準は、最新の水準から前年同月比で12か月ずつさかのぼって断層を除き、STL（周期12、ロバスト）で季節調整する
- コロナ前の傾向（2014年1月〜2019年12月の季節調整値の対数に直線を当てはめ）を延ばした値と、実際の値の差を見る
- 伸び方が変わったか：コロナ前（2014〜2019年）とコロナ後（2022年1月〜2026年8月）の傾き（年率）を比べる（HAC標準誤差）
"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.tsa.seasonal import STL
from common import load, chain_annual, vs_2019, backcast_monthly, note, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, PURPLE, RED, LIGHT

ya, ym, vm = load("annual_yoy"), load("monthly_yoy"), load("monthly_value")
SER = {"ドラッグストア": "ドラッグストア|商品販売額", "スーパー": "スーパー|合計", "コンビニ": "コンビニ|商品販売額",
       "家電大型専門店": "家電大型専門店|商品販売額", "ホームセンター": "ホームセンター|商品販売額", "百貨店": "百貨店|合計",
       "小売業計": "業種別|小売業計", "医薬品・化粧品小売業": "業種別|医薬品・化粧品小売業", "飲食料品小売業": "業種別|飲食料品小売業",
       "燃料小売業": "業種別|燃料小売業", "機械器具小売業": "業種別|機械器具小売業", "無店舗小売業": "業種別|無店舗小売業",
       "各種商品小売業": "業種別|各種商品小売業", "自動車小売業": "業種別|自動車小売業",
       "織物・衣服・身の回り品小売業": "業種別|織物・衣服・身の回り品小売業",
       "百貨店：身の回り品": "百貨店|身の回り品", "百貨店：衣料品": "百貨店|衣料品", "百貨店：飲食料品": "百貨店|飲食料品",
       "百貨店：食堂・喫茶": "百貨店|食堂・喫茶", "コンビニ：サービス売上高": "コンビニ|サービス売上高"}

# 1) 2019年＝100
rows = []
for k, col in SER.items():
    ix = chain_annual(ya[col], 2019)
    m = vs_2019(ym[col])
    rows.append({"系列": k, **{str(t): ix[t] for t in range(2020, 2026)}, "2026年1-8月": m["2026-01":"2026-08"].mean(),
                 "区分": "業態" if "|" in col and not col.startswith("業種別") and "：" not in k else ("業種" if col.startswith("業種別") else "内訳")})
vs = pd.DataFrame(rows)
vs.round(1).to_csv(RES / "w2_vs2019.csv", index=False, encoding="utf-8")
print(vs.round(1).to_string(index=False))

# 2) 季節調整とコロナ前の傾向
TR = ["ドラッグストア", "スーパー", "コンビニ", "百貨店", "家電大型専門店", "ホームセンター"]
trend_rows, sa_store = [], {}
for k in TR:
    col = SER[k]
    s = backcast_monthly(vm[col], ym[col]).loc["2014-01":"2026-08"].dropna()
    lg = np.log(s.values)
    stl = STL(pd.Series(lg, index=s.index.to_timestamp()), period=12, robust=True).fit()
    sa = pd.Series(np.exp(lg - stl.seasonal.values), index=s.index)
    sa_store[k] = sa
    t = np.array([(p.year - 2014) + (p.month - 1) / 12 for p in sa.index])
    pre = (sa.index <= pd.Period("2019-12", "M"))
    X = sm.add_constant(t[pre]); fit = sm.OLS(np.log(sa.values[pre]), X).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    proj = np.exp(fit.params[0] + fit.params[1] * t)
    post = (sa.index >= pd.Period("2022-01", "M"))
    fit2 = sm.OLS(np.log(sa.values[post]), sm.add_constant(t[post])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    gap25 = (sa.loc["2025-01":"2025-12"].values / proj[(sa.index >= pd.Period("2025-01", "M")) & (sa.index <= pd.Period("2025-12", "M"))]).mean() * 100 - 100
    gap_last = sa.values[-1] / proj[-1] * 100 - 100
    trend_rows.append({"業態": k, "コロナ前の年率%": (np.exp(fit.params[1]) - 1) * 100, "同SE": fit.bse[1] * 100,
                       "2022年以降の年率%": (np.exp(fit2.params[1]) - 1) * 100, "同SE ": fit2.bse[1] * 100,
                       "2025年_傾向との差%": gap25, "2026年8月_傾向との差%": gap_last})
    sa_store[k + "_proj"] = pd.Series(proj, index=sa.index)
tr = pd.DataFrame(trend_rows)
tr.round(2).to_csv(RES / "w2_trend_gap.csv", index=False, encoding="utf-8")
print(tr.round(2).to_string(index=False))
pd.DataFrame(sa_store).round(0).to_csv(RES / "w2_seasonally_adjusted.csv", encoding="utf-8")

# 図1：2025年の2019年比
sel = ["ドラッグストア", "医薬品・化粧品小売業", "スーパー", "飲食料品小売業", "コンビニ", "小売業計", "家電大型専門店", "無店舗小売業",
       "ホームセンター", "自動車小売業", "百貨店", "各種商品小売業", "織物・衣服・身の回り品小売業"]
d = vs.set_index("系列").loc[sel, "2025"].sort_values(ascending=False)
sel = list(d.index)
fig, ax = plt.subplots(figsize=(8, 5.4))
yy = np.arange(len(sel))[::-1]
cols = [ORANGE if x >= 110 else (BLUE if x >= 100 else RED) for x in d.values]
ax.barh(yy, d.values - 100, color=cols, height=0.65)
for i, (nm, x) in zip(yy, d.items()):
    ax.text(x - 100 + (0.6 if x >= 100 else -0.6), i, f"{x:.1f}", va="center", ha="left" if x >= 100 else "right", fontsize=9)
ax.axvline(0, color=INK, lw=0.8)
ax.set_xlim(-20, 42)
ax.set_yticks(yy); ax.set_yticklabels([s + ("（業種）" if s.endswith("業") or s == "小売業計" else "（業態）") for s in sel], fontsize=9)
ax.set_xlabel("2019年からの増減（%、名目）")
ax.set_title("2025年の販売額（2019年＝100）", loc="left")
note(ax, "業態は企業単位、業種は事業所単位の集計。公表の前年比をつないで計算。出典：経済産業省「商業動態統計」（e-Stat）を加工して作成", -0.12)
fig.savefig(FIG / "w2_vs2019.png"); plt.close(fig)

# 図2：百貨店の商品別（月次、2019年同月＝100、3か月移動平均）
DC = {"百貨店：身の回り品": ORANGE, "百貨店：衣料品": BLUE, "百貨店：飲食料品": GREEN, "百貨店：食堂・喫茶": PURPLE}
fig, ax = plt.subplots(figsize=(8, 4.6))
for k, c in DC.items():
    m = vs_2019(ym[SER[k]]).rolling(3, center=True).mean()
    x = m.index.to_timestamp()
    ax.plot(x, m.values, color=c, lw=1.8)
    ax.annotate(k.split("：")[1] + f" {m.dropna().iloc[-1]:.0f}", (x[-1], m.dropna().iloc[-1]), color=c, fontsize=10,
                xytext=(6, 0), textcoords="offset points", va="center")
ax.axhline(100, color=GRAY, lw=0.8)
ax.set_title("百貨店の商品別の販売額（2019年同月＝100、3か月移動平均）", loc="left")
note(ax, "9・10月は2019年10月の消費税率の引上げ前後の動きの影響を受ける。出典：経済産業省「商業動態統計」（e-Stat）を加工して作成", -0.1)
fig.savefig(FIG / "w2_department.png"); plt.close(fig)

# 図3：季節調整値とコロナ前の傾向
fig, axes = plt.subplots(2, 3, figsize=(10, 5.8), sharex=True)
for ax, k in zip(axes.ravel(), TR):
    sa, pr = sa_store[k], sa_store[k + "_proj"]
    x = sa.index.to_timestamp()
    ax.plot(x, sa.values / 1e5, color=INK, lw=1.4)
    ax.plot(x, pr.values / 1e5, color=ORANGE, lw=1.2, ls="--")
    ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-31"), color=LIGHT, alpha=0.4, lw=0)
    g = tr.set_index("業態").loc[k, "2025年_傾向との差%"]
    ax.set_title(f"{k}（2025年 傾向比 {g:+.1f}%）", fontsize=10.5, loc="left")
    ax.tick_params(labelsize=8)
axes[0, 0].set_ylabel("千億円／月"); axes[1, 0].set_ylabel("千億円／月")
fig.suptitle("季節調整した月の販売額（黒）と、2014〜2019年の傾向を延ばした線（橙の破線）", x=0.01, ha="left", fontsize=12)
fig.text(0.01, -0.01, "水色は2020年3月〜2021年。名目。出典：経済産業省「商業動態統計」（e-Stat）を加工して作成", fontsize=8, color=GRAY)
fig.tight_layout()
fig.savefig(FIG / "w2_trend.png"); plt.close(fig)
