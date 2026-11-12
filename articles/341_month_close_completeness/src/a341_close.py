"""341 月次の数字は、締めてから何日たてば「確定」と言えるのか（架空の取引・seed 341）"""
import numpy as np, pandas as pd, duckdb, json
import matplotlib.pyplot as plt
from common import *
rng = np.random.default_rng(341)
# ---- 架空の取引：36か月。区分ごとに「起きた日」から「計上される日」までの遅れ（営業日）が違う
CATS = {  # 件数/月, 金額の対数平均, 対数σ, 遅れ：すぐ入る割合, 残りの遅れの対数平均, 対数σ
    "店頭の売上":   (9000, 8.6, 0.8, 0.97, 0.3, 0.5),
    "請求書の売上": (1200, 11.3, 1.0, 0.35, 1.3, 0.7),
    "返品・値引き": (500, 9.5, 0.9, 0.20, 1.8, 0.8),
    "経費精算":     (800, 9.2, 0.9, 0.10, 2.0, 0.7),
}
SIGN = {"店頭の売上": 1, "請求書の売上": 1, "返品・値引き": -1, "経費精算": -1}
months = pd.period_range("2023-01", "2025-12", freq="M")
rows = []
for m in months:
    days = pd.bdate_range(m.start_time, m.end_time)
    w = np.ones(len(days)); w[-3:] = 2.5            # 月末の3営業日に取引が集まる
    for c, (n, mu, sg, p0, dmu, dsg) in CATS.items():
        k = rng.poisson(n)
        d = rng.choice(len(days), k, p=w / w.sum())
        amt = np.round(rng.lognormal(mu, sg, k)) * SIGN[c]
        quick = rng.random(k) < p0
        delay = np.where(quick, rng.integers(0, 2, k), np.ceil(rng.lognormal(dmu, dsg, k))).astype(int)
        if c == "請求書の売上" and m.month in (3, 9):   # 半期末は請求書が遅れやすい
            delay = np.where(quick, delay, np.ceil(delay * 1.5)).astype(int)
        occ = days[d].values.astype("datetime64[D]")
        post = np.busday_offset(occ, delay, roll="forward")
        rows.append(pd.DataFrame({"ym": str(m), "cat": c, "occ": occ, "post": post, "amt": amt}))
tx = pd.concat(rows, ignore_index=True)
# 大口の遅れ：36か月のうち4か月で、金額の大きい請求書1枚が締め後6〜9営業日に入る
for ym in ["2023-06", "2024-02", "2024-11", "2025-08"]:
    me = np.datetime64(pd.Period(ym).end_time.date())
    last = np.busday_offset(me, 0, roll="backward")
    tx.loc[len(tx)] = [ym, "請求書の売上", last, np.busday_offset(last, int(rng.integers(6, 10))), 6_000_000.0]
tx["occ"] = pd.to_datetime(tx.occ); tx["post"] = pd.to_datetime(tx.post)
# 締め後の営業日数（0＝月の最後の営業日までに計上、1＝翌営業日…）
mend = tx.ym.map(lambda s: np.busday_offset(np.datetime64(pd.Period(s).end_time.date()), 0, roll="backward"))
tx["lag"] = np.maximum(np.busday_count(mend.values.astype("datetime64[D]"), tx.post.values.astype("datetime64[D]")), 0)
con = duckdb.connect()
con.register("tx", tx)
# ---- SQL：締め後 k 営業日の時点で入っている金額（T-SQL でも同じ形。sql/ に置いた版は未検証）
curve = con.execute("""
WITH k AS (SELECT range AS k FROM range(0, 61)),
     f AS (SELECT ym, SUM(amt) AS final FROM tx GROUP BY ym)
SELECT t.ym, k.k, SUM(CASE WHEN t.lag <= k.k THEN t.amt ELSE 0 END) AS cum, MAX(f.final) AS final
FROM tx t CROSS JOIN k JOIN f USING (ym) GROUP BY t.ym, k.k ORDER BY 1, 2""").df()
curve["ratio"] = curve.cum / curve.final
piv = curve.pivot(index="ym", columns="k", values="ratio")
chk = tx.assign(v=lambda d: d.amt).groupby("ym").apply(lambda d: d.loc[d.lag <= 3, "amt"].sum() / d.amt.sum())
assert np.allclose(chk.values, piv[3].values)            # pandas で別に計算して一致
KS = [0, 1, 3, 5, 10, 15, 20]
summ = pd.DataFrame({"k": KS, "median": [piv[k].median() for k in KS], "min": [piv[k].min() for k in KS],
                     "max": [piv[k].max() for k in KS],
                     "within1pct": [int(((piv[k] - 1).abs() <= 0.01).sum()) for k in KS],
                     "within01pct": [int(((piv[k] - 1).abs() <= 0.001).sum()) for k in KS]})
