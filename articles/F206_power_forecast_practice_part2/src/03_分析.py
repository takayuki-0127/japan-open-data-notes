# F206 電力需要の予測を実務で回す（後編）：階層の整合・区間の当たり方・1年の見張り
# 入力：data/（F205・F157・F22 のデータを切り出したもの）
# 出力：results/
import json, os, warnings, numpy as np, pandas as pd, lightgbm as lgb
warnings.filterwarnings("ignore")
np.random.seed(206)
H = os.path.dirname(os.path.abspath(__file__)) + '/..'
R = H + '/results'; os.makedirs(R, exist_ok=True)
EVAL0, EVAL1 = '2026-01-01', '2026-09-30 23:00'   # 評価期間（10〜12月は誤差の履歴をためる期間）

# ---------- データ ----------
def area(a):
    p = pd.read_csv(f'{H}/data/area_pred_{a}_2025_26.csv.gz', parse_dates=['ts']).set_index('ts')
    h = pd.read_csv(f'{H}/data/hourly_{a}_2024_26.csv.gz', parse_dates=['ts']).set_index('ts')
    return p, h
pT, hT = area('tokyo'); pK, hK = area('kansai')
ts = pT.index
assert (pK.index == ts).all()

# ---------- A. 合計（東京＋関西）を直接当てる予測（エリアの予測とは別に作る） ----------
def make_feat(hT, hK):
    d = pd.DataFrame({'y': hT.demand + hK.demand})
    d['hour'] = d.index.hour; d['dow'] = d.index.dayofweek; d['month'] = d.index.month
    d['hol'] = ((hT.holiday == 1) | (d.dow >= 5)).astype(int)
    for c in ['temp_mean', 'temp_max', 'temp_min']:
        d[c + '_T'] = hT[c]; d[c + '_K'] = hK[c]
    d['lag24'] = d.y.shift(24); d['lag168'] = d.y.shift(168)
    d['prevday'] = d.y.shift(24).rolling(24).mean()
    return d
F = make_feat(hT, hK)
FEATS_FULL = ['hour', 'dow', 'month', 'hol', 'temp_mean_T', 'temp_max_T', 'temp_min_T',
              'temp_mean_K', 'temp_max_K', 'temp_min_K', 'lag24', 'lag168', 'prevday']
FEATS_NOTEMP = ['hour', 'dow', 'month', 'hol', 'lag24', 'lag168', 'prevday']

def fit_monthly(F, feats, seed=206):
    out = pd.Series(index=ts, dtype=float)
    for m in pd.period_range('2025-10', '2026-09', freq='M'):
        tr = F[(F.index < m.start_time)].dropna()
        te = F[(F.index >= m.start_time) & (F.index <= m.end_time)]
        mdl = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31,
                                min_child_samples=20, subsample=0.9, subsample_freq=1,
                                colsample_bytree=0.9, random_state=seed, verbose=-1, n_jobs=2)
        mdl.fit(tr[feats], tr.y)
        out.loc[te.index] = mdl.predict(te[feats])
    return out
totbase = fit_monthly(F, FEATS_FULL)
totbase_notemp = fit_monthly(F, FEATS_NOTEMP)

Y = pd.DataFrame({'T': F.y.reindex(ts), 'Tk': pT.actual, 'Ks': pK.actual})

def bases(area_col, tot):
    return pd.DataFrame({'T': tot, 'Tk': pT[area_col], 'Ks': pK[area_col]})

# ---------- 整合（3系列：合計・東京・関西） ----------
S = np.array([[1, 1], [1, 0], [0, 1]], float)
def P_of(W):
    Wi = np.linalg.inv(W)
    return np.linalg.inv(S.T @ Wi @ S) @ S.T @ Wi
