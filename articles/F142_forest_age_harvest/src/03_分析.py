# 齢級のコホート推移・主伐期の割合・蓄積の増え方と伐採量の比較
import pandas as pd, numpy as np, json
from pathlib import Path
B = Path(__file__).resolve().parents[1]
D, OUT = B / 'data', B / 'results'
OUT.mkdir(exist_ok=True)
np.random.seed(142)
f = pd.read_csv(D / 'forest_age_class.csv')
wd = pd.read_csv(D / 'log_production_national.csv').set_index('year')
pp = pd.read_csv(D / 'log_production_pref.csv')
YRS = [2007, 2012, 2017, 2022]
WIN = {2012: range(2007, 2012), 2017: range(2012, 2017), 2022: range(2017, 2022)}  # 3月末の時点の間の5暦年（おおよそ）
CONV = 0.7  # 素材の量 ÷ 立木の量（利用率、仮定）。頑健性で 0.6・0.8・1.0
res = {}

def tab(kind, sp, pref='全国'):
    return f[(f.kind == kind) & (f.species == sp) & (f.pref == pref)].pivot(index='age_class', columns='year', values='value').reindex(range(1, 20)).fillna(0)

# A 主伐期（既定：11齢級以上＝51年生以上）の割合
A = {}
for sp in ['人工林計', 'スギ', 'ヒノキ', 'カラマツ', '人工林計_民有林', '人工林計_国有林']:
    t = tab('area_ha', sp)
    for th in [10, 11, 12]:
        A[f'{sp}|{th}'] = (t.loc[th:].sum() / t.sum()).round(4).to_dict()
res['share_mature'] = A
ta = tab('area_ha', '人工林計')
res['area_total_ha'] = ta.sum().round(0).to_dict()
res['area_ge11_ha'] = ta.loc[11:].sum().round(0).to_dict()
res['area_le4_ha'] = ta.loc[:4].sum().round(0).to_dict()

# B コホートの残り方：k齢級(t) → k+1齢級(t+5)。19は「19以上」
def cohort(t):
    rows = []
    for a, b in [(2007, 2012), (2012, 2017), (2017, 2022)]:
        for k in range(1, 19):
            before = t.loc[k, a] + (t.loc[19, a] if k == 18 else 0)
            after = t.loc[k + 1, b]
            rows.append(dict(period=f'{a}-{b}', k=k, before=before, after=after, ratio=after / before if before else np.nan))
    return pd.DataFrame(rows)
cb = cohort(ta)
cb.to_csv(OUT / 'cohort_ratio_planted.csv', index=False)
summ = []
for per, g in cb.groupby('period'):
    a, b = map(int, per.split('-'))
    loss_mature = (g.loc[g.k >= 10, 'before'] - g.loc[g.k >= 10, 'after']).sum()  # 10齢級以上(t) から減った面積
    loss_all = (g.before - g.after).sum()
    new1 = ta.loc[1, b]
    summ.append(dict(period=per, loss_k10plus_ha=loss_mature, loss_all_ha=loss_all, new_age1_ha=new1,
                     replant_ratio=new1 / loss_all if loss_all > 0 else np.nan,
                     replant_ratio_adj=new1 * g.loc[g.k == 1, 'ratio'].iloc[0] / loss_all,  # 1齢級の遅れた登録（1→2齢級の比）で補正
                     mature_cut_rate_per_yr=(g.loc[g.k >= 10, 'before'].sum() - g.loc[g.k >= 10, 'after'].sum()) / g.loc[g.k >= 10, 'before'].sum() / 5,
                     total_change_ha=ta[b].sum() - ta[a].sum(),
                     ratio_k10plus=g.loc[g.k >= 10, 'after'].sum() / g.loc[g.k >= 10, 'before'].sum(),
                     ratio_k1_9=g.loc[g.k <= 9, 'after'].sum() / g.loc[g.k <= 9, 'before'].sum()))
cs = pd.DataFrame(summ)
cs.to_csv(OUT / 'cohort_summary_planted.csv', index=False)
res['cohort_summary'] = cs.round(4).to_dict(orient='records')

