"""03 分析：見通しの伸びと実績の伸びのずれ（log差、%）。結果は results/ に出す。"""
import json, os
import numpy as np, pandas as pd
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
RAW = os.path.join(ROOT, 'data', 'raw'); RES = os.path.join(ROOT, 'results'); os.makedirs(RES, exist_ok=True)
LAST = 2024
A = pd.read_csv(os.path.join(ROOT, 'data', 'processed', 'actuals.csv')).set_index('year')
# 参考系列：電気事業者計の2010年度は前年度より0.8%減り、総発電（+4.0%）・一般電気事業者の販売（+5.6%）と動きが逆。
# 集計の範囲が変わった可能性がある（推測）ので、2010年度だけ2009年度×総発電の伸びでつないだ系列も作る。
A['gen_utility_splice'] = A['gen_utility_fy']
A.loc[2010, 'gen_utility_splice'] = A.loc[2009, 'gen_utility_fy'] * A.loc[2010, 'gen_fy'] / A.loc[2009, 'gen_fy']
P = pd.read_csv(os.path.join(RAW, 'projections.csv'))
G = pd.read_csv(os.path.join(RAW, 'gdp_assumptions.csv'))
# 2001・2004 の見通しは電気事業用の発電電力量なので、電事連の「電気事業者計」（2001〜2010年度）と比べる（主）
MAIN = {'demand': 'demand_fy', 'generation': 'gen_owid_cal_twh', 'generation_utility': 'gen_utility_fy'}
# 入れ替え：需要↔発電（自家発込み）。電気事業用の見通しは自家発込みの発電電力量（初版の比べ方）
ALT = {'demand': 'gen_owid_cal_twh', 'generation': 'demand_fy', 'generation_utility': 'gen_owid_cal_twh'}
def proj_ratio(r):
    if not np.isnan(r.growth_rate):
        return (1 + r.growth_rate) ** (r.target_year - r.base_year)
    return r.target_value / r.base_value
def act(col, y, avg3=False):
    if avg3:
        ys = [v for v in (y-1, y, y+1) if v in A.index and v <= LAST and not np.isnan(A.loc[v, col])]
        return A.loc[ys, col].mean() if ys else np.nan
    return A.loc[y, col] if (y in A.index and y <= LAST) else np.nan
def anchor(col, b):
    """基準年の実績がない系列（電気事業者計は2001年度から）は、基準年より後で最初に値のある年を起点にする。"""
    for y in range(b, b + 3):
        if not np.isnan(act(col, y)):
            return y
    return None
def path_rows(series_map, avg3=False, last=LAST):
    out = []
    for _, r in P.iterrows():
        col = series_map[r.metric]; R = proj_ratio(r); T, b = r.target_year, r.base_year
        a = anchor(col, b)
        if a is None:
            continue
        a0 = act(col, a)
        for t in range(a + 1, min(T, last) + 1):
            at = act(col, t, avg3 and t == T)
            if np.isnan(at):
                continue
            pr = R ** ((t - a) / (T - b))  # 起点 a から t までの見通しの伸び（道筋の一部）
            e = np.log(pr) - np.log(at / a0)
            out.append(dict(vintage=r.vintage, name=r['name'], case=r.case, case_rank=r.case_rank, metric=r.metric,
                            base_year=b, target_year=T, year=t, horizon=t - b, at_target=(t == T),
                            proj_growth_pct=100 * (pr - 1), act_growth_pct=100 * (at / a0 - 1), err_pct=100 * (np.exp(e) - 1), err_log=e))
    return pd.DataFrame(out)
def summary(D):
    tgt = D[D.at_target].copy()
    latest = D.sort_values('year').groupby(['vintage', 'case', 'target_year']).tail(1)
    return tgt, latest
