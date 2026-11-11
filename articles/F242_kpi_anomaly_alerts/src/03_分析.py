"""03 分析：
A. 架空の会社「あおばマート」（架空）の毎日の注文数をシミュレーションで作り、
   わざと入れた「異常」を、6つの検知ルールがどれだけ見つけ、どれだけ空振りするかを比べる（乱数の種20通り）。
B. 本物の毎日の数字（東京・関西の電力需要、F22 のデータ）に同じルールを当て、1年に何回鳴り、どんな日に鳴るかを見る。"""
import json, numpy as np, pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from detectors import d1_prev_day, d2_moving, d3_same_weekday, d4_stl, d5_calendar, d6_confirm, _mad
os.makedirs("results", exist_ok=True)
NSEED = 20
cal = pd.read_csv("data/daily_power_tokyo.csv", parse_dates=["date"])
cal = cal[(cal.date >= "2021-01-01") & (cal.date <= "2025-12-31")].reset_index(drop=True)
DATES = cal.date.values; N = len(cal); WD = cal.date.dt.weekday.values
EVAL0 = int(np.where(cal.date >= "2021-04-01")[0][0]); YEARS = (N - EVAL0) / 365.25
camp = (cal.date.dt.day == 11).values
SP = np.where(cal.yearend.values | cal.obon.values, 2, np.where(cal.holiday.values == 1, 1, np.where(camp, 3, 0)))

def simulate(seed, sigma=0.04, n_inc=40):
    rng = np.random.default_rng(seed)
    t = np.arange(N); doy = cal.date.dt.dayofyear.values
    wde = np.array([0.02, 0.0, 0.0, 0.0, 0.03, 0.12, 0.15])[WD]
    ly = np.log(10000) + 0.05 * t / 365.25 + wde + 0.06 * np.cos(2 * np.pi * (doy - 350) / 365.25)
    md = cal.date.dt.month.values * 100 + cal.date.dt.day.values
    ly += np.where(cal.holiday.values == 1, 0.10, 0) + np.where(cal.obon.values == 1, 0.08, 0)
    ly += np.where((md >= 1226) & (md <= 1230), 0.10, 0) + np.where((md >= 1231) | (md <= 102), -0.20, 0)
    ly += np.where(camp, 0.25, 0)
    u = rng.normal(0, sigma, N); ar = np.zeros(N)
    for i in range(N): ar[i] = (0.3 * ar[i - 1] if i else 0) + u[i]
    ly += ar
    # 異常を入れる（重ならないよう10日以上あける）
    lab = np.zeros(N, int); inc = []
    cands = rng.permutation(np.arange(EVAL0, N - 5))
    for s in cands:
        if len(inc) >= n_inc: break
        if any(abs(s - x["start"]) < 10 for x in inc): continue
        dur = rng.choice([1, 2, 3], p=[0.6, 0.25, 0.15]); size = rng.choice([0.05, 0.10, 0.15, 0.20, 0.30])
        sign = -1 if rng.random() < 0.7 else 1
        ly[s:s + dur] += np.log(1 + sign * size)
        lab[s:s + dur] = len(inc) + 1
        inc.append(dict(start=int(s), dur=int(dur), size=float(size), sign=sign, special=int(SP[s:s + dur].max() > 0)))
    return ly, lab, inc

def run_all(ly, sp, wd, k=3.5, nweeks=4, with_stl=True):
    out = {}
    out["D1 前日比10%"] = d1_prev_day(ly)[1]
    out["D2 28日平均±3σ"] = d2_moving(ly)[1]
    out["D3 同じ曜日の中央値"] = d3_same_weekday(ly, k=k, nweeks=nweeks)[1]
    if with_stl:
        z4, a4, z4b, a4b = d4_stl(ly, k=k)
        out["D4 STLの残差"] = a4
        out["D4b STL＋外れで尺度"] = a4b
    z5, a5 = d5_calendar(ly, sp, wd, k=k, nweeks=nweeks)
    out["D5 D3＋暦"] = a5
    out["D6 D5＋2日確認"] = d6_confirm(z5, sp, k=k)
    return out, z5

def events(a, start):
    ev = []; t = start; n = len(a)
    while t < n:
        if a[t]:
            s = t
            while t + 1 < n and a[t + 1]: t += 1
            ev.append((s, t))
        t += 1
    return ev

