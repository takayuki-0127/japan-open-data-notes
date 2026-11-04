# -*- coding: utf-8 -*-
"""F184 新幹線の開業で、空の便はどれだけ減ったか（路線別の差の差）

入力: data/air_routes_annual.csv, data/air_routes_monthly.csv（01_取得 で作成）
出力: results/*.csv
"""
import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data")
R = os.path.join(ROOT, "results")
os.makedirs(R, exist_ok=True)
rng = np.random.default_rng(184)

ann = pd.read_csv(os.path.join(D, "air_routes_annual.csv"))
mon = pd.read_csv(os.path.join(D, "air_routes_monthly.csv"))
ann = ann[ann.pax > 0].copy()
ann["lf"] = ann.pax / ann.seats

# ---- 開業イベント（開業日・最初の「開業後の年」・対象路線・開業時の鉄道の最速所要時間のおおよその値） ----
EVENTS = [
    # name, open (YYYY-MM), t0, treated routes, {route: rail hours}
    ("東北・新青森", "2010-12", 2011, ["羽田―青森", "羽田―三沢"], {"羽田―青森": 3.3, "羽田―三沢": None}),
    ("九州・全線", "2011-03", 2011, ["鹿児島―福岡", "大阪―熊本", "大阪―鹿児島"],
     {"鹿児島―福岡": 1.3, "大阪―熊本": 3.0, "大阪―鹿児島": 3.75}),
    ("北陸・金沢", "2015-03", 2015, ["羽田―富山", "羽田―金沢(小松)"], {"羽田―富山": 2.15, "羽田―金沢(小松)": 2.45}),
    ("北海道・新函館北斗", "2016-03", 2016, ["羽田―函館"], {"羽田―函館": 4.0}),
    ("北陸・敦賀", "2024-03", 2024, ["羽田―金沢(小松)"], {"羽田―金沢(小松)": None}),
]
# 羽田―三沢: 八戸までは2002年に開業済みで、新青森延伸で所要時間はほぼ変わらない（比べるための路線）
# 敦賀延伸: 小松駅に新幹線が止まるようになった（金沢までは2015年に開業済み）

# 対照から外す：新幹線の開業区間の空港に関わる路線、能登（2024年の地震）
EXCL_AIRPORTS = ["青森", "三沢", "富山", "金沢(小松)", "能登", "函館"]
EXCL_ROUTES = ["鹿児島―福岡", "大阪―熊本", "大阪―鹿児島", "関西―鹿児島", "神戸―鹿児島",
               "名古屋(小牧)―熊本", "中部―熊本", "中部―鹿児島", "静岡―鹿児島"]
COVID = {2020, 2021, 2022}


def is_control(route):
    if route in EXCL_ROUTES:
        return False
    a, b = route.split("―")
    return not any(x in (a, b) for x in EXCL_AIRPORTS)


ann["ctrl"] = ann.route.map(is_control)
piv = ann.pivot_table(index="route", columns="year", values="pax")
piv_s = ann.pivot_table(index="route", columns="year", values="seats")


def window(t0, k):
    pre = [y for y in range(t0 - k, t0) if y not in COVID]
    post = [y for y in range(t0, t0 + k) if y not in COVID and y <= 2025]
    if t0 == 2024:  # 敦賀：コロナ期を除いた前の年（2017〜2019・2023）
        pre = [2017, 2018, 2019, 2023][-k - 1:] if k >= 3 else [2019, 2023]
        post = [2024, 2025]
    return pre, post


def controls_for(pre, post, min_pax=50_000, hub=None):
    yrs = pre + post
    c = piv.loc[[r for r in piv.index if is_control(r)], yrs]
    c = c.dropna()
    c = c[(c >= min_pax).all(axis=1)]
    if hub is not None:
        c = c[[hub in r.split("―") for r in c.index]]
    return list(c.index)


