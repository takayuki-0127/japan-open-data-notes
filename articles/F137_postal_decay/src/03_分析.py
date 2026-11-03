"""03 分析: 郵便物の減り方を4つのモデルで当てはめ、「いつ半分になるか」を予測区間つきで出す"""
import json, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import curve_fit
warnings.filterwarnings('ignore')
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'; OUT.mkdir(exist_ok=True)
W = pd.read_csv(ROOT / 'data/postal_annual_wide.csv', index_col='fy')
L = pd.read_csv(ROOT / 'data/postal_annual_long.csv')
BASE = 2025
rng = np.random.default_rng(137)

# ---- モデル（t = 年度 - 2025、y は 億通）----
def f_exp(t, a, b): return a + b * t                               # log y
def f_quad(t, a, b, c): return a + b * t + c * t**2                  # log y
def f_logis(t, F, U, k, t0): return np.log(F + (U - F) / (1 + np.exp(k * (t - t0))))  # 下限 F へ近づく逆S字
def f_expfl(t, F, A, k): return np.log(F + A * np.exp(-k * t))       # 指数＋下限

MODELS = {
 '指数（一定の割合で減る）': (f_exp, lambda y, t: [np.log(y[-1]), -0.03], None),
 '対数2次（減り方が加速）': (f_quad, lambda y, t: [np.log(y[-1]), -0.03, 0.0], None),
 'ロジスティック（下限あり）': (f_logis, lambda y, t: [y.min() * 0.3, y.max() * 1.1, 0.15, 0.0],
                         ([0, 0, 0.001, -60], [np.inf, np.inf, 2, 60])),
 '指数＋下限': (f_expfl, lambda y, t: [y.min() * 0.3, y[-1] * 0.7, 0.05],
              ([0, 0, 0.0001], [np.inf, np.inf, 2])),
}

def fit(name, t, y):
    f, p0, bd = MODELS[name]
    ly = np.log(y)
    if bd is None:
        p, _ = curve_fit(f, t, ly, p0=p0(y, t), maxfev=20000)
    else:
        # 下限つきのモデルは、F を 0〜最小値の範囲で何通りか試して一番よいものを使う
        best = None
        for F0 in np.linspace(0, y.min() * 0.95, 8):
            q0 = p0(y, t); q0[0] = F0
            try:
                p, _ = curve_fit(f, t, ly, p0=q0, bounds=bd, maxfev=20000)
                sse = np.sum((ly - f(t, *p))**2)
                if best is None or sse < best[0]: best = (sse, p)
            except Exception:
                pass
        if best is None: return None
        p = best[1]
    return p

def cross_year(name, p, target, tmax=75):
    f = MODELS[name][0]
    tt = np.arange(0, tmax + 0.001, 0.01)
    yy = np.exp(f(tt, *p))
    idx = np.where(yy <= target)[0]
    return BASE + tt[idx[0]] if len(idx) else np.inf

def series(col, start=2011, end=2025, drop=(), extra=None):
    s = W[col].dropna() / 1e5   # 千通 → 億通
    if extra is not None: s = pd.concat([s, extra]).sort_index()
    s = s[(s.index >= start) & (s.index <= end) & (~s.index.isin(drop))]
    return s

def analyse(s, B=1000, label=''):
    t = s.index.values - BASE; y = s.values
    target = s.loc[BASE] / 2 if BASE in s.index else None
    rows = []
    for name in MODELS:
        p = fit(name, t, y)
        if p is None: rows.append(dict(model=name, ok=False)); continue
        f = MODELS[name][0]
        res = np.log(y) - f(t, *p)
        k = len(p); n = len(y)
        aic = n * np.log(np.sum(res**2) / n) + 2 * k
        r = dict(model=name, ok=True, params=[float(x) for x in p], rmse_log=float(np.sqrt(np.mean(res**2))), aic=float(aic))
        if target is not None:
            r['half_year'] = float(cross_year(name, p, target))
            # 残差ブートストラップで予測区間（パラメータの不確かさ＋将来の年ごとのぶれ）
            ys = []
            for b in range(B):
                yb = np.exp(f(t, *p) + rng.choice(res, n, replace=True))
                pb = fit(name, t, yb)
                if pb is None: continue
                ys.append(cross_year(name, pb, target))
            ys = np.array(ys)
            fin = ys[np.isfinite(ys)]
            r['half_boot_n'] = int(len(ys)); r['half_not_reached_by_2100'] = float(np.mean(~np.isfinite(ys)))
            r['half_q05'], r['half_q50'], r['half_q95'] = [float(np.quantile(ys, q)) if np.isfinite(np.quantile(ys, q)) else None for q in (0.05, 0.5, 0.95)]
            # 2030・2035年度の予測と90%区間（年ごとのぶれも足す）
            for yr in (2030, 2035):
                sims = []
                for b in range(400):
                    yb = np.exp(f(t, *p) + rng.choice(res, n, replace=True))
                    pb = fit(name, t, yb)
                    if pb is None: continue
                    sims.append(np.exp(f(yr - BASE, *pb) + rng.choice(res)))
                r[f'pred_{yr}'] = float(np.exp(f(yr - BASE, *p)))
                r[f'pred_{yr}_q05'], r[f'pred_{yr}_q95'] = float(np.quantile(sims, .05)), float(np.quantile(sims, .95))
        rows.append(r)
    return rows

