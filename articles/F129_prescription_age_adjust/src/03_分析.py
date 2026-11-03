# F129 03 分析：間接法の年齢調整（標準化処方比）、ばらつきの分解、ファンネルプロットの管理限界、頑健性
import json, pathlib
import numpy as np, pandas as pd
np.random.seed(129)
D = pathlib.Path(__file__).resolve().parent.parent / 'data'
R = pathlib.Path(__file__).resolve().parent.parent / 'results'
R.mkdir(exist_ok=True)
pref = pd.read_csv(D / 'ndb_pref_class.csv', dtype={'pref': str})
sa = pd.read_csv(D / 'ndb_sexage_class.csv')
pop = pd.read_csv(D / 'pop_pref_sex_age.csv', dtype={'pref': str})
pin = pd.read_csv(D / 'ndb_innai_pref_class_2024.csv', dtype={'pref': str})
sain = pd.read_csv(D / 'ndb_innai_sexage_class_2024.csv')
MAIN = 214  # 血圧降下剤
REGION = {**{f'{i:02d}': '北海道・東北' for i in range(1, 8)}, **{f'{i:02d}': '関東' for i in range(8, 15)},
          **{f'{i:02d}': '中部' for i in range(15, 24)}, **{f'{i:02d}': '近畿' for i in range(24, 31)},
          **{f'{i:02d}': '中国・四国' for i in range(31, 40)}, **{f'{i:02d}': '九州・沖縄' for i in range(40, 48)}}

def sr_table(cls, year=2024, metric='tabs', by_sex=True, innai=False, mask_fill=0.0):
    p = pref[(pref.cls == cls) & (pref.year == year)].set_index('pref')
    a = sa[(sa.cls == cls) & (sa.year == year)]
    if innai:
        p2 = pin[pin.cls == cls].set_index('pref'); a2 = sain[sain.cls == cls]
        p = p[[metric, 'n_masked']].add(p2[[metric, 'n_masked']], fill_value=0)
        a = pd.concat([a[['sex', 'age', metric, 'n_masked']], a2[['sex', 'age', metric, 'n_masked']]]).groupby(['sex', 'age'], as_index=False).sum()
    O = p[metric] + mask_fill * p['n_masked']
    a = a.assign(v=a[metric] + mask_fill * a['n_masked'])
    pp = pop[pop.year == year]
    nat = pp[pp.pref == '00']; prf = pp[pp.pref != '00']
    keys = ['sex', 'age'] if by_sex else ['age']
    num = a.groupby(keys).v.sum(); den = nat.groupby(keys)['pop'].sum()
    rate = (num / den).rename('rate')
    E = prf.groupby(['pref'] + keys)['pop'].sum().reset_index().merge(rate.reset_index(), on=keys)
    E = (E['pop'] * E['rate']).groupby(E['pref']).sum()
    P = prf.groupby('pref')['pop'].sum()
    df = pd.DataFrame({'O': O, 'E': E, 'P': P}).dropna()
    df['E'] *= df.O.sum() / df.E.sum()          # 全国で O/E=1 にそろえる（県別表と性年齢別表の秘匿の差を吸収）
    df['crude'] = df.O / df.P / (df.O.sum() / df.P.sum())  # 全国平均=1 の粗い比
    df['SR'] = df.O / df.E
    df['age_ratio'] = df.E / df.P / (df.E.sum() / df.P.sum())  # 年齢構成だけから見込まれる比
    return df

def summarize(df):
    lc, ls, la = np.log(df.crude), np.log(df.SR), np.log(df.age_ratio)
    return dict(crude_maxmin=float(df.crude.max() / df.crude.min()), sr_maxmin=float(df.SR.max() / df.SR.min()),
                crude_cv=float(df.crude.std() / df.crude.mean()), sr_cv=float(df.SR.std() / df.SR.mean()),
                share_explained=float(1 - ls.var() / lc.var()),
                r2_age=float(np.corrcoef(lc, la)[0, 1] ** 2))