def shrink_cov(E):
    # Schäfer–Strimmer 型：相関を 0 に縮める
    n = E.shape[0]; S_ = np.cov(E, rowvar=False); sd = np.sqrt(np.diag(S_))
    Xs = (E - E.mean(0)) / sd; C = (Xs.T @ Xs) / n
    w = np.zeros_like(C)
    for i in range(3):
        for j in range(3):
            if i != j:
                wij = Xs[:, i] * Xs[:, j]
                w[i, j] = np.var(wij) * n / (n - 1) ** 2
    num = w[~np.eye(3, dtype=bool)].sum(); den = (C[~np.eye(3, dtype=bool)] ** 2).sum()
    lam = float(np.clip(num / den, 0, 1)) if den > 0 else 1.0
    Cs = (1 - lam) * C; np.fill_diagonal(Cs, 1.0)
    return Cs * np.outer(sd, sd), lam

def reconcile(B, window_days=90, share_days=28):
    days = pd.date_range(EVAL0[:10], EVAL1[:10], freq='D')
    E = (Y - B)  # 予測の外れ（実績−予測）
    out = {k: [] for k in ['base', 'BU', 'TD', 'OLS', 'WLS', 'MinT']}; lams = []
    for d in days:
        idx = (B.index >= d) & (B.index < d + pd.Timedelta(days=1))
        hist = E[(E.index < d) & (E.index >= d - pd.Timedelta(days=window_days))].values
        b = B[idx].values
        out['base'].append(b)
        out['BU'].append(np.c_[b[:, 1] + b[:, 2], b[:, 1], b[:, 2]])
        sh = Y[(Y.index < d) & (Y.index >= d - pd.Timedelta(days=share_days))]
        share = (sh.Tk / sh['T']).groupby(sh.index.hour).mean().reindex(range(24)).values
        out['TD'].append(np.c_[b[:, 0], b[:, 0] * share, b[:, 0] * (1 - share)])
        for name, W in [('OLS', np.eye(3)), ('WLS', np.diag(hist.var(0)))]:
            P = P_of(W); out[name].append((S @ P @ b.T).T)
        Wm, lam = shrink_cov(hist); lams.append(lam)
        out['MinT'].append((S @ P_of(Wm) @ b.T).T)
    eidx = Y[(Y.index >= EVAL0) & (Y.index <= EVAL1)].index
    res = {k: pd.DataFrame(np.vstack(v), index=eidx, columns=['T', 'Tk', 'Ks']) for k, v in out.items()}
    return res, float(np.mean(lams))

def mape(pred, act):
    return float((np.abs(pred - act) / act).mean() * 100)

Ye = Y[(Y.index >= EVAL0) & (Y.index <= EVAL1)]
def table(res):
    rows = []
    for k, df in res.items():
        rows.append({'方法': k, '合計': mape(df['T'], Ye['T']), '東京': mape(df.Tk, Ye.Tk), '関西': mape(df.Ks, Ye.Ks)})
    return pd.DataFrame(rows)

B_main = bases('毎週', totbase)
res_main, lam_main = reconcile(B_main)
tab_main = table(res_main); tab_main.to_csv(f'{R}/A_reconcile_main.csv', index=False)

# 矛盾の大きさ（そろえる前）：合計の予測 − （東京＋関西の予測）
gap = (B_main['T'] - (B_main.Tk + B_main.Ks))
gap_e = gap[(gap.index >= EVAL0) & (gap.index <= EVAL1)]
gap_pct = (gap_e / Ye['T'] * 100)
gap_daily = gap_pct.groupby(gap_pct.index.date).mean()
pd.DataFrame({'date': gap_daily.index, 'gap_pct': gap_daily.values}).to_csv(f'{R}/A_incoherence_daily.csv', index=False)

# 週のブロック・ブートストラップ：MinT − BU、MinT − base
def block_boot(a, b, act, nb=2000, seed=206):
    ea = (np.abs(a - act) / act); eb = (np.abs(b - act) / act)
    wk = ea.index.to_period('W')
    da = ea.groupby(wk).mean(); db = eb.groupby(wk).mean()
    diff = (da - db).values; rng = np.random.default_rng(seed)
    bs = [rng.choice(diff, len(diff), replace=True).mean() for _ in range(nb)]
    return float(diff.mean() * 100), float(np.percentile(bs, 2.5) * 100), float(np.percentile(bs, 97.5) * 100)