def hyp(D):
    tgt, latest = summary(D)
    reached = tgt[tgt.vintage.isin([1998, 2001, 2004, 2008]) & (tgt.target_year <= LAST)]
    # H1: base/high cases
    hi = reached[reached.case_rank == 'high']
    h1_n = int((hi.err_pct >= 5).sum()); h1 = dict(n_over5=h1_n, of=len(hi), rows=hi[['vintage','case','target_year','err_pct']].round(2).to_dict('records'), verdict='支持' if h1_n >= 3 else '外れ')
    # H2: spearman horizon vs |err| over all path points; also latest point per vintage-case
    rho, p = stats.spearmanr(D.horizon, D.err_log.abs())
    rho2, p2 = stats.spearmanr(latest.horizon, latest.err_log.abs())
    h2 = dict(rho_all=rho, p_all=p, n_all=len(D), rho_latest=rho2, p_latest=p2, n_latest=len(latest), verdict='支持' if rho >= 0.3 else '外れ')
    # H3: lowest case closer than highest in 2001, 2004, 2008 (target reached)
    comp = []
    for v in [2001, 2004, 2008]:
        s = reached[reached.vintage == v]
        lo = s[s.case_rank == 'low'].err_log.abs().values[0]; hi_ = s[s.case_rank == 'high'].err_log.abs().values[0]
        comp.append(dict(vintage=v, low_abs=100*lo, high_abs=100*hi_, low_closer=bool(lo < hi_)))
    h3 = dict(rows=comp, verdict='支持' if all(c['low_closer'] for c in comp) else '外れ')
    # H4: path error at LAST for 2015 (both cases) and 2021
    def at_last(v, case=None):
        s = D[(D.vintage == v) & (D.year == LAST)]
        if case: s = s[s.case == case]
        return s.err_pct.values
    e15 = at_last(2015); e21 = at_last(2021)
    h4 = dict(e2015=list(np.round(e15, 2)), e2021=list(np.round(e21, 2)),
              verdict='支持' if (min(e15) >= 5 and abs(e21[0]) <= 3) else '外れ')
    return dict(H1=h1, H2=h2, H3=h3, H4=h4)
def reask():
    """ずれを GDP の前提と GDP あたりの電力（原単位）に分ける。比べる年は min(目標年, 2022)（GDP は OWID の暦年で 2022 まで）。"""
    rows = []
    gcol = 'gdp_owid_cal'; LASTG = 2022
    for _, r in P.iterrows():
        if r.vintage not in G.vintage.values:
            continue
        col = MAIN[r.metric]; b, T = r.base_year, r.target_year; t = min(T, LASTG)
        a = anchor(col, b)
        R = proj_ratio(r); pr = R ** ((t - a) / (T - b))
        g = G[G.vintage == r.vintage]
        lg = 0.0
        for _, gg in g.iterrows():
            lo, hi = max(a, gg.from_year), min(t, gg.to_year)
            if hi > lo:
                if str(gg.real_gdp_growth) == 'actual':  # 公表時にすでに実績だった期間
                    lg += np.log(A.loc[hi, gcol] / A.loc[lo, gcol])
                else:
                    lg += (hi - lo) * np.log(1 + float(gg.real_gdp_growth))
        a_e = np.log(A.loc[t, col] / A.loc[a, col]); a_g = np.log(A.loc[t, gcol] / A.loc[a, gcol])
        p_e = np.log(pr); p_int = p_e - lg; a_int = a_e - a_g
        rows.append(dict(vintage=r.vintage, case=r.case, case_rank=r.case_rank, base_year=b, anchor_year=a, year=t, horizon=t-b,
                         err_total=100*(p_e - a_e), err_gdp=100*(lg - a_g), err_intensity=100*(p_int - a_int),
                         proj_gdp_growth=100*(np.exp(lg)-1), act_gdp_growth=100*(np.exp(a_g)-1),
                         proj_intensity=100*(np.exp(p_int)-1), act_intensity=100*(np.exp(a_int)-1)))
    return pd.DataFrame(rows)