def score(a, lab, inc, start=EVAL0):
    ev = events(a, start)
    win = np.zeros(len(a), bool)
    for x in inc: win[x["start"]:x["start"] + x["dur"] + 1] = True
    fa = sum(1 for s, e in ev if not win[s:e + 1].any())
    rows = []
    for x in inc:
        hit = np.where(a[x["start"]:x["start"] + x["dur"] + 1])[0]
        rows.append(dict(size=x["size"], sign=x["sign"], dur=x["dur"], special=x["special"],
                         found=int(len(hit) > 0), delay=int(hit[0]) if len(hit) else np.nan))
    return fa / YEARS, pd.DataFrame(rows)

# ---- A. シミュレーション ----
recs = []; incs = []
for seed in range(NSEED):
    ly, lab, inc = simulate(seed)
    al, _ = run_all(ly, SP, WD)
    for m, a in al.items():
        fa, df = score(a, lab, inc)
        nd = df[df.special == 0]
        recs.append(dict(seed=seed, method=m, fa_per_year=fa, recall=nd.found.mean(), recall_special=df[df.special == 1].found.mean(),
                         recall_drop10plus=nd[(nd.sign < 0) & (nd["size"] >= 0.10)].found.mean(),
                         delay_med=nd.delay.median(), n_inc=len(nd)))
        df["seed"] = seed; df["method"] = m; incs.append(df)
R = pd.DataFrame(recs); I = pd.concat(incs)
R.to_csv("results/A_sim_by_seed.csv", index=False)
summ = R.groupby("method").agg(fa_per_year=("fa_per_year", "mean"), fa_lo=("fa_per_year", lambda x: x.quantile(.025)), fa_hi=("fa_per_year", lambda x: x.quantile(.975)),
                               recall=("recall", "mean"), recall_lo=("recall", lambda x: x.quantile(.025)), recall_hi=("recall", lambda x: x.quantile(.975)),
                               recall_drop10plus=("recall_drop10plus", "mean"), recall_special=("recall_special", "mean"), delay_med=("delay_med", "mean")).round(3)
summ.to_csv("results/A_sim_summary.csv"); print(summ)
bysize = I[I.special == 0].groupby(["method", "sign", "size"]).found.mean().unstack("size").round(3)
bysize.to_csv("results/A_recall_by_size.csv"); print(bysize)

# 閾値を変えたとき（D1・D5・D6）
sweep = []
for seed in range(NSEED):
    ly, lab, inc = simulate(seed)
    for thr in [0.05, 0.10, 0.15, 0.20]:
        fa, df = score(d1_prev_day(ly, np.log(1 + thr))[1], lab, inc); nd = df[df.special == 0]
        sweep.append(dict(seed=seed, method="D1 前日比", k=thr, fa_per_year=fa, recall=nd.found.mean()))
    for k in [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]:
        z5, a5 = d5_calendar(ly, SP, WD, k=k)
        fa, df = score(a5, lab, inc); nd = df[df.special == 0]
        sweep.append(dict(seed=seed, method="D5 D3＋暦", k=k, fa_per_year=fa, recall=nd.found.mean()))
        fa, df = score(d6_confirm(z5, SP, k=k, k_hi=max(5.0, k + 1)), lab, inc); nd = df[df.special == 0]
        sweep.append(dict(seed=seed, method="D6 D5＋2日確認", k=k, fa_per_year=fa, recall=nd.found.mean()))
S = pd.DataFrame(sweep).groupby(["method", "k"])[["fa_per_year", "recall"]].mean().round(3)
S.to_csv("results/A_threshold_sweep.csv"); print(S)

# 頑健性：ばらつきの大きさ、比べる週の数
rob = []
for sigma in [0.02, 0.04, 0.08]:
    for nweeks in [4, 8]:
        for seed in range(10):
            ly, lab, inc = simulate(seed, sigma=sigma)
            al, _ = run_all(ly, SP, WD, nweeks=nweeks, with_stl=(nweeks == 4))
            for m, a in al.items():
                fa, df = score(a, lab, inc); nd = df[df.special == 0]
                rob.append(dict(sigma=sigma, nweeks=nweeks, seed=seed, method=m, fa_per_year=fa, recall=nd.found.mean()))
RB = pd.DataFrame(rob).groupby(["sigma", "nweeks", "method"])[["fa_per_year", "recall"]].mean().round(3)
RB.to_csv("results/A_robustness_noise_window.csv"); print(RB)