def rolling_cv(s, origins=range(2017, 2023), H=3):
    out = []
    for T in origins:
        tr = s[s.index <= T]
        t = tr.index.values - BASE; y = tr.values
        for name in MODELS:
            p = fit(name, t, y)
            if p is None: continue
            f = MODELS[name][0]
            for h in range(1, H + 1):
                yr = T + h
                if yr not in s.index: continue
                pred = np.exp(f(yr - BASE, *p))
                out.append(dict(origin=T, h=h, model=name, year=yr, actual=s.loc[yr], pred=pred, ape=abs(pred / s.loc[yr] - 1) * 100))
    return pd.DataFrame(out)

results = {}
# ---- 主分析：郵便物 FY2011〜2025 ----
s_main = series('郵便物')
results['main'] = analyse(s_main, label='main')
cv = rolling_cv(s_main); cv.to_csv(OUT / 'rolling_cv.csv', index=False)
results['cv_mape'] = cv.groupby('model').ape.mean().round(2).to_dict()
results['cv_mape_by_h'] = {m: g.groupby('h').ape.mean().round(2).to_dict() for m, g in cv.groupby('model')}

# ---- すでに「半分」になった年：FY2003 の半分を下回った年度 ----
s_all = W['郵便物'].dropna() / 1e5
results['fy2003'] = float(s_all.loc[2003]); results['fy2025'] = float(s_all.loc[2025])
results['ratio_2025_2003'] = float(s_all.loc[2025] / s_all.loc[2003])
results['first_below_half_2003'] = int(s_all[s_all <= s_all.loc[2003] / 2].index.min())
yoy = s_all.pct_change() * 100
results['yoy_recent'] = {int(k): round(float(v), 2) for k, v in yoy.loc[2012:].items() if np.isfinite(v)}
g = lambda a, b: (s_all.loc[b] / s_all.loc[a]) ** (1 / (b - a)) - 1
results['cagr'] = {'2003-2007': g(2003, 2007), '2011-2016': g(2011, 2016), '2016-2021': g(2016, 2021), '2021-2025': g(2021, 2025)}

# ---- 種類別：指数モデルの年率と半減期（FY2011〜2025 と FY2016〜2025）----
typ = {}
for col in ['第一種', '第二種', '年賀', '第三種', '特殊', '荷物', '総計']:
    for st in (2011, 2016):
        s = series(col, start=st)
        t = s.index.values - BASE
        b = np.polyfit(t, np.log(s.values), 1)[0]
        typ[f'{col}_{st}'] = dict(rate=float(np.exp(b) - 1), half_life=float(np.log(2) / -b) if b < 0 else None,
                                  v2025=float(s.loc[2025]), share2025=float(W.loc[2025, col] / W.loc[2025, '郵便物']) if col != '総計' else None)
results['types'] = typ
# 構成比の変化
results['share'] = {str(y): {c: float(W.loc[y, c] / W.loc[y, '郵便物']) for c in ['第一種', '第二種', '年賀', '第三種', '特殊']} for y in (2003, 2011, 2025)}

# ---- 頑健性 ----
rob = {}
rob['R1_2016-2025'] = analyse(series('郵便物', start=2016), B=500)
der = L[(L.item == '郵便物') & (L.kind == 'derived_from_rate')].set_index('fy').value / 1e5
rob['R2_2003-2025（欠けあり）'] = analyse(series('郵便物', start=2003), B=500)
rob['R3_2020年度を除く'] = analyse(series('郵便物', drop=(2020,)), B=500)
rob['R5_FY2010（逆算）を加える'] = analyse(series('郵便物', start=2010, extra=der), B=500)
rob['R6_荷物を含む総計'] = analyse(series('総計'), B=500)
results['robust'] = rob

# R4: 値上げ（2024年10月）前の FY2023 までで当てはめ → FY2024・2025 の予測誤差と「FY2023の半分」に届く年
s23 = series('郵便物', end=2023)
t = s23.index.values - BASE
r4 = {}
for name in MODELS:
    p = fit(name, t, s23.values)
    if p is None: continue
    f = MODELS[name][0]
    r4[name] = dict(pred2024=float(np.exp(f(-1, *p))), pred2025=float(np.exp(f(0, *p))),
                    err2024=float(np.exp(f(-1, *p)) / s_main.loc[2024] - 1), err2025=float(np.exp(f(0, *p)) / s_main.loc[2025] - 1),
                    half_of_fy2025_actual=float(cross_year(name, p, s_main.loc[2025] / 2)))
results['R4_値上げ前まで'] = r4

json.dump(results, open(OUT / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)

# 表
rows = []
for k, lst in [('主分析 FY2011-2025', results['main'])] + list(rob.items()):
    for r in lst:
        if not r.get('ok'): continue
        rows.append(dict(spec=k, model=r['model'], rmse_log=round(r['rmse_log'], 4), aic=round(r['aic'], 1),
                         half_year=round(r.get('half_year', np.nan), 1), q05=r.get('half_q05'), q50=r.get('half_q50'), q95=r.get('half_q95'),
                         not_reached=r.get('half_not_reached_by_2100'), pred2030=round(r.get('pred_2030', np.nan), 1), pred2035=round(r.get('pred_2035', np.nan), 1)))
pd.DataFrame(rows).to_csv(OUT / 'half_year_table.csv', index=False, encoding='utf-8')
print(pd.DataFrame(rows).to_string())
print(json.dumps({k: results[k] for k in ['cv_mape', 'fy2003', 'fy2025', 'ratio_2025_2003', 'first_below_half_2003', 'cagr']}, ensure_ascii=False, indent=1))
print(json.dumps(results['R4_値上げ前まで'], ensure_ascii=False, indent=1))
print(json.dumps(typ, ensure_ascii=False, indent=1))
