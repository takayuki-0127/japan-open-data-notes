"""F280 03 分析：1人当たり医療費の伸びを、年齢構成・受診率・1件当たり日数・1日当たり医療費に分ける。

1人当たり医療費 C = Σ_a w_a × [ r_in·d_in·p_in + r_out·d_out·p_out + o ]   （千円）
  w：人口の割合、r：受診率（件/人）、d：1件当たり日数、p：1日当たり医療費（千円）、
  in：入院（食事・生活療養を含む）、out：入院外（調剤を含む）、
  o：その他の種類（歯科・訪問看護・療養費など）＝ 1人当たり医療費計 − 入院 − 入院外
年ごとに LMDI（対数平均ディビジア指数、加法型）で分けて期間で足す。
"""
import os, json, itertools
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '..', 'data', 'processed')
R = os.path.join(HERE, '..', 'results')
FACT = ['age', 'in_r', 'in_d', 'in_p', 'out_r', 'out_d', 'out_p', 'oth']
LAB = {'age': '年齢構成', 'in_r': '入院・受診率', 'in_d': '入院・1件当たり日数', 'in_p': '入院・1日当たり',
       'out_r': '入院外・受診率', 'out_d': '入院外・1件当たり日数', 'out_p': '入院外・1日当たり', 'oth': 'その他の種類'}

