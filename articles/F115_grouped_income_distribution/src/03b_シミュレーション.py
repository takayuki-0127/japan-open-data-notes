# F115 03b シミュレーション：答え（ジニ係数・上位10%・1%の割合）が分かっている分布から世帯を抜き出し、
# 階級別の割合（0.1%単位に四捨五入）にしてから推定し直す。実データでは確かめられない指標の当たり方を見る
import numpy as np, pandas as pd
from pathlib import Path
from scipy import stats, optimize
from common import *
A = Path(__file__).resolve().parents[1]; R = A / 'results'
bins = pd.read_csv(A / 'data' / 'bins_long.csv'); d24 = bins[bins.year == 2024]
cuts25 = SCHEMES['S25']; sh25 = coarsen(d24.lo, d24.share, cuts25)
rng = np.random.default_rng(1150)

# 答え1：対数正規3つの混合（2024年の25階級に区間の最尤推定で当てはめる。どの推定方法の型にも入らない）
b = np.concatenate([np.asarray(cuts25, float), [np.inf]]); s = sh25 / sh25.sum()
def mix_cdf(x, t):
    w = np.exp(np.r_[t[0:2], 0]); w = w / w.sum(); mu = t[2:5]; sg = np.exp(t[5:8])
    return sum(w[i] * stats.lognorm.cdf(x, sg[i], scale=np.exp(mu[i])) for i in range(3))
def nll(t):
    F = np.where(np.isinf(b), 1.0, mix_cdf(np.where(np.isinf(b), 1, b), t)); pr = np.diff(F)
    return -np.sum(s * np.log(np.maximum(pr, 1e-300)))
best = None
for st in [[0, 0, np.log(150), np.log(400), np.log(900), np.log(.5), np.log(.4), np.log(.5)], [-.5, .5, np.log(120), np.log(450), np.log(1100), np.log(.6), np.log(.45), np.log(.6)]]:
    r = optimize.minimize(nll, st, method='Nelder-Mead', options=dict(maxiter=20000, xatol=1e-8, fatol=1e-12))
    if best is None or r.fun < best.fun: best = r
F_mix = mix_cdf(GRID, best.x); F_mix[0] = 0
truths = {'mix3': Dist(F_mix, 'mix3')}
# 答え2：GB2（パラメトリックの型に有利な場合）
dg, _, _ = fit_param(cuts25, sh25, 'gb2', []); truths['gb2'] = dg
fitcheck = pd.DataFrame({'share_pub': s * 100, 'share_mix3': np.diff(np.r_[truths['mix3'].cdf(b[:-1]), 1]) * 100}, index=cuts25)
fitcheck.to_csv(R / 'sim_truth_fit.csv')
print('混合分布の当てはまり：最大の差（ポイント）', (fitcheck.share_pub - fitcheck.share_mix3).abs().max().round(2))

def sample(dist, n):  # 格子の累積分布の逆関数で n 世帯を抜き出す
    return dist.ppf(rng.uniform(0, dist.F[-1], n))

rows = []; truth_rows = []
for tn, td in truths.items():
    ts = td.summary(); truth_rows.append(dict(truth=tn, **ts))
    plan = [(None, 1)] + ([(2000, 60), (5000, 60), (20000, 60)] if tn == 'mix3' else [(5000, 40)])
    for n, reps in plan:
        for k in range(reps):
            if n is None:  # 標本の誤差なし（四捨五入だけ）
                p_fine = np.diff(np.r_[td.cdf(np.asarray(cuts25, float)), td.F[-1]]) * 100
            else:
                x = sample(td, n); p_fine = np.bincount(np.searchsorted(cuts25, x, side='right') - 1, minlength=len(cuts25)) / n * 100
            p_fine = np.round(p_fine, 1)  # 公表と同じく0.1%単位
            for sc in ['S25', 'S14', 'S8', 'S5']:
                cuts = SCHEMES[sc]; sh = np.maximum(coarsen(cuts25, p_fine, cuts), 1e-4)
                for m, (sm, _) in estimate_all(cuts, sh).items():
                    rows.append(dict(truth=tn, n=n or 0, rep=k, scheme=sc, method=m, **sm))
sim = pd.DataFrame(rows); tru = pd.DataFrame(truth_rows).set_index('truth')
sim.to_csv(R / 'sim_estimates.csv', index=False); tru.to_csv(R / 'sim_truth.csv')
K = ['gini', 'top10', 'top1', 'mean', 'median', 'qmean5']
for k in K: sim[k + '_err'] = sim[k] - sim.truth.map(tru[k])
agg = sim.groupby(['truth', 'n', 'scheme', 'method'])[[k + '_err' for k in K]].agg(['mean', lambda v: np.sqrt(np.mean(v ** 2))])
agg.columns = [f'{a}_{"bias" if b == "mean" else "rmse"}' for a, b in agg.columns]
agg.reset_index().to_csv(R / 'sim_summary.csv', index=False)
print(tru[K].round(4))
print(agg.loc[('mix3', 5000, 'S25')][['gini_err_bias', 'gini_err_rmse', 'top10_err_bias', 'top1_err_bias', 'top1_err_rmse']].round(4))
print(agg.loc[('mix3', 0)][['gini_err_bias', 'top10_err_bias', 'top1_err_bias']].round(4).to_string())