# C 蓄積の増え方と伐採量（全国、千m3/年）
def stock_vs_harvest(sp_stock, harvest_cols, conv=CONV, pref='全国'):
    s = f[(f.kind == 'stock_m3') & (f.species == sp_stock) & (f.pref == pref)].groupby('year').value.sum()
    rows = []
    for b, yrs in WIN.items():
        a = b - 5
        dS = (s[b] - s[a]) / 5
        h = wd.loc[list(yrs), harvest_cols].sum(axis=1).mean()
        hr = h / conv
        rows.append(dict(period=f'{a}-{b}', stock_start=s[a], stock_end=s[b], d_stock_per_yr=dS, log_per_yr=h,
                         harvest_standing_per_yr=hr, gross_growth_per_yr=dS + hr, harvest_share=hr / (dS + hr)))
    return pd.DataFrame(rows)
C = stock_vs_harvest('人工林計', ['conifer'])
C.to_csv(OUT / 'stock_vs_harvest_planted.csv', index=False)
res['stock_vs_harvest'] = C.round(4).to_dict(orient='records')
spmap = {'スギ': ['sugi'], 'ヒノキ': ['hinoki'], 'カラマツ': ['karamatsu']}
Csp = pd.concat([stock_vs_harvest(sp, cols).assign(species=sp) for sp, cols in spmap.items()])
Csp.to_csv(OUT / 'stock_vs_harvest_species.csv', index=False)
res['stock_vs_harvest_species'] = Csp.round(4).to_dict(orient='records')

# D 頑健性
rob = []
for conv in [0.6, 0.7, 0.8, 1.0]:
    for cols, lab in [(['conifer'], '針葉樹計'), (['sugi', 'hinoki', 'karamatsu'], 'スギ・ヒノキ・カラマツ'), (['total'], '広葉樹を含む計')]:
        c = stock_vs_harvest('人工林計', cols, conv)
        rob.append(dict(conv=conv, harvest=lab, **{p: round(v, 4) for p, v in zip(c.period, c.harvest_share)}))
rob = pd.DataFrame(rob)
rob.to_csv(OUT / 'robustness_harvest_share.csv', index=False)
res['robust_harvest_share'] = rob.to_dict(orient='records')
# 民有林・国有林でのコホート
own = {}
for sp in ['人工林計_民有林', '人工林計_国有林', 'スギ', 'ヒノキ', 'カラマツ']:
    g = cohort(tab('area_ha', sp))
    own[sp] = {per: dict(r10=round(x.loc[x.k >= 10, 'after'].sum() / x.loc[x.k >= 10, 'before'].sum(), 4),
                         r1_9=round(x.loc[x.k <= 9, 'after'].sum() / x.loc[x.k <= 9, 'before'].sum(), 4))
               for per, x in g.groupby('period')}
res['cohort_by_group'] = own

# E 見通し：2017→2022 の残り方と新しい1齢級の面積が続くとしたとき
t = ta[2022].copy()
r = cb[cb.period == '2017-2022'].set_index('k').ratio
proj = {2022: t.copy()}
for y in [2027, 2032, 2037]:
    n = pd.Series(0.0, index=range(1, 20))
    n[1] = ta.loc[1, 2022]
    for k in range(1, 18): n[k + 1] = t[k] * r[k]
    n[19] = (t[18] + t[19]) * r[18]
    proj[y] = n; t = n
P = pd.DataFrame(proj)
P.to_csv(OUT / 'projection_area.csv')
res['projection_share_ge11'] = {int(y): round(P[y].loc[11:].sum() / P[y].sum(), 4) for y in P}
res['projection_share_ge11_noharvest'] = {}
t = ta[2022].copy()
for y in [2027, 2032, 2037]:
    n = pd.Series(0.0, index=range(1, 20)); n[1] = ta.loc[1, 2022]
    for k in range(1, 18): n[k + 1] = t[k]
    n[19] = t[18] + t[19]; t = n
    res['projection_share_ge11_noharvest'][y] = round(n.loc[11:].sum() / n.sum(), 4)