summ.to_csv(RES / "completeness_by_day.csv", index=False)
# 区分ごとの入り方（絶対額でみた割合）
catc = con.execute("""SELECT cat, k.k, SUM(CASE WHEN lag<=k.k THEN ABS(amt) ELSE 0 END)/SUM(ABS(amt)) AS ratio
FROM tx CROSS JOIN (SELECT unnest([0,1,3,5,10]) AS k) k GROUP BY 1,2 ORDER BY 1,2""").df()
catc.pivot(index="cat", columns="k", values="ratio").round(4).to_csv(RES / "completeness_by_category.csv")
# ---- 見込みで補う：過去12か月の「k日目の割合」で割り戻す。区分をまとめて割る形と、区分ごとに割って足す形
cc = con.execute("""SELECT ym, cat, k.k, SUM(CASE WHEN lag<=k.k THEN amt ELSE 0 END) AS cum, SUM(amt) AS final
FROM tx CROSS JOIN (SELECT unnest([0,1,3,5,10]) AS k) k GROUP BY 1,2,3""").df()
yms = [str(m) for m in months]; est = []
for i in range(12, len(yms)):
    past, cur = yms[i - 12:i], yms[i]
    for k in [0, 1, 3, 5, 10]:
        a = curve[(curve.ym == cur) & (curve.k == k)].iloc[0]
        r_all = curve[curve.ym.isin(past) & (curve.k == k)].pipe(lambda d: d.cum.sum() / d.final.sum())
        e_cat = 0.0
        for c in CATS:
            p = cc[cc.ym.isin(past) & (cc.k == k) & (cc.cat == c)]
            x = cc[(cc.ym == cur) & (cc.k == k) & (cc.cat == c)].cum.iloc[0]
            e_cat += x / (p.cum.sum() / p.final.sum())
        est.append({"ym": cur, "k": k, "final": a.final, "raw": a.cum, "est_all": a.cum / r_all, "est_cat": e_cat})
est = pd.DataFrame(est)
for c in ["raw", "est_all", "est_cat"]:
    est[c + "_err"] = est[c] / est.final - 1
est.to_csv(RES / "estimate_errors.csv", index=False)
big = {"2024-02", "2024-11", "2025-08"}
g = est.assign(big=est.ym.isin(big)).groupby("k")
es = pd.DataFrame({"raw_mae": g.raw_err.apply(lambda s: s.abs().mean()), "est_all_mae": g.est_all_err.apply(lambda s: s.abs().mean()),
                   "est_cat_mae": g.est_cat_err.apply(lambda s: s.abs().mean()),
                   "raw_max": g.raw_err.apply(lambda s: s.abs().max()), "est_all_max": g.est_all_err.apply(lambda s: s.abs().max()),
                   "est_cat_max": g.est_cat_err.apply(lambda s: s.abs().max())})
