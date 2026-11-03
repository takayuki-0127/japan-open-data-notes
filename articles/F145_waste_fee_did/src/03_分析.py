# 03 分析：ごみ処理の有料化（家庭系の可燃ごみ）の前後で、1人1日あたりの生活系ごみは減ったか
# 段階的な差の差（Callaway–Sant'Anna 型、条件なし）を自前で実装。乱数シード固定。
import os, json
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'results'); os.makedirs(RES, exist_ok=True)
rng = np.random.default_rng(0)
B = 499
P = pd.read_csv(os.path.join(ROOT, 'data/panel.csv'), dtype={'code': str})
YEARS = sorted(P.year.unique()); Y0, Y1 = YEARS[0], YEARS[-1]

def cohorts(P, partial_as=0.0, min_pre=2):
    """自治体ごとの有料化の年 g（初めて有料になった年度）。
    条件：最初の年は無料、有料になってから無料に戻らない、前に min_pre 年以上の無料。
    never=最後まで無料。always=最初から有料。その他（戻った・不明）は除外。"""
    out = {}
    for code, d in P.sort_values('year').groupby('code'):
        f = d.fee.replace(0.5, partial_as).values
        yrs = d.year.values
        if len(yrs) != len(YEARS) or np.isnan(f).any():
            out[code] = 'drop'; continue
        if (f == 0).all(): out[code] = 'never'; continue
        if (f == 1).all(): out[code] = 'always'; continue
        if not set(np.unique(f)) <= {0.0, 1.0}: out[code] = 'drop'; continue
        k = int(np.argmax(f == 1))
        if (f[k:] == 1).all() and k >= min_pre: out[code] = int(yrs[k])
        else: out[code] = 'drop'
    return pd.Series(out, name='g')

def wide(P, col, transform=np.log):
    W = P.pivot(index='code', columns='year', values=col)
    W = W.where(W > 0) if transform is np.log else W
    return transform(W) if transform is not None else W

def att_gt(W, G, control='never', base_shift=1, anticip=0):
    """ATT(g,t)。基準年は g-base_shift（共通の基準年）。control='never'（最後まで無料）or 'notyet'（まだ有料化していない）"""
    Y = W.values; yrs = list(W.columns)
    gv = np.array([g if isinstance(g, (int, np.integer)) else (-1 if g == 'never' else -9) for g in G.values])
    res = []
    for g in sorted(set(gv[gv > 0])):
        b = g - base_shift
        if b not in yrs: continue
        ib = yrs.index(b); tr = gv == g
        for it, t in enumerate(yrs):
            if t == b: continue
            if control == 'never': ctrl = gv == -1
            else: ctrl = (gv == -1) | ((gv > max(t, b) + anticip) & (gv != g))
            dt = Y[tr, it] - Y[tr, ib]; dc = Y[ctrl, it] - Y[ctrl, ib]
            if len(dt) == 0 or len(dc) < 5: continue
            res.append((g, t, t - g, dt.mean() - dc.mean(), len(dt), len(dc)))
    return pd.DataFrame(res, columns=['g', 't', 'e', 'att', 'n_t', 'n_c'])

def aggregate(A, emin=-5, emax=5):
    E = A[(A.e >= emin) & (A.e <= emax)]
    ev = (E.att * E.n_t).groupby(E.e).sum() / E.n_t.groupby(E.e).sum(); ev.name = 'att'
    post = A[A.e >= 0]
    overall = np.average(post.att, weights=post.n_t) if len(post) else np.nan
    pre = A[A.e < -1]
    pre_avg = np.average(pre.att, weights=pre.n_t) if len(pre) else np.nan
    return ev, overall, pre_avg

def run(P, col='seikatsu_gpd', transform=np.log, control='never', partial_as=0.0, base_shift=1, sub=None,
        gmin=None, gmax=None, tmax=None, boot=True, label=''):
    Q = P if sub is None else P[P.code.isin(sub)]
    if tmax is not None: Q = Q[Q.year <= tmax]
    global YEARS, Y0, Y1
    YS = YEARS; YEARS = sorted(Q.year.unique()); Y0, Y1 = YEARS[0], YEARS[-1]
    G = cohorts(Q, partial_as=partial_as)
    if gmin is not None or gmax is not None:
        G = G.map(lambda x: x if not isinstance(x, (int, np.integer)) or ((gmin is None or x >= gmin) and (gmax is None or x <= gmax)) else 'drop')
    W = wide(Q, col, transform)
    W = W.loc[W.notna().all(axis=1)]  # 全年度そろう自治体だけ（バランスパネル）
    G = G.reindex(W.index).fillna('drop')
    A = att_gt(W, G, control, base_shift)
    ev, ov, pre = aggregate(A)
    out = dict(label=label, overall=ov, pre_avg=pre, n_treated=int(sum(isinstance(x, (int, np.integer)) for x in G.values)),
               n_never=int((G == 'never').sum()), n_always=int((G == 'always').sum()), n_drop=int((G == 'drop').sum()))
    if boot:
        codes_by = {k: G.index[G.map(lambda x: x == k)] for k in set(G.values) if k not in ('drop', 'always')}
        bov, bev, bpre = [], [], []
        for b in range(B):
            idx = np.concatenate([rng.choice(v, size=len(v), replace=True) for v in codes_by.values()])
            Wb = W.loc[idx].reset_index(drop=True); Wb.index = [f'u{i}' for i in range(len(idx))]
            Gb = pd.Series(G.loc[idx].values, index=Wb.index)
            Ab = att_gt(Wb, Gb, control, base_shift)
            e2, o2, p2 = aggregate(Ab)
            bov.append(o2); bev.append(e2); bpre.append(p2)
        out['ci'] = [float(np.nanpercentile(bov, 2.5)), float(np.nanpercentile(bov, 97.5))]
        out['se'] = float(np.nanstd(bov))
        out['pre_ci'] = [float(np.nanpercentile(bpre, 2.5)), float(np.nanpercentile(bpre, 97.5))]
        EV = pd.concat(bev, axis=1)
        ev = pd.DataFrame(dict(att=ev, lo=EV.quantile(0.025, axis=1), hi=EV.quantile(0.975, axis=1)))
    YEARS = YS; Y0, Y1 = YEARS[0], YEARS[-1]
    return out, ev, A, G

