"""03：繰り返し売買法（Bailey–Muth–Nourse／Case–Shiller の3段階）とヘドニック法で価格指数を作り、比べる"""
from common import *
import statsmodels.formula.api as smf
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr
import importlib
P = importlib.import_module('02_pairs')
rng = np.random.default_rng(56)

d, log = load()
QS = sorted(d.year_q.unique()); T = len(QS)
YR = np.array([int(q[:4]) for q in QS])
F = "lppm2 ~ C(year_q) + C(muni) + age + I(age**2) + larea + I(larea**2) + walk + I(walk**2) + C(struct) + renov"


def hedonic(x):
    m = smf.ols(F, x).fit()
    c = np.array([m.params.get(f"C(year_q)[T.{q}]", 0.0) for q in QS])
    return c, m


def rs_index(p, weighted=True, adj=None):
    """繰り返し売買法。戻り値は log 指数（最初の四半期＝0）"""
    y = p.dlp.values.copy()
    if adj is not None: y = y - adj
    n = len(p)
    rows = np.r_[np.arange(n), np.arange(n)]
    cols = np.r_[p.q2.values, p.q1.values]
    vals = np.r_[np.ones(n), -np.ones(n)]
    keep = cols > 0                                   # 最初の四半期は基準（0）
    X = csr_matrix((vals[keep], (rows[keep], cols[keep] - 1)), shape=(n, T - 1))
    b = lsqr(X, y, atol=1e-10, btol=1e-10)[0]
    if weighted:                                       # Case–Shiller：残差の2乗を間隔で説明し、その逆数で重み付け
        e2 = (y - X @ b) ** 2
        A = np.c_[np.ones(n), p.gap.values]
        g = np.linalg.lstsq(A, e2, rcond=None)[0]
        v = np.clip(A @ g, np.percentile(e2, 5) + 1e-6, None)
        w = 1 / np.sqrt(v)
        from scipy.sparse import diags
        b = lsqr(diags(w) @ X, y * w, atol=1e-10, btol=1e-10)[0]
    return np.r_[0.0, b]


def yearly(li):
    """四半期の log 指数 → 年平均の指数（2015年＝100）"""
    s = pd.Series(np.exp(li), index=YR).groupby(level=0).mean()
    return s / s.iloc[0] * 100


def chg(li, a=2015, b=2025):
    y = yearly(li); return (y[b] / y[a] - 1) * 100