# F 都道府県：人工林の蓄積の増え（2017→2022）と針葉樹の素材生産量（2019年、頑健性：2019と2024の平均）
s = f[(f.kind == 'stock_m3') & (f.species == '人工林計') & (f.pref != '全国')].groupby(['pref', 'year']).value.sum().unstack()
ar = f[(f.kind == 'area_ha') & (f.species == '人工林計') & (f.pref != '全国')]
mat = ar[ar.age_class >= 11].groupby('pref').apply(lambda g: g[g.year == 2022].value.sum()) / ar[ar.year == 2022].groupby('pref').value.sum()
pp['pref2'] = pp.pref.str.replace('全国', '全国')
def tofull(n):
    for full in s.index:
        if full.startswith(n) and len(full) - len(n) <= 1: return full
    return None
pp['pref_full'] = pp.pref.map(tofull)
h19 = pp[pp.year == 2019].set_index('pref_full').conifer
h1924 = pp[pp.year.isin([2019, 2024])].groupby('pref_full').conifer.mean()
PF = pd.DataFrame({'d_stock_per_yr': (s[2022] - s[2017]) / 5, 'stock_2022': s[2022], 'log_2019': h19, 'log_19_24': h1924, 'share_ge11': mat}).dropna()
PF['harvest_share'] = (PF.log_2019 / CONV) / (PF.d_stock_per_yr + PF.log_2019 / CONV)
PF['harvest_share_1924'] = (PF.log_19_24 / CONV) / (PF.d_stock_per_yr + PF.log_19_24 / CONV)
REG = {'北海道': '北海道', '東北': '青森県 岩手県 宮城県 秋田県 山形県 福島県', '関東': '茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県',
       '中部': '新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県', '近畿': '三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県',
       '中国': '鳥取県 島根県 岡山県 広島県 山口県', '四国': '徳島県 香川県 愛媛県 高知県', '九州・沖縄': '福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'}
rmap = {p: r for r, ps in REG.items() for p in ps.split()}
PF['region'] = PF.index.map(rmap)
PF.to_csv(OUT / 'prefecture_stock_harvest.csv')
G = PF.groupby('region').agg(d_stock=('d_stock_per_yr', 'sum'), log19=('log_2019', 'sum'), log1924=('log_19_24', 'sum'))
G['harvest_share'] = (G.log19 / CONV) / (G.d_stock + G.log19 / CONV)
G['harvest_share_1924'] = (G.log1924 / CONV) / (G.d_stock + G.log1924 / CONV)
G.to_csv(OUT / 'region_stock_harvest.csv')
res['region_harvest_share'] = G.harvest_share.round(4).to_dict()
res['region_harvest_share_1924'] = G.harvest_share_1924.round(4).to_dict()
q = PF.harvest_share.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(4).to_dict()
res['pref_harvest_share_quantiles'] = q
from scipy.stats import spearmanr
rho = spearmanr(PF.share_ge11, PF.harvest_share)
bs = []
idx = np.arange(len(PF))
for _ in range(2000):
    i = np.random.choice(idx, len(idx))
    bs.append(spearmanr(PF.share_ge11.values[i], PF.harvest_share.values[i]).correlation)
res['pref_rho_mature_vs_harvestshare'] = dict(rho=round(rho.correlation, 3), p=round(rho.pvalue, 4), ci=[round(np.nanpercentile(bs, 2.5), 3), round(np.nanpercentile(bs, 97.5), 3)], n=len(PF))
res['pref_rho_1924'] = round(spearmanr(PF.share_ge11, PF.harvest_share_1924).correlation, 3)
res['pref_n_neg_dstock'] = int((PF.d_stock_per_yr < 0).sum())
res['log_by_year'] = wd[['total', 'conifer', 'sugi', 'hinoki', 'karamatsu']].to_dict(orient='index')
json.dump(res, open(OUT / 'summary.json', 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in res.items() if k != 'log_by_year'}, ensure_ascii=False, indent=1, default=float)[:9000])
