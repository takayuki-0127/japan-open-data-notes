"""471 年初からの累計で見た前年比は、月ごとの変化に何か月遅れて気づくのか（seed 471）"""
import json, numpy as np, pandas as pd, duckdb, matplotlib.pyplot as plt
from common import *
SEED = 471; SRC = "架空の月次売上（seed 471）"
Y0, NY = 2021, 7; T = NY * 12; G = 0.02; CY = 2025          # 2021〜2027年。変化は2025年のどこかの月
SHAPE = np.array([-.6, -1., .1, .0, .1, -.1, .3, .1, -.2, .1, .2, 1.])  # 季節の形（12月が山、2月が谷）
SHAPE = SHAPE - SHAPE.mean()

def series(k=None, s=-0.10, amp=0.15, sigma=0.0, rng=None, n=1):
    """k: 変化の月（1〜12、2025年）。s: 水準の変化。amp: 季節の強さ。n 本を返す (n,T)"""
    t = np.arange(T); lvl = 100 * (1 + G) ** (t / 12)
    if k is not None: lvl = lvl * np.where(t >= (CY - Y0) * 12 + k - 1, 1 + s, 1.0)
    x = lvl * (1 + amp * SHAPE[t % 12])
    x = np.tile(x, (n, 1))
    if sigma > 0: x = x * np.exp(rng.normal(0, sigma, (n, T)) - sigma ** 2 / 2)
    return x

def views(x):
    """x:(n,T) → 単月・累計・直近12か月の前年比 (n,T)。最初の年は NaN（直近12か月は最初の2年のうち23か月）"""
    n = x.shape[0]; xr = x.reshape(n, NY, 12); ytd = xr.cumsum(axis=2).reshape(n, T)
    cs = np.concatenate([np.zeros((n, 1)), x.cumsum(axis=1)], axis=1); r12 = np.full((n, T), np.nan)
    r12[:, 11:] = cs[:, 12:] - cs[:, :-12]
    def yoy(a):
        o = np.full((n, T), np.nan); o[:, 12:] = a[:, 12:] / a[:, :-12] - 1; return o
    return yoy(x), yoy(ytd), yoy(r12)

NAMES = ["単月の前年同月比", "年初からの累計の前年比", "直近12か月の合計の前年比"]; KEY = ["month", "ytd", "r12"]; COL = [ORANGE, BLUE, GREEN]
YM = pd.period_range(f"{Y0}-01", periods=T, freq="M")
res = {}

# ---- SQL（DuckDB）と一致するか ----
x0 = series(k=9)[0]; con = duckdb.connect(); con.execute("SET threads=1")
con.register("monthly", pd.DataFrame({"ym": YM.to_timestamp(), "sales": x0}))
sql = open(SQL / "01_ytd_tsql.sql", encoding="utf-8").read()
q = con.execute(sql).df(); v = views(x0[None, :])
for c, a in zip(["yoy_month", "yoy_ytd", "yoy_r12"], v):
    b = a[0][12:]; m = ~np.isnan(b); assert np.allclose(q[c].values[m], b[m], atol=1e-12), c
res["sql_check"] = "DuckDB の結果が numpy の計算と一致（84か月のうち前年のある72か月）"

# ---- 1. 揺れなし：変化の月ごとに、半分まで追いつくのに要る月数・年末と翌1月の差・戻りの遅れ ----
S = -0.10; PRE = G; POST = (1 + G) * (1 + S) - 1; MID = (PRE + POST) / 2
rows = []
for amp in [0.0, 0.15, 0.40]:
    for k in range(1, 13):
        tc = (CY - Y0) * 12 + k - 1; vv = views(series(k=k, s=S, amp=amp))
        r = {"amp": amp, "change_month": k}
        for key, a in zip(KEY, vv):
            a = a[0]; hit = np.where(a[tc:] <= MID)[0]; r[f"lag_half_{key}"] = int(hit[0]) if len(hit) else np.nan
            back = np.where(a[tc + 12:] >= MID)[0]            # 単月が戻る月（変化の12か月後）から数えて、半分まで戻る月数
            r[f"lag_back_{key}"] = int(back[0]) if len(back) else np.nan
        ytd = vv[1][0]; dec, jan = (CY - Y0) * 12 + 11, (CY - Y0 + 1) * 12
        r["ytd_dec"] = ytd[dec]; r["ytd_next_jan"] = ytd[jan]; r["jump_pt"] = (ytd[jan] - ytd[dec]) * 100
        r["share_shown_dec"] = (ytd[dec] - PRE) / (POST - PRE)
        r["ytd_dec_next_year"] = ytd[jan + 11]; r["month_dec_next_year"] = vv[0][0][jan + 11]
        rows.append(r)