def funnel(df, z95=1.96, z998=3.09):
    # (1) ポアソン（数量をそのまま件数とみなす） (2) 加法的ランダム効果（Spiegelhalter 2005、DL推定・10%ウィンズライズ）
    y, E = df.SR.values, df.E.values
    s = 1 / np.sqrt(E)
    zs = (y - 1) / s
    out = {}
    out['poisson_out95'] = int((np.abs(zs) > z95).sum()); out['poisson_out998'] = int((np.abs(zs) > z998).sum())
    lo, hi = np.quantile(zs, [0.1, 0.9]); zw = np.clip(zs, lo, hi)
    phi = float(np.mean(zw ** 2))
    w = 1 / s ** 2
    tau2 = max(0.0, (len(y) * phi - (len(y) - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
    sd = np.sqrt(s ** 2 + tau2)
    zr = (y - 1) / sd
    out.update(phi=phi, tau=float(np.sqrt(tau2)), re_out95=int((np.abs(zr) > z95).sum()), re_out998=int((np.abs(zr) > z998).sum()))
    # (3) 乗法的過分散（Spiegelhalter 2005）
    zm = zs / np.sqrt(phi)
    out.update(mult_out95=int((np.abs(zm) > z95).sum()), mult_out998=int((np.abs(zm) > z998).sum()))
    return out, tau2

res = {}
main = sr_table(MAIN, innai=True)  # 主：院外＋院内（外来）
main['region'] = main.index.map(REGION)
main.to_csv(R / 'sr_main_214_2024.csv')
res['main'] = summarize(main)
fo, tau2 = funnel(main); res['main_funnel'] = fo
res['main_corr_sr_age'] = float(np.corrcoef(main.SR, main.age_ratio)[0, 1])
res['main_corr_crude_age'] = float(np.corrcoef(main.crude, main.age_ratio)[0, 1])
res['main_region_sr'] = main.groupby('region').SR.mean().round(3).to_dict()
res['main_region_crude'] = main.groupby('region').crude.mean().round(3).to_dict()
json.dump({'tau2': tau2}, open(R / 'funnel_tau2.json', 'w'))

# 頑健性
rob = []
def add(name, df):
    s = summarize(df); f, _ = funnel(df)
    rob.append(dict(check=name, **{k: round(v, 4) for k, v in s.items()}, re_out95=f['re_out95'], re_out998=f['re_out998'],
                    corr_with_main=round(float(np.corrcoef(df.SR.reindex(main.index), main.SR)[0, 1]), 4)))
add('主：2024年度・外来（院外＋院内）・錠とカプセルの数・性と年齢', main)
add('指標を薬剤費（数量×薬価）にする', sr_table(MAIN, metric='yen', innai=True))
add('年齢だけで調整（性を分けない）', sr_table(MAIN, by_sex=False, innai=True))
add('秘匿（1000未満）を500とみなす', sr_table(MAIN, mask_fill=500.0, innai=True))
add('院外処方だけ（2024年度）', sr_table(MAIN))
add('院外処方だけ（2023年度・第10回）', sr_table(MAIN, year=2023))
pd.DataFrame(rob).to_csv(R / 'robustness_214.csv', index=False)
res['robustness'] = rob

# 薬効分類ごと（全国の錠・カプセル数の上位25分類）
tot = sa[(sa.year == 2024)].groupby(['cls', 'cname']).tabs.sum().sort_values(ascending=False)
cl = []
for (c, n), v in tot.head(25).items():
    d24 = sr_table(c, innai=True); dy = sr_table(c, metric='yen', innai=True)
    o24 = sr_table(c); d23 = sr_table(c, year=2023)
    s = summarize(d24)
    cl.append(dict(cls=c, cname=n, tabs_2024=float(v), **{k: round(x, 4) for k, x in s.items()},
                   share_explained_outonly=round(summarize(o24)['share_explained'], 4),
                   share_explained_outonly_2023=round(summarize(d23)['share_explained'], 4),
                   share_explained_yen=round(summarize(dy)['share_explained'], 4),
                   sr_corr_2023_2024=round(float(np.corrcoef(o24.SR, d23.SR.reindex(o24.index))[0, 1]), 4),
                   re_out95=funnel(d24)[0]['re_out95']))
cl = pd.DataFrame(cl); cl.to_csv(R / 'by_class_2024.csv', index=False)
res['by_class'] = dict(n=len(cl), median_share=float(cl.share_explained.median()),
                       n_share_over_half=int((cl.share_explained > 0.5).sum()), n_share_negative=int((cl.share_explained < 0).sum()),
                       median_sr_corr_years=float(cl.sr_corr_2023_2024.median()),
                       median_crude_maxmin=float(cl.crude_maxmin.median()), median_sr_maxmin=float(cl.sr_maxmin.median()))
# 年度の比較（主）
d23 = sr_table(MAIN, year=2023); o24 = sr_table(MAIN)
res['main_sr_corr_2023_2024_outonly'] = float(np.corrcoef(o24.SR, d23.SR.reindex(o24.index))[0, 1])
res['outonly_vs_total_sr_corr'] = float(np.corrcoef(o24.SR, main.SR.reindex(o24.index))[0, 1])
pd.DataFrame({'SR2024_out': o24.SR, 'SR2023_out': d23.SR.reindex(o24.index), 'SR2024_total': main.SR}).to_csv(R / 'sr_214_compare.csv')
# 院外の割合（錠・カプセル数）
po = pref[(pref.cls == MAIN) & (pref.year == 2024)].set_index('pref').tabs; pi_ = pin[pin.cls == MAIN].set_index('pref').tabs
share_out = po / (po + pi_)
res['outshare_min_max'] = [float(share_out.min()), float(share_out.max())]
res['corr_outonly_sr_vs_outshare'] = float(np.corrcoef(o24.SR, share_out.reindex(o24.index))[0, 1])
res['corr_total_sr_vs_outshare'] = float(np.corrcoef(main.SR, share_out.reindex(main.index))[0, 1])
share_out.rename('out_share').to_csv(R / 'outshare_214_2024.csv')
# 表どうしの整合（県別合計と性年齢別合計）
chk = []
for y in (2023, 2024):
    a = pref[(pref.cls == MAIN) & (pref.year == y)].tabs.sum(); b = sa[(sa.cls == MAIN) & (sa.year == y)].tabs.sum()
    chk.append(dict(year=y, pref_total=a, sexage_total=b, ratio=a / b))
res['table_consistency'] = chk
res['main_national_tabs_per_capita'] = float(main.O.sum() / main.P.sum())
json.dump(res, open(R / 'summary.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
print(cl[['cls','cname','crude_cv','sr_cv','share_explained','share_explained_outonly','share_explained_outonly_2023','share_explained_yen','sr_corr_2023_2024','re_out95']].to_string())