# ---- B. 本物の毎日の数字（電力需要） ----
def real(area, eval_from):
    d = pd.read_csv(f"data/daily_power_{area}.csv", parse_dates=["date"]).reset_index(drop=True)
    ly = np.log(d.demand.values); wd = d.date.dt.weekday.values
    sp = np.where(d.yearend.values | d.obon.values, 2, np.where(d.holiday.values == 1, 1, 0))
    al, z5 = run_all(ly, sp, wd)
    # D7：気温と暦を説明変数にした回帰（毎月、前の730日で当てはめ直す）
    if area == "tokyo":
        tm = d.tmean.values; n = len(d); z7 = np.full(n, np.nan)
        X = np.column_stack([np.ones(n), np.eye(7)[wd][:, 1:], d.holiday.values, d.yearend.values, d.obon.values,
                             np.maximum(tm - 20, 0), np.maximum(tm - 20, 0) ** 2, np.maximum(15 - tm, 0), np.maximum(15 - tm, 0) ** 2, np.arange(n) / 365.25])
        months = d.date.dt.to_period("M").values
        for mth in pd.unique(months):
            idx = np.where(months == mth)[0]; t0 = idx[0]
            if t0 < 730: continue
            tr = np.arange(t0 - 730, t0)
            b, *_ = np.linalg.lstsq(X[tr], ly[tr], rcond=None)
            s = _mad(ly[tr] - X[tr] @ b)
            z7[idx] = (ly[idx] - X[idx] @ b) / s
        al["D7 暦＋気温の回帰"] = np.abs(z7) > 3.5
    start = int(np.where(d.date >= eval_from)[0][0]); yrs = (len(d) - start) / 365.25
    # 鳴った日の分類
    tdev = np.full(len(d), np.nan)
    for t in range(28, len(d)): tdev[t] = d.tmean.values[t] - d.tmean.values[t - 28:t:7].mean()
    spn = sp > 0; adj = np.r_[False, spn[:-1]] | np.r_[spn[1:], False]
    cls = np.where(spn, "特別な日", np.where(adj, "特別な日の前後", np.where(np.abs(tdev) >= 4, "気温が急に変わった日", "そのほか")))
    rows = []
    for m, a in al.items():
        ev = events(a, start); days = np.where(a[start:])[0] + start
        c = pd.Series(cls[days]).value_counts()
        rows.append(dict(area=area, method=m, events_per_year=round(len(ev) / yrs, 1), alert_days_per_year=round(len(days) / yrs, 1),
                         **{f"share_{k}": round(c.get(k, 0) / max(len(days), 1), 3) for k in ["特別な日", "特別な日の前後", "気温が急に変わった日", "そのほか"]}))
    # 例：直近の警報日（D5・D7）
    ex = []
    for m in ["D5 D3＋暦", "D6 D5＋2日確認"] + (["D7 暦＋気温の回帰"] if area == "tokyo" else []):
        for t in np.where(al[m][start:])[0][-12:] + start:
            ex.append(dict(area=area, method=m, date=str(d.date[t].date()), class_=cls[t], tmean=d.tmean[t], z5=round(z5[t], 2)))
    return rows, ex, d, al, z5, start
rows_t, ex_t, dt_, al_t, z5_t, st_t = real("tokyo", "2018-04-01")
rows_k, ex_k, *_ = real("kansai", "2024-08-01")
RR = pd.DataFrame(rows_t + rows_k); RR.to_csv("results/B_real_power_alerts.csv", index=False); print(RR.to_string())
pd.DataFrame(ex_t + ex_k).to_csv("results/B_recent_alert_examples.csv", index=False)
# 図用の保存
np.savez_compressed("results/_fig_data.npz", tokyo_d5=al_t["D5 D3＋暦"], tokyo_d7=al_t["D7 暦＋気温の回帰"], tokyo_d1=al_t["D1 前日比10%"], z5=z5_t)
ly0, lab0, inc0 = simulate(0); al0, z50 = run_all(ly0, SP, WD)
pd.DataFrame({"date": cal.date, "orders": np.exp(ly0).round(), "anomaly": lab0 > 0, "sp": SP, "z5": z50, **{m: al0[m] for m in al0}}).to_csv("results/A_sim_seed0_series.csv", index=False)
main = dict(sim=summ.reset_index().to_dict("records"), sweep=S.reset_index().to_dict("records"), real=RR.to_dict("records"), nseed=NSEED, years=round(YEARS, 2))
json.dump(main, open("results/main.json", "w"), ensure_ascii=False, indent=1, default=float)