def boot_rows(res, label):
    rows = []
    for lvl, nm in [('T', '合計'), ('Tk', '東京'), ('Ks', '関西')]:
        for other in ['BU', 'base']:
            m, lo, hi = block_boot(res['MinT'][lvl], res[other][lvl], Ye[lvl])
            rows.append({'条件': label, '比べる相手': other, 'レベル': nm, '差': m, '下限': lo, '上限': hi})
    return rows
boot = boot_rows(res_main, '主（毎週・誤差90日）')

# 頑健性1：誤差の履歴の長さ
rob = []
for w in [30, 180]:
    r, _ = reconcile(B_main, window_days=w); t = table(r); t['条件'] = f'誤差の履歴{w}日'; rob.append(t)
    boot += boot_rows(r, f'誤差の履歴{w}日')
# 頑健性2：エリアの予測を「毎月」「固定」に
for col, lab in [('毎月', 'エリア＝毎月'), ('固定（開始前に1回）', 'エリア＝固定')]:
    r, _ = reconcile(bases(col, totbase)); t = table(r); t['条件'] = lab; rob.append(t)
    boot += boot_rows(r, lab)
# 頑健性3：合計の予測を気温なしに（合計の予測が弱いとき）
r, _ = reconcile(bases('毎週', totbase_notemp)); t = table(r); t['条件'] = '合計＝気温なし'; rob.append(t)
boot += boot_rows(r, '合計＝気温なし')
# 頑健性4：季節（1〜6月／7〜9月）
for lab, m0, m1 in [('1〜6月', '2026-01-01', '2026-06-30 23:00'), ('7〜9月', '2026-07-01', '2026-09-30 23:00')]:
    rows = []
    for k, df in res_main.items():
        dd = df[(df.index >= m0) & (df.index <= m1)]; yy = Ye[(Ye.index >= m0) & (Ye.index <= m1)]
        rows.append({'方法': k, '合計': mape(dd['T'], yy['T']), '東京': mape(dd.Tk, yy.Tk), '関西': mape(dd.Ks, yy.Ks), '条件': lab})
    rob.append(pd.DataFrame(rows))
tab_main2 = tab_main.copy(); tab_main2['条件'] = '主（毎週・誤差90日）'
pd.concat([tab_main2] + rob).to_csv(f'{R}/A_reconcile_robust.csv', index=False)
pd.DataFrame(boot).to_csv(f'{R}/A_boot_mint.csv', index=False)

# ---------- B. 時間の階層：24時間の予測の合計と、1日の量を直接当てる予測 ----------
def daily_feat(h):
    d = h.resample('D').agg({'demand': 'sum', 'temp_mean': 'first', 'temp_max': 'first', 'temp_min': 'first', 'holiday': 'max'})
    d = d.rename(columns={'demand': 'y'}); d['dow'] = d.index.dayofweek; d['month'] = d.index.month
    d['hol'] = ((d.holiday == 1) | (d.dow >= 5)).astype(int)
    d['lag1'] = d.y.shift(1); d['lag7'] = d.y.shift(7)
    return d
def daily_monthly(d):
    feats = ['dow', 'month', 'hol', 'temp_mean', 'temp_max', 'temp_min', 'lag1', 'lag7']
    out = pd.Series(index=pd.date_range('2025-10-01', '2026-09-30'), dtype=float)
    for m in pd.period_range('2025-10', '2026-09', freq='M'):
        tr = d[d.index < m.start_time].dropna(); te = d[(d.index >= m.start_time) & (d.index <= m.end_time)]
        mdl = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=10,
                                random_state=206, verbose=-1, n_jobs=2)
        mdl.fit(tr[feats], tr.y); out.loc[te.index] = mdl.predict(te[feats])
    return out