def did_one(series_tbl, route, ctrls, pre, post):
    lg = np.log(series_tbl)
    d_t = lg.loc[route, post].mean() - lg.loc[route, pre].mean()
    d_c = (lg.loc[ctrls, post].mean(axis=1) - lg.loc[ctrls, pre].mean(axis=1))
    return d_t - d_c.mean(), d_c


def perm_p(est, d_c):
    # 対照の各路線を「処置されたことにした」ときの差の差（その路線以外の対照と比べる）
    vals = []
    arr = d_c.values
    for i in range(len(arr)):
        vals.append(arr[i] - np.delete(arr, i).mean())
    vals = np.array(vals)
    return (np.sum(np.abs(vals) >= abs(est)) + 1) / (len(vals) + 1), vals


rows = []
for name, op, t0, treated, rail in EVENTS:
    pre, post = window(t0, 3)
    ctrls = controls_for(pre, post)
    for r in treated:
        if r not in piv.index or piv.loc[r, pre + post].isna().any():
            continue
        est, d_c = did_one(piv, r, ctrls, pre, post)
        p, _ = perm_p(est, d_c)
        est_s, _ = did_one(piv_s, r, ctrls, pre, post)
        rows.append(dict(event=name, open=op, route=r, pre=f"{pre[0]}-{pre[-1]}", post=f"{post[0]}-{post[-1]}",
                         n_ctrl=len(ctrls), did_log=est, did_pct=np.expm1(est) * 100, perm_p=p,
                         did_seats_pct=np.expm1(est_s) * 100, did_lf_pts=None,
                         pax_pre=piv.loc[r, pre].mean(), pax_post=piv.loc[r, post].mean(),
                         rail_h=rail.get(r)))
main = pd.DataFrame(rows)
# 搭乗率（旅客÷座席）の変化（ポイント）
for i, x in main.iterrows():
    name = x.event
    t0 = [e for e in EVENTS if e[0] == name][0][2]
    pre, post = window(t0, 3)
    ctrls = controls_for(pre, post)
    lf = (piv / piv_s)
    dt = lf.loc[x.route, post].mean() - lf.loc[x.route, pre].mean()
    dc = (lf.loc[ctrls, post].mean(axis=1) - lf.loc[ctrls, pre].mean(axis=1)).mean()
    main.loc[i, "did_lf_pts"] = (dt - dc) * 100
main.to_csv(os.path.join(R, "did_main.csv"), index=False, encoding="utf-8-sig")
print(main[["event", "route", "pre", "post", "n_ctrl", "did_pct", "perm_p", "did_seats_pct", "did_lf_pts", "rail_h"]].round(3).to_string())

# ---- 頑健性：対照・期間・指標 ----
rob = []
for name, op, t0, treated, rail in EVENTS:
    for r in treated:
        for k in (2, 3, 4):
            pre, post = window(t0, k)
            if r not in piv.index or piv.loc[r, pre + post].isna().any():
                continue
            specs = {
                "全路線（主）": controls_for(pre, post),
                "羽田発着だけ": controls_for(pre, post, hub="羽田"),
                "旅客20万人以上": controls_for(pre, post, min_pax=200_000),
            }
            # 前の期間の伸びが近い10路線
            base = controls_for(pre, post)
            lg = np.log(piv)
            if len(pre) >= 2:
                g_t = lg.loc[r, pre[-1]] - lg.loc[r, pre[0]]
                g_c = (lg.loc[base, pre[-1]] - lg.loc[base, pre[0]])
                specs["前の伸びが近い10路線"] = list((g_c - g_t).abs().sort_values().index[:10])
            for sname, ctrls in specs.items():
                if len(ctrls) < 5:
                    continue
                est, d_c = did_one(piv, r, ctrls, pre, post)
                p, _ = perm_p(est, d_c)
                rob.append(dict(event=name, route=r, k=k, control=sname, n_ctrl=len(ctrls),
                                did_pct=np.expm1(est) * 100, perm_p=p))
        # 開業の年を除く（年の途中で開業したため）
        pre, post = window(t0, 3)
        post2 = [y for y in post if y != t0]
        if post2 and r in piv.index and not piv.loc[r, pre + post2].isna().any():
            ctrls = controls_for(pre, post2)
            est, d_c = did_one(piv, r, ctrls, pre, post2)
            p, _ = perm_p(est, d_c)
            rob.append(dict(event=name, route=r, k=3, control="開業の年を除く", n_ctrl=len(ctrls),
                            did_pct=np.expm1(est) * 100, perm_p=p))