if __name__ == '__main__':
    ps = P.make_pairs(d, P.KEY_STRICT)
    pb = P.make_pairs(d, P.KEY_BUILDING)
    # --- ヘドニック（全取引と、ペアに入った取引だけ）
    h_all, mh = hedonic(d)
    ba, ba2 = mh.params['age'], mh.params['I(age ** 2)']
    bl, bl2 = mh.params['larea'], mh.params['I(larea ** 2)']
    ps['k'] = ps.k.astype(str)
    d['k'] = d[P.KEY_STRICT].astype(str).agg('|'.join, axis=1)
    inpair = d.k.isin(set(ps.k))
    h_pair, _ = hedonic(d[inpair])
    med = d.groupby('year_q').ppm2.median(); m_med = np.log(med.values / med.values[0])
    # --- 繰り返し売買
    agef = lambda a: ba * a + ba2 * a ** 2
    adj_age = agef(ps.age2.values) - agef(ps.age1.values)
    rs_cs = rs_index(ps)
    rs_bmn = rs_index(ps, weighted=False)
    rs_ageadj = rs_index(ps, adj=adj_age)
    # ブートストラップ（キーごとに取り直し、200回）
    keys = ps.k.unique(); grp = ps.groupby('k').indices
    B = []
    for i in range(200):
        kk = rng.choice(keys, len(keys), replace=True)
        idx = np.concatenate([grp[k] for k in kk])
        B.append(rs_index(ps.iloc[idx].reset_index(drop=True)))
    B = np.array(B)
    lo, hi = np.percentile(B, [2.5, 97.5], axis=0)
    idx = pd.DataFrame({'quarter': QS, 'hedonic_all': np.exp(h_all) * 100, 'hedonic_pairsample': np.exp(h_pair) * 100,
                        'median': np.exp(m_med) * 100, 'rs_cs': np.exp(rs_cs) * 100, 'rs_cs_lo': np.exp(lo) * 100,
                        'rs_cs_hi': np.exp(hi) * 100, 'rs_bmn': np.exp(rs_bmn) * 100, 'rs_ageadj': np.exp(rs_ageadj) * 100,
                        'n_trans': d.groupby('year_q').size().values,
                        'n_pairs_end': np.bincount(ps.q2, minlength=T), 'n_pairs_start': np.bincount(ps.q1, minlength=T)})
    idx.round(3).to_csv(RES / 'index_quarterly.csv', index=False, encoding='utf-8-sig')
    yy = pd.DataFrame({k: yearly(v) for k, v in [('hedonic_all', h_all), ('hedonic_pairsample', h_pair), ('median', m_med),
                                                  ('rs_cs', rs_cs), ('rs_bmn', rs_bmn), ('rs_ageadj', rs_ageadj)]})
    yy.round(2).to_csv(RES / 'index_yearly.csv', encoding='utf-8-sig')
    dq = lambda v: np.diff(v)
    s = {'n_trans': len(d), 'n_keys_strict': d.k.nunique(), 'n_pairs_strict': len(ps), 'n_pair_keys': ps.k.nunique(),
         'share_trans_in_pairs': inpair.mean() * 100, 'n_pairs_building': len(pb),
         'gap_median_q': ps.gap.median(), 'gap_mean_q': ps.gap.mean(), 'share_gap_le4': (ps.gap <= 4).mean() * 100,
         'renov_change_share': (ps.ren1 != ps.ren2).mean() * 100,
         'chg_hed_all': chg(h_all), 'chg_hed_pair': chg(h_pair), 'chg_median': chg(m_med), 'chg_rs_cs': chg(rs_cs),
         'chg_rs_cs_lo': np.percentile([chg(b) for b in B], 2.5), 'chg_rs_cs_hi': np.percentile([chg(b) for b in B], 97.5),
         'chg_rs_bmn': chg(rs_bmn), 'chg_rs_ageadj': chg(rs_ageadj),
         'chg2020_25_hed': chg(h_all, 2020, 2025), 'chg2020_25_rs': chg(rs_cs, 2020, 2025), 'chg2020_25_rsadj': chg(rs_ageadj, 2020, 2025),
         'corr_dq_rs_hed': np.corrcoef(dq(rs_cs), dq(h_all))[0, 1], 'corr_dq_rsadj_hed': np.corrcoef(dq(rs_ageadj), dq(h_all))[0, 1],
         'sd_dq_hed': np.std(dq(h_all)) * 100, 'sd_dq_rs': np.std(dq(rs_cs)) * 100, 'sd_dq_med': np.std(dq(m_med)) * 100,
         'ann_age_effect_pct': (np.exp(np.mean(adj_age / (ps.gap.values / 4))) - 1) * 100,
         'b_age': ba, 'b_age2': ba2,
         'pair_age1_mean': ps.age1.mean(), 'all_age_mean': d.age.mean(), 'pair_area_mean': ps.area.mean(), 'all_area_mean': d.area.mean(),
         'pair_23share': ps.ward23.mean() * 100, 'all_23share': d.ward23.mean() * 100,
         'pair_walk_mean': ps.walk.mean(), 'all_walk_mean': d.walk.mean()}
    # --- 改定：2020年末までのデータだけで作った指数と、全期間で作った指数の2015〜2020年の差
    q2020 = QS.index('2020Q4')
    ps20 = ps[ps.q2 <= q2020]
    rs20 = rs_index_sub = None
    yv = ps20.dlp.values; n = len(ps20)
    rows = np.r_[np.arange(n), np.arange(n)]; cols = np.r_[ps20.q2.values, ps20.q1.values]; vals = np.r_[np.ones(n), -np.ones(n)]
    keep = cols > 0
    X = csr_matrix((vals[keep], (rows[keep], cols[keep] - 1)), shape=(n, q2020))
    b20 = np.r_[0, lsqr(X, yv, atol=1e-10, btol=1e-10)[0]]
    full_b = rs_bmn[:q2020 + 1]
    rev_rs = np.abs(np.exp(full_b - b20) - 1) * 100
    h20, _ = hedonic(d[d.q <= pd.Period('2020Q4', 'Q')])
    rev_h = np.abs(np.exp(h_all[:q2020 + 1] - h20[:q2020 + 1]) - 1) * 100
    s['revision_rs_mean'] = rev_rs[1:].mean(); s['revision_rs_max'] = rev_rs.max()
    s['revision_hed_mean'] = rev_h[1:].mean(); s['revision_hed_max'] = rev_h.max()
    pd.DataFrame({'quarter': QS[:q2020 + 1], 'rs_upto2020': np.exp(b20) * 100, 'rs_full': np.exp(full_b) * 100,
                  'hed_upto2020': np.exp(h20[:q2020 + 1]) * 100, 'hed_full': np.exp(h_all[:q2020 + 1]) * 100}).round(3)\
        .to_csv(RES / 'revision_2020.csv', index=False, encoding='utf-8-sig')
    # --- 頑健性（2015→2025年の上昇率）
    rb = {}
    rb['基本（CS 重み、同じ建物・間取り・面積）'] = chg(rs_cs)
    rb['重みなし（BMN）'] = chg(rs_bmn)
    rb['築年の効果を差し引く'] = chg(rs_ageadj)
    pr = ps[ps.ren1 == ps.ren2]; rb['改装の有無が変わったペアを除く'] = chg(rs_index(pr))
    pg = ps[ps.gap >= 4]; rb['1年未満の転売を除く'] = chg(rs_index(pg))
    pn = ps[ps.age1 >= 3]; rb['築3年未満の売り出しを除く'] = chg(rs_index(pn))
    pbx = pb.copy(); adj_area = bl * (pbx.larea2 - pbx.larea1) + bl2 * (pbx.larea2 ** 2 - pbx.larea1 ** 2)
    rb['同じ建物（面積の違いをヘドニックで補正）'] = chg(rs_index(pbx, adj=adj_area.values))
    p23 = ps[ps.ward23]; rb['23区だけ'] = chg(rs_index(p23)); rb['23区以外だけ'] = chg(rs_index(ps[~ps.ward23]))
    h23, _ = hedonic(d[d.ward23]); hno, _ = hedonic(d[~d.ward23])
    rb['（参考）ヘドニック 23区'] = chg(h23); rb['（参考）ヘドニック 23区以外'] = chg(hno)
    rb['（参考）ヘドニック 全取引'] = chg(h_all); rb['（参考）単純な中央値'] = chg(m_med)
    pd.Series(rb).round(2).to_csv(RES / 'robustness.csv', header=['chg_2015_2025_pct'], encoding='utf-8-sig')
    pd.Series(s).to_csv(RES / 'summary.csv', header=['value'], encoding='utf-8-sig')
    # 間隔の分布・ペアの特徴
    ps.gap.value_counts().sort_index().to_csv(RES / 'gap_dist.csv', header=['pairs'])
    print(pd.Series(s).round(3).to_string()); print(pd.Series(rb).round(1).to_string())
    np.save(RES / '_boot.npy', B)