lag = pd.DataFrame(rows); lag.to_csv(RES / "lag_by_change_month.csv", index=False)
b = lag[lag.amp == 0.15]
res["lag_half_ytd_by_month"] = b.set_index("change_month").lag_half_ytd.astype(int).to_dict()
res["lag_half_r12"] = sorted(b.lag_half_r12.unique().astype(int).tolist()); res["lag_half_month"] = sorted(b.lag_half_month.unique().astype(int).tolist())
res["lag_half_ytd_mean"] = float(b.lag_half_ytd.mean()); res["lag_half_ytd_max"] = int(b.lag_half_ytd.max())
res["share_shown_dec"] = {int(k): round(float(v), 3) for k, v in b.set_index("change_month").share_shown_dec.items()}
res["jump_pt"] = {int(k): round(float(v), 2) for k, v in b.set_index("change_month").jump_pt.items()}
res["lag_back_ytd"] = {int(k): (None if np.isnan(v) else int(v)) for k, v in b.set_index("change_month").lag_back_ytd.items()}
res["lag_back_r12"] = sorted(set(int(v) for v in b.lag_back_r12)); res["lag_back_month"] = sorted(set(int(v) for v in b.lag_back_month)); res["ytd_dec_next_year_k10"] = float(b[b.change_month == 10].ytd_dec_next_year.iloc[0])
res["by_amp_lag_half_ytd_mean"] = {str(a): float(g.lag_half_ytd.mean()) for a, g in lag.groupby("amp")}
res["by_amp_lag_half_ytd_k7"] = {str(a): int(g[g.change_month == 7].lag_half_ytd.iloc[0]) for a, g in lag.groupby("amp")}

# ---- 2. 最新の月が累計に占める重み（年度の後半ほど動かない） ----
w = []
for amp in [0.0, 0.15, 0.40]:
    x = series(amp=amp)[0][-12:]; cw = x / x.cumsum()
    for m in range(12): w.append({"amp": amp, "month": m + 1, "weight_latest_month": cw[m], "ytd_move_if_month_moves_10pct": cw[m] * 10})
wt = pd.DataFrame(w); wt.to_csv(RES / "latest_month_weight.csv", index=False)
res["weight"] = {int(m): round(float(v), 4) for m, v in wt[wt.amp == 0.15].set_index("month").weight_latest_month.items()}

# ---- 3. 揺れあり：気づくまでの月数と空振り ----
rng = np.random.default_rng(SEED); NS = 2000; SIG = 0.03
x = series(sigma=SIG, rng=rng, n=NS); vv = views(x)
sd = {key: np.nanstd(a[:, 24:].reshape(NS, NY - 2, 12), axis=(0, 1)) for key, a in zip(KEY, vv)}   # 月ごとの揺れ（変化なし）
pd.DataFrame({"month": range(1, 13), **{f"sd_{k}_pt": v * 100 for k, v in sd.items()}}).to_csv(RES / "noise_sd_by_month.csv", index=False)
res["noise_sd_pt"] = {k: [round(float(z) * 100, 2) for z in v] for k, v in sd.items()}
THR = PRE - 0.05                                                      # 「前年比が ふだん−5ポイント を下回ったら気づく」
fa = {key: float((a[:, 24:] <= THR).mean() * 12) for key, a in zip(KEY, vv)}     # 変化なしで鳴る回数（年あたり）
fa_m = {key: (a[:, 24:].reshape(NS, NY - 2, 12) <= THR).mean(axis=(0, 1)) for key, a in zip(KEY, vv)}
rows = []
for k in range(1, 13):
    tc = (CY - Y0) * 12 + k - 1; a3 = views(series(k=k, s=S, sigma=SIG, rng=rng, n=NS)); r = {"change_month": k}
    for key, a in zip(KEY, a3):
        hit = (a[:, tc:] <= THR); first = np.where(hit.any(axis=1), hit.argmax(axis=1), np.nan)
        r[f"median_{key}"] = float(np.nanmedian(first)); r[f"p90_{key}"] = float(np.nanpercentile(first, 90)); r[f"within2_{key}"] = float((first <= 2).mean())
    rows.append(r)
det = pd.DataFrame(rows); det.to_csv(RES / "detect_with_noise.csv", index=False)
res["detect"] = {key: {"median_mean_over_months": float(det[f"median_{key}"].mean()), "p90_mean": float(det[f"p90_{key}"].mean()),
                       "false_alarm_per_year": fa[key]} for key in KEY}