temp_rows = []
for a, p, h in [('東京', pT, hT), ('関西', pK, hK)]:
    dd = daily_feat(h); dpred = daily_monthly(dd)
    hp = p['毎週']; ha = p.actual
    E = ha - hp
    days = pd.date_range(EVAL0[:10], EVAL1[:10], freq='D')
    Sd = np.vstack([np.ones((1, 24)), np.eye(24)])
    rec_h = {'時間の合計（下から）': [], '構造の重み': [], '分散の重み': []}
    dE = (dd.y - dpred)
    for d in days:
        idx = (hp.index >= d) & (hp.index < d + pd.Timedelta(days=1))
        b = np.r_[dpred.loc[d], hp[idx].values]
        rec_h['時間の合計（下から）'].append(hp[idx].values)
        for nm in ['構造の重み', '分散の重み']:
            if nm == '構造の重み':
                w = np.r_[24.0, np.ones(24)]
            else:
                he = E[(E.index < d) & (E.index >= d - pd.Timedelta(days=90))]
                vh = he.groupby(he.index.hour).var().reindex(range(24)).values
                vd = dE[(dE.index < d) & (dE.index >= d - pd.Timedelta(days=90))].var()
                w = np.r_[vd, vh]
            Wi = np.diag(1 / w); P = np.linalg.inv(Sd.T @ Wi @ Sd) @ Sd.T @ Wi
            rec_h[nm].append(P @ b)
    eidx = hp[(hp.index >= EVAL0) & (hp.index <= EVAL1)].index
    act_d = dd.y.loc[days]; act_h = ha.loc[eidx]
    for nm, v in rec_h.items():
        rh = pd.Series(np.concatenate(v), index=eidx)
        rd = rh.groupby(rh.index.normalize()).sum()
        temp_rows.append({'エリア': a, '方法': nm, '1日の量のMAPE': mape(rd.values, act_d.values), '1時間ごとのMAPE': mape(rh, act_h)})
    temp_rows.append({'エリア': a, '方法': '1日の量を直接', '1日の量のMAPE': mape(dpred.loc[days].values, act_d.values), '1時間ごとのMAPE': np.nan})
pd.DataFrame(temp_rows).to_csv(f'{R}/B_temporal.csv', index=False)

# ---------- C. 区間（80%・95%）の当たり方と、見張り ----------
def intervals(p, col='毎週', days_hist=90):
    rel = (p.actual / p[col] - 1)
    q = {}
    for d in pd.date_range(EVAL0[:10], EVAL1[:10], freq='D'):
        hist = rel[(rel.index < d) & (rel.index >= d - pd.Timedelta(days=days_hist))]
        g = hist.groupby(hist.index.hour)
        q[d] = pd.DataFrame({'lo80': g.quantile(0.10), 'hi80': g.quantile(0.90), 'lo95': g.quantile(0.025), 'hi95': g.quantile(0.975)})
    rows = []
    for d, qq in q.items():
        idx = (p.index >= d) & (p.index < d + pd.Timedelta(days=1))
        sub = p[idx]; hrs = sub.index.hour
        f = sub[col].values
        rows.append(pd.DataFrame({'ts': sub.index, 'actual': sub.actual.values, 'pred': f,
                                  'lo80': f * (1 + qq.lo80.reindex(hrs).values), 'hi80': f * (1 + qq.hi80.reindex(hrs).values),
                                  'lo95': f * (1 + qq.lo95.reindex(hrs).values), 'hi95': f * (1 + qq.hi95.reindex(hrs).values)}))
    return pd.concat(rows).set_index('ts')