def L(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    with np.errstate(divide='ignore', invalid='ignore'):
        out = np.where(np.isclose(a, b), a, (a - b) / (np.log(a) - np.log(b)))
    return out

def prep(d):
    d = d.copy()
    d['w'] = d.pop_k / d.groupby('fy').pop_k.transform('sum')
    d['oth'] = d.cost_man * 10 - d.in_r * d.in_d * d.in_p - d.out_r * d.out_d * d.out_p
    return d

def total(d):
    return (d.w * d.cost_man * 10).groupby(d.fy).sum()

def lmdi_step(a, b):
    """a, b：同じ年齢の並びの2時点（DataFrame）。各要因の寄与（千円）を返す。"""
    res = {k: 0.0 for k in FACT}
    Vin0, Vin1 = a.w * a.in_r * a.in_d * a.in_p, b.w.values * b.in_r.values * b.in_d.values * b.in_p.values
    Vo0, Vo1 = a.w * a.out_r * a.out_d * a.out_p, b.w.values * b.out_r.values * b.out_d.values * b.out_p.values
    Vt0, Vt1 = a.w * a.oth, b.w.values * b.oth.values
    for V0, V1, fs in [(Vin0.values, Vin1, ['in_r', 'in_d', 'in_p']), (Vo0.values, Vo1, ['out_r', 'out_d', 'out_p']),
                       (Vt0.values, Vt1, ['oth'])]:
        Lw = L(V1, V0)
        res['age'] += float(np.sum(Lw * np.log(b.w.values / a.w.values)))
        for f in fs:
            res[f] += float(np.sum(Lw * np.log(b[f].values / a[f].values)))
    return res

def lmdi_chain(d, y0, y1):
    tot = {k: 0.0 for k in FACT}
    yearly = []
    for y in range(y0 + 1, y1 + 1):
        a = d[d.fy == y - 1].sort_values('age_i'); b = d[d.fy == y].sort_values('age_i')
        r = lmdi_step(a, b)
        yearly.append(dict(fy=y, **r))
        for k in FACT:
            tot[k] += r[k]
    return tot, pd.DataFrame(yearly)

def shapley_two_point(d, y0, y1):
    """始めと終わりの2時点で、各項（年齢×種類）ごとに要因のシャープレイ値を出して足す。"""
    a = d[d.fy == y0].sort_values('age_i'); b = d[d.fy == y1].sort_values('age_i')
    tot = {k: 0.0 for k in FACT}
    for kind, fs in [('in', ['in_r', 'in_d', 'in_p']), ('out', ['out_r', 'out_d', 'out_p']), ('oth', ['oth'])]:
        names = ['w'] + fs
        x0 = np.vstack([a[n].values for n in names]); x1 = np.vstack([b[n].values for n in names])
        m = len(names)
        phi = np.zeros((m, x0.shape[1]))
        for perm in itertools.permutations(range(m)):
            cur = x0.copy()
            prev = np.prod(cur, axis=0)
            for j in perm:
                cur[j] = x1[j]
                now = np.prod(cur, axis=0)
                phi[j] += now - prev
                prev = now
        import math; phi /= math.factorial(m)
        for j, n in enumerate(names):
            tot['age' if n == 'w' else n] += float(phi[j].sum())
    return tot

def to10(d):
    """10歳階級にまとめる（0-9, …, 90-99, 100+）。"""
    d = d.copy()
    d['g'] = d.age_i.map(lambda i: min(i // 2, 10))
    rows = []
    for (y, g), s in d.groupby(['fy', 'g']):
        W = s.w.sum()
        row = dict(fy=y, age_i=g, w=W, pop_k=s.pop_k.sum())
        for k in ['in', 'out']:
            R_ = (s.w * s[f'{k}_r']).sum() / W
            D_ = (s.w * s[f'{k}_r'] * s[f'{k}_d']).sum() / (s.w * s[f'{k}_r']).sum()
            P_ = (s.w * s[f'{k}_r'] * s[f'{k}_d'] * s[f'{k}_p']).sum() / (s.w * s[f'{k}_r'] * s[f'{k}_d']).sum()
            row.update({f'{k}_r': R_, f'{k}_d': D_, f'{k}_p': P_})
        row['oth'] = (s.w * s.oth).sum() / W
        row['cost_man'] = (s.w * s.cost_man).sum() / W
        rows.append(row)
    return pd.DataFrame(rows)

def summarize(tot, d, y0, y1):
    C = total(d)
    dC = C[y1] - C[y0]
    within_inout = sum(tot[k] for k in ['in_r', 'in_d', 'in_p', 'out_r', 'out_d', 'out_p'])
    p_contrib = tot['in_p'] + tot['out_p']
    return dict(C0=C[y0], C1=C[y1], dC=dC, growth_pct=100 * (C[y1] / C[y0] - 1),
                share_age=tot['age'] / dC, within_inout=within_inout,
                share_p_in_within=p_contrib / within_inout,
                rd_contrib=within_inout - p_contrib,
                contrib={k: tot[k] for k in FACT}, resid=dC - sum(tot.values()))

def divisia_p(d, y0, y1):
    """入院＋入院外の1日当たり医療費の、年齢の重みを固定した伸び（対数×100、年ごとにつなぐ）。"""
    s = 0.0; per = []
    for y in range(y0 + 1, y1 + 1):
        a = d[d.fy == y - 1].sort_values('age_i'); b = d[d.fy == y].sort_values('age_i')
        V0 = np.concatenate([(a.w * a.in_r * a.in_d * a.in_p).values, (a.w * a.out_r * a.out_d * a.out_p).values])
        V1 = np.concatenate([(b.w * b.in_r * b.in_d * b.in_p).values, (b.w * b.out_r * b.out_d * b.out_p).values])
        lr = np.concatenate([np.log(b.in_p.values / a.in_p.values), np.log(b.out_p.values / a.out_p.values)])
        Lw = L(V1, V0)
        g = float(np.sum(Lw * lr) / np.sum(Lw)) * 100
        per.append(dict(fy=y, p_growth_logpct=g)); s += g
    return s, pd.DataFrame(per)


def divisia_generic(d, y0, y1, fn):
    """入院＋入院外で、年齢の重み（LMDI）を使って、fn(行, 種類) の伸びを年ごとにつないだ値（対数×100）。"""
    s = 0.0; per = []
    for y in range(y0 + 1, y1 + 1):
        a = d[d.fy == y - 1].sort_values('age_i'); b = d[d.fy == y].sort_values('age_i')
        V0 = np.concatenate([(a.w * a.in_r * a.in_d * a.in_p).values, (a.w * a.out_r * a.out_d * a.out_p).values])
        V1 = np.concatenate([(b.w * b.in_r * b.in_d * b.in_p).values, (b.w * b.out_r * b.out_d * b.out_p).values])
        lr = np.concatenate([np.log(fn(b, 'in') / fn(a, 'in')), np.log(fn(b, 'out') / fn(a, 'out'))])
        Lw = L(V1, V0)
        g = float(np.sum(Lw * lr) / np.sum(Lw)) * 100
        per.append(dict(fy=y, g=g)); s += g
    return s, pd.DataFrame(per)

def reask(d, rev, y0=2013, y1=2023):
    """問い直し（結果を見てから足した）：1日当たりの伸びは、日数が短くなった分の言い換えか。
    1件当たり医療費（＝1件当たり日数×1日当たり）で見ても、改定の累積を上回るか。入院・入院外べつにも見る。"""
    rs = float(rev[(rev.fy > y0) & (rev.fy <= y1)].revision_pct.sum())
    res = {}
    for name, fn in [('per_day', lambda x, k: x[f'{k}_p'].values),
                     ('per_case', lambda x, k: (x[f'{k}_d'] * x[f'{k}_p']).values),
                     ('days_per_person', lambda x, k: (x[f'{k}_r'] * x[f'{k}_d']).values),
                     ('cases_per_person', lambda x, k: x[f'{k}_r'].values)]:
        g, _ = divisia_generic(d, y0, y1, fn)
        res[name] = g
    for k in ['in', 'out']:
        for name, col in [('per_day', lambda x: x[f'{k}_p'].values), ('per_case', lambda x: (x[f'{k}_d'] * x[f'{k}_p']).values)]:
            s = 0.0
            for y in range(y0 + 1, y1 + 1):
                a = d[d.fy == y - 1].sort_values('age_i'); b = d[d.fy == y].sort_values('age_i')
                V0 = (a.w * a[f'{k}_r'] * a[f'{k}_d'] * a[f'{k}_p']).values; V1 = (b.w * b[f'{k}_r'] * b[f'{k}_d'] * b[f'{k}_p']).values
                Lw = L(V1, V0)
                s += float(np.sum(Lw * np.log(col(b) / col(a))) / np.sum(Lw)) * 100
            res[f'{k}_{name}'] = s
    res['revision_sum_pct'] = rs
    res['per_case_gap'] = res['per_case'] - rs
    return res

def run_all(d, y0, y1):
    tot, yearly = lmdi_chain(d, y0, y1)
    return summarize(tot, d, y0, y1), yearly

def main():
    os.makedirs(R, exist_ok=True)
    raw = pd.read_csv(os.path.join(P, 'panel.csv'))
    ages = list(dict.fromkeys(raw.age))
    raw['age_i'] = raw.age.map({a: i for i, a in enumerate(ages)})
    d = prep(raw)
    rev = pd.read_csv(os.path.join(P, 'revision.csv'))
    out = {}
    # 主：2013→2023
    main_s, yearly = run_all(d, 2013, 2023)
    out['main'] = main_s
    yearly.to_csv(os.path.join(R, 'A_yearly_contrib.csv'), index=False)
    pc, pyear = divisia_p(d, 2013, 2023)
    rv = rev[(rev.fy >= 2014) & (rev.fy <= 2023)]
    out['H4'] = dict(p_growth_logpct=pc, revision_sum_pct=float(rv.revision_pct.sum()),
                     gap=pc - float(rv.revision_pct.sum()))
    pyear = pyear.merge(rev[['fy', 'revision_pct']], on='fy')
    pyear.to_csv(os.path.join(R, 'B_daily_cost_vs_revision.csv'), index=False)
    H = {}
    H['H1'] = dict(value=main_s['share_age'], rule='>=0.40', support=bool(main_s['share_age'] >= 0.40))
    H['H2'] = dict(value=main_s['share_p_in_within'], rule='>1.0', support=bool(main_s['share_p_in_within'] > 1.0))
    H['H3'] = dict(value=main_s['contrib']['in_d'], rule='<0', support=bool(main_s['contrib']['in_d'] < 0))
    H['H4'] = dict(value=out['H4']['gap'], rule='>=10pt', support=bool(out['H4']['gap'] >= 10))
    out['hypotheses'] = H
    # 公表の要因分解との照合（2014〜2023年度の和、%）
    out['official_sum_2014_2023'] = {c: float(rv[c].sum()) for c in ['official_growth_pct', 'official_pop_pct', 'official_aging_pct', 'revision_pct', 'official_other_pct']}
    C = total(d)
    out['C_by_year'] = {int(k): float(v) for k, v in C.items()}
    # 頑健性
    rob = {}
    s, _ = run_all(d, 2013, 2019); rob['R1_end2019'] = s
    pc19, _ = divisia_p(d, 2013, 2019)
    rob['R1_end2019']['H4_gap'] = pc19 - float(rev[(rev.fy >= 2014) & (rev.fy <= 2019)].revision_pct.sum())
    sh = shapley_two_point(d, 2013, 2023); rob['R2_shapley'] = summarize(sh, d, 2013, 2023)
    d10 = to10(d); s, _ = run_all(d10, 2013, 2023); rob['R3_10yr'] = s
    s, _ = run_all(d, 2013, 2022); rob['R7_end2022'] = s
    pc22, _ = divisia_p(d, 2013, 2022)
    rob['R7_end2022']['H4_gap'] = pc22 - float(rev[(rev.fy >= 2014) & (rev.fy <= 2022)].revision_pct.sum())
    rob['R7_end2022']['per_case_gap'] = reask(d, rev, 2013, 2022)['per_case_gap']
    s, _ = run_all(d, 2011, 2023); rob['R4b_start2011'] = s
    pc11, _ = divisia_p(d, 2011, 2023)
    rob['R4b_start2011']['H4_gap'] = pc11 - float(rev[(rev.fy >= 2012) & (rev.fy <= 2023)].revision_pct.sum())
    # R6：公表値の丸めの幅（最後の桁の±半分）で値をずらして1,000回
    rng = np.random.default_rng(280)
    half = {'cost_man': 0.05, 'in_r': 0.005, 'in_d': 0.05, 'in_p': 0.05, 'out_r': 0.05, 'out_d': 0.05, 'out_p': 0.05}
    sims = []
    base = raw.copy()
    for _ in range(1000):
        x = base.copy()
        for c, h in half.items():
            x[c] = x[c] + rng.uniform(-h, h, len(x))
        x['in_r'] = x.in_r.clip(lower=0.004)
        xd = prep(x)
        if (xd.oth <= 0).any():
            xd.loc[xd.oth <= 0, 'oth'] = 0.1
        s, _ = run_all(xd, 2013, 2023)
        pcs, _ = divisia_p(xd, 2013, 2023)
        sims.append(dict(share_age=s['share_age'], share_p=s['share_p_in_within'], in_d=s['contrib']['in_d'],
                         out_d=s['contrib']['out_d'], H4_gap=pcs - out['H4']['revision_sum_pct']))
    sims = pd.DataFrame(sims)
    rob['R6_rounding'] = {c: [float(sims[c].quantile(q)) for q in (0.025, 0.5, 0.975)] for c in sims.columns}
    out['robustness'] = rob
    out['reask'] = reask(d, rev)
    out['reask_end2019'] = reask(d, rev, 2013, 2019)
    # 年齢別の表（2013・2023年度）
    t = d[d.fy.isin([2013, 2023])][['fy', 'age', 'w', 'cost_man', 'in_r', 'in_d', 'in_p', 'out_r', 'out_d', 'out_p', 'oth']]
    t.to_csv(os.path.join(R, 'C_age_2013_2023.csv'), index=False)
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return round(float(o), 6)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    json.dump(clean(out), open(os.path.join(R, 'main.json'), 'w'), ensure_ascii=False, indent=1)
    m = out['main']
    print('C', round(m['C0'], 1), '->', round(m['C1'], 1), 'growth%', round(m['growth_pct'], 2), 'resid', round(m['resid'], 4))
    for k in FACT:
        print(f"  {LAB[k]:　<12} {m['contrib'][k]:8.2f} 千円  {100*m['contrib'][k]/m['dC']:6.1f}%")
    print('H', {k: (round(v['value'], 3), v['support']) for k, v in H.items()})
    print('H4', {k: round(v, 2) for k, v in out['H4'].items()})
    print('official', out['official_sum_2014_2023'])
    print('reask', {k: round(v, 2) for k, v in out['reask'].items()})
    print('reask19', {k: round(v, 2) for k, v in out['reask_end2019'].items()})
    for k, v in rob.items():
        if k == 'R6_rounding':
            print(k, {a: [round(z, 3) for z in b] for a, b in v.items()})
        else:
            print(k, 'age', round(v['share_age'], 3), 'p/within', round(v['share_p_in_within'], 3), 'in_d', round(v['contrib']['in_d'], 2), 'growth', round(v['growth_pct'], 2), 'H4gap', round(v.get('H4_gap', float('nan')), 2))

if __name__ == '__main__':
    main()