res["false_alarm_by_month_ytd"] = [round(float(z), 4) for z in fa_m["ytd"]]
res["detect_ytd_median_by_month"] = det.set_index("change_month").median_ytd.to_dict()

# ---- 4. 変化の大きさ・年度の始まりを変える ----
rows = []
for s in [-0.05, -0.10, -0.20, 0.10]:
    pre, post = G, (1 + G) * (1 + s) - 1; mid = (pre + post) / 2
    for k in range(1, 13):
        tc = (CY - Y0) * 12 + k - 1; a = views(series(k=k, s=s))[1][0]
        hit = np.where((a[tc:] <= mid) if s < 0 else (a[tc:] >= mid))[0]; rows.append({"shift": s, "change_month": k, "lag_half_ytd": int(hit[0])})
sw = pd.DataFrame(rows); sw.to_csv(RES / "sweep_shift_size.csv", index=False)
res["lag_same_for_all_sizes"] = bool(sw.groupby("change_month").lag_half_ytd.nunique().max() == 1)

# ---- 5. 公的な月次統計（商業動態統計の百貨店、暦年の累計） ----
d = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"]); pub = {}
for gy in ["百貨店", "コンビニ"]:
    g = d[d.gyotai == gy].sort_values("ym").set_index("ym").sales.astype(float)
    df = pd.DataFrame({"sales": g}); df["yr"] = df.index.year; df["mon"] = df.index.month
    df["ytd"] = df.groupby("yr").sales.cumsum(); df["r12"] = df.sales.rolling(12).sum()
    for c in ["sales", "ytd", "r12"]: df["yoy_" + c] = df[c] / df[c].shift(12) - 1
    df = df.rename(columns={"yoy_sales": "yoy_month"}); df["gyotai"] = gy; pub[gy] = df
pd.concat(pub.values()).reset_index().to_csv(RES / "public_three_views.csv", index=False)
dp = pub["百貨店"]; f = lambda c, thr, a, b: dp.loc[a:b][dp.loc[a:b][c] <= thr].index.min()
res["dept"] = {"first_below_-10_month": str(f("yoy_month", -.10, "2020-01", "2021-12"))[:7], "first_below_-10_ytd": str(f("yoy_ytd", -.10, "2020-01", "2021-12"))[:7],
               "first_below_-10_r12": str(f("yoy_r12", -.10, "2020-01", "2021-12"))[:7],
               "2020-12": {c: float(dp.loc["2020-12-01", c]) for c in ["yoy_month", "yoy_ytd", "yoy_r12"]},
               "2021-01": {c: float(dp.loc["2021-01-01", c]) for c in ["yoy_month", "yoy_ytd", "yoy_r12"]},
               "2021-04": {c: float(dp.loc["2021-04-01", c]) for c in ["yoy_month", "yoy_ytd", "yoy_r12"]},
               "2020-03": {c: float(dp.loc["2020-03-01", c]) for c in ["yoy_month", "yoy_ytd", "yoy_r12"]},
               "2020-04": {c: float(dp.loc["2020-04-01", c]) for c in ["yoy_month", "yoy_ytd", "yoy_r12"]},
               "first_positive_month_2021": str(dp.loc["2021-01":"2021-12"][dp.loc["2021-01":"2021-12"].yoy_month > 0].index.min())[:7],
               "first_positive_r12_after": str(dp.loc["2021-01":"2023-12"][dp.loc["2021-01":"2023-12"].yoy_r12 > 0].index.min())[:7],
               "first_positive_ytd_2021": str(dp.loc["2021-01":"2021-12"][dp.loc["2021-01":"2021-12"].yoy_ytd > 0].index.min())[:7]}