es.to_csv(RES / "estimate_summary.csv")
nb = est[~est.ym.isin(big)].groupby("k").est_cat_err.apply(lambda s: s.abs().mean())
bb = est[est.ym.isin(big)].groupby("k").est_cat_err.apply(lambda s: s.abs().mean())
main = {"n_tx": int(len(tx)), "months": len(yms), "final_mean_man": float(curve.groupby("ym").final.max().mean() / 1e4),
        "completeness": {int(r["k"]): {"median": round(r["median"], 4), "min": round(r["min"], 4), "max": round(r["max"], 4),
                                    "within1pct": int(r["within1pct"]), "within01pct": int(r["within01pct"])} for _, r in summ.iterrows()},
        "estimate_mae": {int(k): {c: round(float(v), 5) for c, v in r.items()} for k, r in es.iterrows()},
        "est_cat_mae_normal_months": {int(k): round(float(v), 5) for k, v in nb.items()},
        "est_cat_mae_big_invoice_months": {int(k): round(float(v), 5) for k, v in bb.items()},
        "first_day_all_within_1pct": int(next((k for k in range(61) if ((piv[k] - 1).abs() <= 0.01).all()), -1)),
        "first_day_all_within_01pct": int(next((k for k in range(61) if ((piv[k] - 1).abs() <= 0.001).all()), -1))}
json.dump(main, open(RES / "a341_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(catc.pivot(index="cat", columns="k", values="ratio").round(3))
SRC = "架空の取引（乱数で作成、seed 341）。営業日は土日だけを除いて数えた"
# 図1：締め後の営業日数と、最終値に対する割合
fig, ax = plt.subplots(figsize=(8, 4.6))
for ym in piv.index: ax.plot(piv.columns[:21], piv.loc[ym].values[:21] * 100, color=LIGHT, lw=0.8)
ax.plot(piv.columns[:21], piv.median().values[:21] * 100, color=BLUE, lw=2.5, label="36か月の中央値")
ax.axhline(100, color=GRAY, lw=0.8); ax.axhline(99, color=ORANGE, lw=0.8, ls="--"); ax.text(20.2, 98.9, "99%", color=ORANGE, va="top", fontsize=9)
ax.set_xlabel("締めてからの営業日数（0＝月の最後の営業日）"); ax.set_ylabel("最終値に対する割合（%）"); ax.set_xticks(range(0, 21, 2))
ax.set_title("月次の利益は、締め後の何営業日目で最終値にそろうか（細い線は月ごと）"); ax.legend(frameon=False, loc="lower right")
save(fig, "a341_curve.png", SRC)
# 図2：そのまま出す・見込みで補う の誤差
fig, ax = plt.subplots(figsize=(8, 4.4)); x = np.arange(5); w = 0.27
for j, (c, lab, col) in enumerate([("raw_mae", "入っている分だけで出す", GRAY), ("est_all_mae", "全体の割合で割り戻す", LIGHT), ("est_cat_mae", "区分ごとに割り戻して足す", BLUE)]):
    b = ax.bar(x + (j - 1) * w, es[c].values * 100, w, color=col, label=lab)
    for xi, v in zip(x + (j - 1) * w, es[c].values * 100): ax.text(xi, v + 0.15, f"{v:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([f"{k}営業日目" for k in es.index]); ax.set_ylabel("最終値とのずれ（24か月の平均、%）")
ax.set_title("早く出すとき、見込みで補うとずれはどれだけ小さくなるか"); ax.legend(frameon=False)
save(fig, "a341_estimate.png", SRC)
# 図3：区分ごとの入り方
cp = catc.pivot(index="cat", columns="k", values="ratio").loc[list(CATS)]
fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(len(cp)); w = 0.16
cols = [GRAY, LIGHT, BLUE, GREEN, ORANGE]
for j, k in enumerate(cp.columns):
    ax.bar(x + (j - 2) * w, cp[k].values * 100, w, color=cols[j], label=f"{k}営業日目")
ax.set_xticks(x); ax.set_xticklabels(cp.index); ax.set_ylabel("その区分の金額のうち、入っている割合（%）"); ax.set_ylim(0, 105)
ax.set_title("遅れて入るのは、請求書・返品・経費精算"); ax.legend(frameon=False, ncol=5, fontsize=8, loc="lower center")
save(fig, "a341_category.png", SRC)