rob = pd.DataFrame(rob)
rob.to_csv(os.path.join(R, "did_robustness.csv"), index=False, encoding="utf-8-sig")
summ = rob.groupby(["event", "route"]).did_pct.agg(["min", "max", "count"]).round(1)
print(summ.to_string())

# ---- 同じ空港の別の路線と比べる（空港全体の需要の変化か、路線の置き換えか） ----
same = []
pairs = [("羽田―富山", ["富山―新千歳"], 2015), ("羽田―金沢(小松)", ["金沢(小松)―新千歳", "福岡―金沢(小松)"], 2015),
         ("羽田―函館", ["中部―函館", "大阪―函館", "新千歳―函館"], 2016), ("羽田―青森", ["新千歳―青森", "大阪―青森"], 2011)]
for tr, cs, t0 in pairs:
    pre, post = window(t0, 3)
    lg = np.log(piv)
    for c in cs:
        if c not in piv.index or piv.loc[c, pre + post].isna().any():
            same.append(dict(route=tr, compare=c, change_pct=None))
            continue
        dc = lg.loc[c, post].mean() - lg.loc[c, pre].mean()
        same.append(dict(route=tr, compare=c, change_pct=np.expm1(dc) * 100))
    dt = lg.loc[tr, post].mean() - lg.loc[tr, pre].mean()
    same.append(dict(route=tr, compare="（その路線自身）", change_pct=np.expm1(dt) * 100))
    allc = controls_for(pre, post)
    dca = (lg.loc[allc, post].mean(axis=1) - lg.loc[allc, pre].mean(axis=1)).mean()
    same.append(dict(route=tr, compare="（対照の平均）", change_pct=np.expm1(dca) * 100))
same = pd.DataFrame(same)
same.to_csv(os.path.join(R, "same_airport.csv"), index=False, encoding="utf-8-sig")
print(same.round(1).to_string())

# ---- 年ごとのイベントスタディ（処置路線ごと、対照平均との差、開業前年=0） ----
es = []
for name, op, t0, treated, rail in EVENTS[:4]:
    yrs = [y for y in range(t0 - 5, t0 + 5) if y not in COVID and 2006 <= y <= 2019]
    ctrls = controls_for(yrs, [])
    lg = np.log(piv)
    cm = lg.loc[ctrls, yrs].mean()
    for r in treated:
        if r not in piv.index:
            continue
        g = lg.loc[r, yrs] - cm
        g = g - g.get(t0 - 1)
        for y, v in g.items():
            es.append(dict(event=name, route=r, year=y, k=y - t0, gap_pct=np.expm1(v) * 100))
es = pd.DataFrame(es)
es.to_csv(os.path.join(R, "event_study.csv"), index=False, encoding="utf-8-sig")

# ---- まとめた効果：鉄道の所要時間が縮んだ7路線の平均（三沢・敦賀は除く） ----
CORE = [("東北・新青森", "羽田―青森"), ("九州・全線", "鹿児島―福岡"), ("九州・全線", "大阪―熊本"),
        ("九州・全線", "大阪―鹿児島"), ("北陸・金沢", "羽田―富山"), ("北陸・金沢", "羽田―金沢(小松)"),
        ("北海道・新函館北斗", "羽田―函館")]