def main():
    D = path_rows(MAIN); D.to_csv(os.path.join(RES, 'A_path_errors.csv'), index=False)
    tgt, latest = summary(D)
    tgt.to_csv(os.path.join(RES, 'B_target_year_errors.csv'), index=False)
    latest.to_csv(os.path.join(RES, 'C_latest_errors.csv'), index=False)
    H = hyp(D)
    rob = {}
    D1 = path_rows(ALT); rob['R1_alt_series'] = hyp(D1)
    D2 = path_rows(MAIN, avg3=True); rob['R2_avg3_at_target'] = hyp(D2)
    lt = latest.copy(); lt['err_per_year'] = lt.err_log / lt.horizon * 100
    rob['R3_per_year'] = dict(spearman_horizon_vs_abs_per_year=stats.spearmanr(lt.horizon, lt.err_per_year.abs())[0],
                              per_year=lt[['vintage','case','target_year','horizon','err_per_year']].round(2).to_dict('records'))
    D4 = D[D.vintage != 2010]; rob['R4_excl_2010plan'] = dict(H2_rho=stats.spearmanr(D4.horizon, D4.err_log.abs())[0])
    # R5：電気事業者計の2010年度は区分替えの影響がありうるので、2009年度で比べる（2001・2004）
    D5 = path_rows(MAIN, last=2009)
    r5 = D5[D5.vintage.isin([2001, 2004]) & (D5.year == 2009)]
    rob['R5_utility_to_2009'] = r5[['vintage','case','case_rank','year','proj_growth_pct','act_growth_pct','err_pct']].round(2).to_dict('records')
    # R6：電気事業用の見通しを、一般電気事業者の販売（使用電力量）の伸びと比べる（参考。発電と販売の差は自家発・卸からの買い取りなど）
    D6 = path_rows({'demand': 'demand_fy', 'generation': 'gen_owid_cal_twh', 'generation_utility': 'sales_general_fy'})
    r6 = D6[D6.vintage.isin([2001, 2004]) & D6.at_target]
    rob['R6_utility_sales'] = r6[['vintage','case','case_rank','year','proj_growth_pct','act_growth_pct','err_pct']].round(2).to_dict('records')
    # R7：2010年度をつないだ電気事業用の系列
    D7 = path_rows({'demand': 'demand_fy', 'generation': 'gen_owid_cal_twh', 'generation_utility': 'gen_utility_splice'})
    r7 = D7[D7.vintage.isin([2001, 2004]) & D7.at_target]
    rob['R7_utility_splice2010'] = r7[['vintage','case','case_rank','year','proj_growth_pct','act_growth_pct','err_pct']].round(2).to_dict('records')
    rob['R7_hyp'] = hyp(D7)
    # 2008の見通しの道筋のずれ（主の系列）：震災前・後
    d8 = D[(D.vintage == 2008) & (D.target_year == 2020) & D.year.isin([2008, 2009, 2010, 2011, 2012, 2015, 2019, 2020])]
    rob['path_2008'] = d8[['case','year','err_pct']].round(2).to_dict('records')
    # 2008の見通しを電気事業者計（2005→2010年度）で見た場合（参考）
    P8 = P[(P.vintage == 2008) & (P.target_year == 2020)].copy()
    u = []
    for _, r in P8.iterrows():
        R = proj_ratio(r); pr = R ** ((2010 - 2005) / (2020 - 2005))
        for col in ['gen_utility_fy', 'gen_owid_cal_twh']:
            u.append(dict(case=r.case, series=col, err_pct=100 * (pr / (A.loc[2010, col] / A.loc[2005, col]) - 1)))
    rob['path_2008_fy2010_by_series'] = pd.DataFrame(u).round(2).to_dict('records')
    RA = reask(); RA.to_csv(os.path.join(RES, 'D_reask_gdp_intensity.csv'), index=False)
    RV = RA.drop_duplicates('vintage', keep='first')
    reask_counts = dict(n_rows=len(RA), n_vintages=int(RA.vintage.nunique()),
                        gdp_positive_vintages=int(RA.groupby('vintage').err_gdp.min().gt(0).sum()),
                        intensity_negative_rows=int((RA.err_intensity < 0).sum()),
                        gdp_err_by_vintage=RA.groupby('vintage').err_gdp.first().round(2).to_dict())
    out = dict(H=H, robust=rob, n_path_points=len(D), reask_counts=reask_counts,
               target=tgt[['vintage','case','target_year','horizon','proj_growth_pct','act_growth_pct','err_pct']].round(2).to_dict('records'),
               latest=latest[['vintage','case','target_year','year','horizon','proj_growth_pct','act_growth_pct','err_pct']].round(2).to_dict('records'),
               reask=RA.round(2).to_dict('records'))
    json.dump(out, open(os.path.join(RES, 'main.json'), 'w'), ensure_ascii=False, indent=1, default=float)
    pd.set_option('display.width', 200)
    print(tgt[['vintage','case','target_year','horizon','proj_growth_pct','act_growth_pct','err_pct']].round(1).to_string())
    print(latest[['vintage','case','target_year','year','horizon','proj_growth_pct','act_growth_pct','err_pct']].round(1).to_string())
    print(json.dumps(H, ensure_ascii=False, indent=1, default=float))
    print(json.dumps({k: (v if k != 'R3_per_year' else {kk: vv for kk, vv in v.items() if kk != 'per_year'}) for k, v in rob.items()}, ensure_ascii=False, indent=1, default=float)[:3000])
    print(RA.round(1).to_string()); print(reask_counts)
    print(json.dumps({k: rob[k] for k in ['R7_utility_splice2010','R7_hyp','R6_utility_sales','R5_utility_to_2009','path_2008','path_2008_fy2010_by_series']}, ensure_ascii=False, default=float)[:3000])
if __name__ == '__main__':
    main()