def twfe(P, G, col='seikatsu_gpd'):
    """比較用：普通の二元固定効果（TWFE）の推定値"""
    Q = P.copy(); Q['y'] = np.log(Q[col].where(Q[col] > 0))
    Q = Q[Q.code.isin(G.index[G.map(lambda x: x == 'never' or isinstance(x, (int, np.integer)))])].dropna(subset=['y'])
    gmap = G.to_dict()
    Q['D'] = [1.0 if isinstance(gmap[c], (int, np.integer)) and yr >= gmap[c] else 0.0 for c, yr in zip(Q.code, Q.year)]
    for v in ['y', 'D']:
        Q[v + '_dm'] = Q[v] - Q.groupby('code')[v].transform('mean') - Q.groupby('year')[v].transform('mean') + Q[v].mean()
    beta = (Q.y_dm * Q.D_dm).sum() / (Q.D_dm ** 2).sum()
    e = Q.y_dm - beta * Q.D_dm
    # 自治体クラスタの頑健な標準誤差
    s = (Q.D_dm * e).groupby(Q.code).sum()
    se = np.sqrt((s ** 2).sum()) / (Q.D_dm ** 2).sum()
    return float(beta), float(se)

if __name__ == '__main__':
    R = {}
    main, ev_main, A_main, G_main = run(P, label='主：never-treated 対照、生活系ごみ（集団回収を含む）g/人/日、対数')
    R['main'] = main
    ev_main.to_csv(os.path.join(RES, 'event_main.csv'))
    A_main.to_csv(os.path.join(RES, 'att_gt_main.csv'), index=False)
    G_main.to_csv(os.path.join(RES, 'cohorts.csv'))
    # コホートごとの数と、コホートごとの導入後平均
    cg = A_main[A_main.e >= 0].groupby('g').apply(lambda d: pd.Series(dict(att=np.average(d.att, weights=d.n_t), n=d.n_t.iloc[0])))
    cg.to_csv(os.path.join(RES, 'att_by_cohort.csv'))
    R['by_cohort'] = cg.reset_index().to_dict('records')
    # 記述：有料化の割合の推移
    st = P.groupby('year').fee.apply(lambda s: pd.Series(dict(paid=(s == 1).mean(), partial=(s == 0.5).mean(), free=(s == 0).mean(), na=s.isna().mean()))).unstack()
    st.to_csv(os.path.join(RES, 'fee_share_by_year.csv'))
    R['fee_share'] = st.round(4).reset_index().to_dict('records')
    # 頑健性
    rob = []
    def add(lbl, **kw):
        o, ev, A, G = run(P, label=lbl, **kw)
        rob.append(o); return o, ev
    add('対照を「まだ有料化していない自治体」に', control='notyet')
    add('一部有料も「有料」とみなす', partial_as=1.0)
    G_all = cohorts(P)
    big = P[(P.year == YEARS[0]) & (P['pop'] >= 10000)].code
    add('人口1万人以上の自治体だけ', sub=set(big))
    add('基準年を導入2年前に（前倒しの反応を除く）', base_shift=2)
    add('導入年を2014〜2019年度に限る', gmin=2014, gmax=2019)
    add('コロナ前（2019年度まで）だけ', tmax=2019)
    o_tot, ev_tot = add('結果：1人1日あたりの総排出量（事業系を含む）', col='total_gpd')
    o_rec, ev_rec = add('結果：リサイクル率（%ポイント、対数にしない）', col='recycle', transform=None)
    R['robust'] = rob
    ev_rec.to_csv(os.path.join(RES, 'event_recycle.csv'))
    b, se = twfe(P, G_main)
    R['twfe'] = dict(beta=b, se=se, ci=[b - 1.96 * se, b + 1.96 * se])
    # 水準：導入前年の平均 g/人/日（処置群・対照）
    W = P.pivot(index='code', columns='year', values='seikatsu_gpd')
    tr = [c for c, g in G_main.items() if isinstance(g, (int, np.integer))]
    R['levels'] = dict(
        treated_pre=float(np.mean([W.loc[c, G_main[c] - 1] for c in tr if c in W.index])),
        never_2012=float(W.loc[G_main.index[G_main == 'never']].iloc[:, 0].mean()),
        always_2012=float(W.loc[G_main.index[G_main == 'always']].iloc[:, 0].mean()),
        nat_2012=float(np.average(P[P.year == YEARS[0]].seikatsu_gpd.dropna(), weights=P[P.year == YEARS[0]].dropna(subset=['seikatsu_gpd'])['pop'])),
        nat_last=float(np.average(P[P.year == YEARS[-1]].seikatsu_gpd.dropna(), weights=P[P.year == YEARS[-1]].dropna(subset=['seikatsu_gpd'])['pop'])),
    )
    json.dump(R, open(os.path.join(RES, 'results.json'), 'w'), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R, ensure_ascii=False, indent=1, default=float)[:6000])
