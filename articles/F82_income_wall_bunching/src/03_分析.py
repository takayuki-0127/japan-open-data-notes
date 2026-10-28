"""「年収の壁」の手前（50～149万円）に、どれくらいの人が集まっているかを集積（bunching）分析で測る。
集計表は所得が50万円刻み（300万円からは100万円刻み）なので、壁（103万・106万・130万円）の前後を細かく分けられない。
そこで「50～149万円の2つの階級」を集積の窓とし、窓の外の階級に当てはめた滑らかな分布（反実仮想）との差を数える。"""
import json, pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / 'data' / 'shugyo_long.csv')
RES = ROOT / 'results'; RES.mkdir(exist_ok=True)
BINS = ['0-49', '50-99', '100-149', '150-199', '200-249', '250-299', '300-399', '400-499']
LO = np.array([0, 50, 100, 150, 200, 250, 300, 400]); HI = np.array([50, 100, 150, 200, 250, 300, 400, 500])
W = HI - LO; MID = (LO + HI) / 2
WIN = np.array([b in ('50-99', '100-149') for b in BINS])
AGES_CORE = [f'{a}歳' for a in ['25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59']]

def dist(year, sex, married, adjust='総数', emp='総数', ages=None):
    s = df[(df.year == year) & (df.sex == sex) & (df.adjust == adjust) & (df.emp == emp)]
    if ages is None: s = s[s.age == '総数']
    else: s = s[s.age.isin(ages)]
    if married == '配偶者なし':
        a = s[s.married == '総数'].groupby('income').n.sum(); b = s[s.married == '配偶者あり'].groupby('income').n.sum()
        g = a - b
    else:
        g = s[s.married == married].groupby('income').n.sum()
    return g.reindex(BINS).fillna(0).values.astype(float)

def bunch(counts, deg=2, log=True, win=WIN):
    dens = counts / W
    x = MID[~win]; y = dens[~win]
    if log:
        ok = y > 0
        c = np.polyfit(x[ok], np.log(y[ok]), deg); pred = np.exp(np.polyval(c, MID))
    else:
        c = np.polyfit(x, y, deg); pred = np.clip(np.polyval(c, MID), 0, None)
    pc = pred * W
    excess = counts[win].sum() - pc[win].sum()
    return dict(actual_window=float(counts[win].sum()), cf_window=float(pc[win].sum()), excess=float(excess),
                b=float(excess / pc[win].sum()), share_window=float(counts[win].sum() / counts.sum()),
                pred=pc.tolist(), counts=counts.tolist())

def bunch_cmp(counts, comp, win=WIN):
    """比較グループの分布の形を、窓の外の人数に合わせて拡大縮小したものを反実仮想にする。"""
    k = counts[~win].sum() / comp[~win].sum(); pc = comp * k
    excess = counts[win].sum() - pc[win].sum()
    return dict(excess=float(excess), b=float(excess / pc[win].sum()), pred=pc.tolist())

out = {}
groups = {'有配偶の女性': ('女', '配偶者あり'), '配偶者のいない女性': ('女', '配偶者なし'),
          '有配偶の男性': ('男', '配偶者あり'), '配偶者のいない男性': ('男', '配偶者なし')}
main = {}
for y in (2017, 2022):
    for g, (s, m) in groups.items():
        c = dist(y, s, m); r = bunch(c); main[f'{y}_{g}'] = r
out['main'] = main

# 就業調整をしている人の割合（所得階級別）
adjshare = {}
for y in (2017, 2022):
    for g, (s, m) in groups.items():
        t = dist(y, s, m); a = dist(y, s, m, adjust='就業調整をしている')
        adjshare[f'{y}_{g}'] = (a / np.where(t > 0, t, np.nan)).tolist()
out['adjust_share'] = adjshare

# 比較グループを反実仮想にする（有配偶女性）
cmpres = {}
for y in (2017, 2022):
    c = dist(y, '女', '配偶者あり')
    cmpres[f'{y}_就業調整していない有配偶女性'] = bunch_cmp(c, dist(y, '女', '配偶者あり', adjust='就業調整をしていない'))
    cmpres[f'{y}_配偶者のいない女性'] = bunch_cmp(c, dist(y, '女', '配偶者なし'))
    cmpres[f'{y}_有配偶の男性'] = bunch_cmp(c, dist(y, '男', '配偶者あり'))