core = main.set_index(["event", "route"]).loc[CORE].reset_index()
avg = core.did_log.mean()
# 並べ替え：各イベントの対照から同じ数の路線を無作為に選び「処置したことにした」平均
draws = []
ev_ctrl = {}
for name, op, t0, treated, rail in EVENTS:
    pre, post = window(t0, 3)
    ctrls = controls_for(pre, post)
    lg = np.log(piv)
    ev_ctrl[name] = (lg.loc[ctrls, post].mean(axis=1) - lg.loc[ctrls, pre].mean(axis=1))
for _ in range(10000):
    v = []
    for name, r in CORE:
        d = ev_ctrl[name]
        i = rng.integers(len(d))
        v.append(d.iloc[i] - d.drop(d.index[i]).mean())
    draws.append(np.mean(v))
draws = np.array(draws)
p_avg = (np.sum(np.abs(draws) >= abs(avg)) + 1) / (len(draws) + 1)
# 鉄道の所要時間との関係（順位相関と、その並べ替え p）
from scipy.stats import spearmanr
rho = spearmanr(core.rail_h, core.did_log).correlation
perm_r = [spearmanr(core.rail_h, rng.permutation(core.did_log.values)).correlation for _ in range(10000)]
p_rho = (np.sum(np.abs(perm_r) >= abs(rho)) + 1) / 10001
slope = np.polyfit(core.rail_h, core.did_log, 1)[0]
pd.DataFrame([dict(n_routes=len(core), avg_pct=np.expm1(avg) * 100, perm_p=p_avg,
                   placebo_lo=np.expm1(np.quantile(draws, 0.025)) * 100, placebo_hi=np.expm1(np.quantile(draws, 0.975)) * 100,
                   spearman_rail=rho, spearman_p=p_rho, slope_log_per_hour=slope)]).to_csv(
    os.path.join(R, "did_pooled.csv"), index=False, encoding="utf-8-sig")
print("pooled", np.expm1(avg) * 100, p_avg, "rho", rho, p_rho, "slope", slope)

# ---- 前の傾きを延ばして差し引く（開業前から差が開いていた分を除く） ----
tr_rows = []
for name, r in CORE:
    sub = es[(es.event == name) & (es.route == r)].copy()
    sub["lg"] = np.log(sub.gap_pct / 100 + 1)
    pre_ = sub[(sub.k < 0) & (sub.k >= -4)]
    post_ = sub[(sub.k >= 0) & (sub.k <= 2)]
    if len(pre_) < 3:
        tr_rows.append(dict(event=name, route=r, n_pre=len(pre_), did_trend_pct=None))
        continue
    b1, b0 = np.polyfit(pre_.k, pre_.lg, 1)
    adj = (post_.lg - (b0 + b1 * post_.k)).mean()
    tr_rows.append(dict(event=name, route=r, n_pre=len(pre_), pre_slope_pct_per_year=np.expm1(b1) * 100,
                        did_trend_pct=np.expm1(adj) * 100))
tr = pd.DataFrame(tr_rows)
tr.to_csv(os.path.join(R, "did_trend_adjusted.csv"), index=False, encoding="utf-8-sig")
print(tr.round(1).to_string())
pool = es[es.set_index(["event", "route"]).index.isin(CORE)].groupby("k").gap_pct.apply(
    lambda x: (np.exp(np.log(x / 100 + 1).mean()) - 1) * 100).reset_index()
pool.to_csv(os.path.join(R, "event_study_pooled.csv"), index=False, encoding="utf-8-sig")
print(pool.round(1).to_string())