cov_rows = []
for a, p in [('東京', pT), ('関西', pK)]:
    for hist in [30, 90, 180]:
        iv = intervals(p, days_hist=hist)
        c80 = ((iv.actual >= iv.lo80) & (iv.actual <= iv.hi80)); c95 = ((iv.actual >= iv.lo95) & (iv.actual <= iv.hi95))
        if a == '東京' and hist == 90:
            iv.to_csv(f'{R}/C_intervals_tokyo.csv.gz', compression='gzip'); ivT = iv
            mon = pd.DataFrame({'80%区間': c80.groupby(iv.index.month).mean() * 100, '95%区間': c95.groupby(iv.index.month).mean() * 100})
            mon.index.name = '月'; mon.to_csv(f'{R}/C_coverage_monthly_tokyo.csv')
            # ピーク（1日の最大）の当たり方：上の端を使う
            dmax = iv.groupby(iv.index.date).apply(lambda x: x.loc[x.actual.idxmax()])
            peak_hi95_cov = float((dmax.actual <= dmax.hi95).mean() * 100)
        cov_rows.append({'エリア': a, '誤差の履歴': f'{hist}日', '80%区間に入った割合': c80.mean() * 100, '95%区間に入った割合': c95.mean() * 100,
                         '80%区間の幅（平均%）': ((iv.hi80 - iv.lo80) / iv.pred).mean() * 100})
pd.DataFrame(cov_rows).to_csv(f'{R}/C_coverage.csv', index=False)

# 見張り：ずれの7日平均（符号つき）が ±1.5% を超えた日（F205 のおすすめの例）
rel = (pT.actual - pT['毎週']) / pT.actual * 100
drel = rel.groupby(rel.index.normalize()).mean()
ma7 = drel.rolling(7).mean()
dm = (pT['毎週'] - pT.actual).abs() / pT.actual * 100
dmape = dm.groupby(dm.index.normalize()).mean()
mon_df = pd.DataFrame({'日のMAPE': dmape, 'ずれの7日平均': ma7})
mon_df.to_csv(f'{R}/C_monitor_daily_tokyo.csv')
alert = ma7.abs() > 1.5
# アラートの「まとまり」を数える（連続した日を1回とする）
runs = []; cur = None
for d, v in alert.items():
    if v and cur is None: cur = [d, d]
    elif v: cur[1] = d
    elif cur is not None: runs.append(cur); cur = None
if cur is not None: runs.append(cur)
runs_df = pd.DataFrame([{'始まり': r[0].date(), '終わり': r[1].date(), '日数': (r[1] - r[0]).days + 1,
                          'ずれの7日平均の最大': float(ma7.loc[r[0]:r[1]].abs().max())} for r in runs])
runs_df.to_csv(f'{R}/C_alerts_tokyo.csv', index=False)

# ダッシュボード用の1日（2026年度上期で需要がいちばん大きかった日の前日夜に出したとする）
s26 = pT[(pT.index >= '2026-07-01')]
peak_day = s26.actual.idxmax().normalize()
dash = ivT.loc[str(peak_day.date())].copy()
dash.to_csv(f'{R}/C_dashboard_day.csv')

main = {
    '評価期間': f'{EVAL0}〜{EVAL1[:10]}',
    'A_MAPE_main': tab_main.set_index('方法').round(3).to_dict(orient='index'),
    'A_MinT_縮小の強さ平均': lam_main,
    'A_矛盾_合計比_平均絶対': float(gap_pct.abs().mean()), 'A_矛盾_合計比_95点': float(gap_pct.abs().quantile(0.95)),
    'A_合計の予測が東京＋関西より大きい時間の割合': float((gap_e > 0).mean() * 100),
    'A_boot': boot[:6],
    'B_temporal': temp_rows,
    'C_coverage': cov_rows, 'C_peak_hi95_cov_tokyo': peak_hi95_cov,
    'C_alerts': runs_df.to_dict(orient='records') if len(runs_df) else [],
    'C_alert_days': int(alert.sum()),
    'dashboard_day': str(peak_day.date()),
}
json.dump(main, open(f'{R}/main.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: main[k] for k in ['A_MAPE_main', 'A_MinT_縮小の強さ平均', 'A_矛盾_合計比_平均絶対', 'A_矛盾_合計比_95点', 'C_alert_days', 'dashboard_day', 'C_peak_hi95_cov_tokyo']}, ensure_ascii=False, indent=1, default=str))