json.dump(res, open(RES / "a471_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"ym": YM.astype(str), "sales_change_in_sep": series(k=9)[0].round(3), "sales_change_in_mar": series(k=3)[0].round(3)}).to_csv(DATA / "fictional_monthly_sales.csv", index=False)

# ---- 図 ----
fig, ax = plt.subplots(1, 2, figsize=(12, 4.3), sharey=True)
for a, k in zip(ax, [3, 9]):
    vv = views(series(k=k)); sl = slice(36, 72); xs = np.arange(36)
    for nm, v, c in zip(NAMES, vv, COL): a.plot(xs, v[0][sl] * 100, color=c, lw=2, label=nm)
    a.axhline(MID * 100, color=GRAY, ls=":", lw=1); a.axvline(12 + k - 1, color=GRAY, lw=1); a.axvline(24, color=LIGHT, lw=1)
    a.set_xticks(range(0, 36, 3)); a.set_xticklabels([f"{2024 + i // 12}\n{i % 12 + 1}月" if i % 12 == 0 else f"{i % 12 + 1}月" for i in range(0, 36, 3)], fontsize=8)
    a.set_title(f"2025年{k}月から、売上の水準が10%下がった場合"); a.text(12 + k - 0.7, 2.6, "変化", fontsize=9, color=GRAY); a.set_ylim(-10, 3.6)
ax[0].set_ylabel("前年比（%）"); ax[0].legend(fontsize=8.5, loc="lower left", frameon=False)
save(fig, "a471_example.png", f"出典：{SRC}。点線は、変化の前（+2%）と後（−8.2%）の真ん中。暦年（1〜12月）の累計")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.3)); ks = np.arange(1, 13); wd = 0.27
for i, (key, nm, c) in enumerate(zip(KEY, NAMES, COL)): ax[0].bar(ks + (i - 1) * wd, b[f"lag_half_{key}"], wd, color=c, label=nm)
for k_, v_ in zip(ks, b.lag_half_ytd): ax[0].text(k_, v_ + .12, str(int(v_)), ha="center", fontsize=8, color=BLUE)
ax[0].set_xticks(ks); ax[0].set_xticklabels([f"{k}月" for k in ks], fontsize=8.5); ax[0].set_xlabel("水準が変わった月"); ax[0].set_ylabel("真ん中まで追いつくのに要った月数（0＝その月）")
ax[0].set_title("変化の半分まで追いつくまでの月数（揺れなし）"); ax[0].legend(fontsize=8.5, frameon=False, loc="upper left"); ax[0].set_ylim(0, 8.6)
ax[1].bar(ks - .2, b.share_shown_dec * 100, .4, color=BLUE, label="12月の累計に出た割合（変化のうち）"); ax[1].bar(ks + .2, np.where(ks == 1, np.nan, -b.jump_pt.values), .4, color=ORANGE, label="12月→翌1月に累計の前年比が動いた幅（ポイント）")
ax[1].set_xticks(ks); ax[1].set_xticklabels([f"{k}月" for k in ks], fontsize=8.5); ax[1].set_xlabel("水準が変わった月"); ax[1].set_title("年末の累計に出た割合と、年が替わった月の飛び")
ax[1].set_ylabel("%（青）／ポイント（オレンジ）"); ax[1].legend(fontsize=8.5, frameon=False, loc="upper center")
save(fig, "a471_lag_by_month.png", f"出典：{SRC}。水準が10%下がる場合、季節の強さ0.15。変化の大きさを−5%・−20%・+10%にしても、左の月数は同じ。1月に変わった場合は年末までに全部出るので、右のオレンジは書いていない")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
for key, nm, c in zip(KEY, NAMES, COL): ax[0].plot(ks, sd[key] * 100, marker="o", ms=4, color=c, label=nm)
ax[0].set_xticks(ks); ax[0].set_xticklabels([f"{k}月" for k in ks], fontsize=8.5); ax[0].set_ylabel("前年比の揺れ（標準偏差、ポイント）"); ax[0].set_ylim(0, 5)
ax[0].set_title("変化がないときの揺れ（月の売上の揺れ3%）"); ax[0].legend(fontsize=8.5, frameon=False)
sl = dp.loc["2019-07":"2021-12"]
for c_, nm, c in zip(["yoy_month", "yoy_ytd", "yoy_r12"], NAMES, COL): ax[1].plot(range(len(sl)), sl[c_] * 100, color=c, lw=2, label=nm)
ax[1].axhline(0, color=GRAY, lw=.8); ix = [i for i, t in enumerate(sl.index) if t.month in (1, 4, 7, 10)]
ax[1].set_xticks(ix); ax[1].set_xticklabels([f"{sl.index[i].year}\n{sl.index[i].month}月" if sl.index[i].month == 1 else f"{sl.index[i].month}月" for i in ix], fontsize=8)
ax[1].set_title("百貨店の販売額（商業動態統計、2019年7月〜2021年12月）"); ax[1].set_ylabel("前年比（%）")
save(fig, "a471_noise_and_public.png", f"出典：左は{SRC}の2,000本。右は経済産業省「商業動態統計」をもとに作成者が加工して作成。暦年の累計。線の色は左と同じ")
print(json.dumps(res, ensure_ascii=False)[:3500])