# ---- 月次：開業前12か月と開業後12か月（同じ月どうし）、対照との差 ----
mon = mon[mon.pax > 0].copy()
mon["t"] = mon.year * 12 + mon.month - 1
mrows = []
for name, op, t0, treated, rail in EVENTS:
    y, mo = map(int, op.split("-"))
    tt = y * 12 + mo - 1
    pre_t = range(tt - 12, tt)
    post_t = range(tt + 1, tt + 13)  # 開業月は除く
    if name == "北陸・敦賀":
        post_t = range(tt + 1, min(tt + 13, 2025 * 12 + 12))
        pre_t = range(tt - len(post_t), tt)  # 同じ長さの前
    mp = mon.pivot_table(index="route", columns="t", values="pax")
    cols = list(pre_t) + list(post_t)
    if not set(cols) <= set(mp.columns):
        mrows.append(dict(event=name, note="月次データが足りない"))
        continue
    c = mp.loc[[r for r in mp.index if is_control(r)], cols].dropna()
    c = c[(c > 3000).all(axis=1)]
    lg = np.log(mp[cols])
    dcm = (lg.loc[c.index, list(post_t)].sum(axis=1) - lg.loc[c.index, list(pre_t)].sum(axis=1)) / len(post_t)
    for r in treated:
        if r not in mp.index or mp.loc[r, cols].isna().any():
            continue
        dt = (lg.loc[r, list(post_t)].sum() - lg.loc[r, list(pre_t)].sum()) / len(post_t)
        est = dt - dcm.mean()
        p, _ = perm_p(est, dcm)
        mrows.append(dict(event=name, route=r, months=len(post_t), n_ctrl=len(c), did_pct=np.expm1(est) * 100, perm_p=p))
mres = pd.DataFrame(mrows)
mres.to_csv(os.path.join(R, "did_monthly12.csv"), index=False, encoding="utf-8-sig")
print(mres.round(3).to_string())

# 月次の指数（開業の13〜24か月前の同じ月=100、対照平均の動きを除く）：図用
idx = []
mp = mon.pivot_table(index="route", columns="t", values="pax")
for name, op, t0, treated, rail in EVENTS[:4]:
    y, mo = map(int, op.split("-"))
    tt = y * 12 + mo - 1
    cols = [t for t in range(tt - 24, tt + 37) if t in mp.columns and (t // 12) not in COVID]
    c = mp.loc[[r for r in mp.index if is_control(r)], cols].dropna()
    c = c[(c > 3000).all(axis=1)]
    lg = np.log(mp[cols])
    # 季節をそろえるため、各路線の「開業の13〜24か月前の同じ月」で割る（開業前の1年も動きが見えるように）
    for r in treated:
        if r not in mp.index:
            continue
        for t in cols:
            m_ = t % 12
            base_t = [b for b in range(tt - 24, tt - 12) if b % 12 == m_]
            if not base_t:
                continue
            b0 = base_t[0]
            if pd.isna(mp.loc[r, t]) or pd.isna(mp.loc[r, b0]):
                continue
            g = (np.log(mp.loc[r, t]) - np.log(mp.loc[r, b0])) - (lg.loc[c.index, t] - lg.loc[c.index, b0]).mean()
            idx.append(dict(event=name, route=r, t=t - tt, year=t // 12, month=t % 12 + 1, idx=np.exp(g) * 100))
pd.DataFrame(idx).to_csv(os.path.join(R, "monthly_index.csv"), index=False, encoding="utf-8-sig")

# ---- 検出力の目安：対照の「処置したことにした」差の差のばらつき ----
pre, post = window(2015, 3)
ctrls = controls_for(pre, post)
_, d_c = did_one(piv, ctrls[0], ctrls, pre, post)
_, vals = perm_p(0, d_c)
pd.DataFrame([dict(sd_pct=np.std(vals) * 100, q05=np.expm1(np.quantile(vals, 0.025)) * 100,
                   q95=np.expm1(np.quantile(vals, 0.975)) * 100, n=len(vals))]).to_csv(
    os.path.join(R, "placebo_spread.csv"), index=False, encoding="utf-8-sig")
print("placebo sd", np.std(vals) * 100, np.expm1(np.quantile(vals, [0.025, 0.975])) * 100)