out['comparison_cf'] = cmpres

# 就業調整の有無で分けた所得分布（有配偶女性）
out['by_adjust'] = {f'{y}_{a}': dist(y, '女', '配偶者あり', adjust=a).tolist()
                    for y in (2017, 2022) for a in ['就業調整をしている', '就業調整をしていない']}

# 2022 雇用形態別（有配偶女性）
emp = {}
for e in ['パート', 'アルバイト', '契約社員', '労働者派遣事業所の派遣社員']:
    c = dist(2022, '女', '配偶者あり', emp=e)
    if c.sum() > 0: emp[e] = bunch(c) | dict(total=float(c.sum()))
out['by_emp_2022'] = emp

# 年齢別（2022 有配偶女性、就業調整をしている割合と窓の割合）
ages = sorted(df[(df.year == 2022) & (df.age != '総数')].age.unique())
agetab = []
for a in ages:
    t = dist(2022, '女', '配偶者あり', ages=[a]); ad = dist(2022, '女', '配偶者あり', adjust='就業調整をしている', ages=[a])
    if t.sum() < 20000: continue
    agetab.append(dict(age=a, total=float(t.sum()), adjust_share=float(ad.sum() / t.sum()), window_share=float(t[WIN].sum() / t.sum())))
out['by_age_2022'] = agetab

# 頑健性
rob = []
for y in (2017, 2022):
    c = dist(y, '女', '配偶者あり')
    for deg in (1, 2, 3):
        for lg in (True, False):
            r = bunch(c, deg=deg, log=lg); rob.append(dict(year=y, spec=f'{"対数" if lg else "そのまま"}の密度・{deg}次', b=r['b'], excess=r['excess']))
    # 窓を50～99万円だけにする
    w2 = np.array([b == '50-99' for b in BINS]); r = bunch(c, win=w2)
    rob.append(dict(year=y, spec='窓を50～99万円だけ', b=r['b'], excess=r['excess']))
    # 25～59歳に限る
    r = bunch(dist(y, '女', '配偶者あり', ages=AGES_CORE)); rob.append(dict(year=y, spec='25～59歳に限る', b=r['b'], excess=r['excess']))
    # 100万円刻みにまとめる（0-99,100-199,200-299,300-399,400-499）。窓は0～199万円、窓の外の3点に対数の1次を当てはめる
    c2 = np.array([c[0] + c[1], c[2] + c[3], c[4] + c[5], c[6], c[7]])
    mid2 = np.array([50, 150, 250, 350, 450]); w2b = np.array([True, True, False, False, False])
    co = np.polyfit(mid2[~w2b], np.log(c2[~w2b] / 100), 1); pc = np.exp(np.polyval(co, mid2)) * 100
    rob.append(dict(year=y, spec='100万円刻み（窓0～199万円、窓の外は3点）', b=float((c2[w2b].sum() - pc[w2b].sum()) / pc[w2b].sum()), excess=float(c2[w2b].sum() - pc[w2b].sum())))
out['robust'] = rob
# 比較: 他のグループの b
json.dump(out, open(RES / 'summary.json', 'w'), ensure_ascii=False, indent=1)
pd.DataFrame(rob).to_csv(RES / 'robustness.csv', index=False)
pd.DataFrame([dict(key=k, **{kk: v for kk, v in r.items() if kk not in ('pred', 'counts')}) for k, r in main.items()]).to_csv(RES / 'bunching_main.csv', index=False)
pd.DataFrame(agetab).to_csv(RES / 'by_age_2022.csv', index=False)
for k, r in main.items(): print(k, round(r['b'], 2), int(r['excess']), round(r['share_window'], 3))
for k, r in cmpres.items(): print('cmp', k, round(r['b'], 2), int(r['excess']))
for k, r in emp.items(): print('emp', k, round(r['b'], 2), int(r['total']), round(r['share_window'], 3))
for r in rob: print(r['year'], r['spec'], round(r['b'], 2), int(r['excess']))
for a in agetab: print(a)
for k, v in adjshare.items(): print(k, [round(x, 2) if x == x else None for x in v])
