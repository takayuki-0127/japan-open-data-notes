import json, numpy as np, pandas as pd, matplotlib, sys
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in fm.findSystemFonts():
    if 'NotoSansCJK' in f or 'NotoSansJP' in f: fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus'] = False
from pathlib import Path
B = Path(__file__).resolve().parents[1]; R = B/'results'; F = B/'figures'
sys.path.insert(0, str(Path(__file__).resolve().parent)); from common import *
d = pd.read_csv(B/'data/normals_mean_temp.csv', dtype={'id':str})
cv = pd.read_csv(R/'cv_metrics.csv'); vg = json.load(open(R/'variogram.json')); S = json.load(open(R/'summary.json'))
COL = {'IDW':'#9e9e9e','OK':'#4c78a8','線形回帰':'#f58518','RK':'#54a24b','LightGBM':'#b279a2'}
# 1) 地点と年平均気温
fig, ax = plt.subplots(1, 2, figsize=(11, 5.2))
sc = ax[0].scatter(d.lon, d.lat, c=d.annual, s=8, cmap='RdYlBu_r'); fig.colorbar(sc, ax=ax[0], label='年平均気温（℃）')
ax[0].set_title(f'観測点 {len(d)} 地点の年平均気温（平年値）', loc='left', fontsize=12); ax[0].set_aspect(1.2)
yy = d.annual - (S['lapse']['annual']['lat']*d.lat + S['lapse']['annual']['lon']*d.lon); yy = yy - yy[d.alt<50].median()
k_ = d.alt < 2000
ax[1].scatter(d.alt[k_], yy[k_], s=8, alpha=.5, c='#4c78a8'); ax[1].plot([0,1500],[0,1500*S['lapse']['annual']['per100m']/100], c='#e45756', lw=1.5)
ax[1].text(0.02, 0.03, '富士山頂（3,775m）は図の外', transform=ax[1].transAxes, fontsize=8)
ax[1].set_xlabel('標高（m）'); ax[1].set_ylabel('緯度・経度の分を除いた気温（低地との差、℃）')
ax[1].set_title(f"標高100mで {S['lapse']['annual']['per100m']:.2f}℃", loc='left', fontsize=12); ax[1].grid(alpha=.3)
fig.tight_layout(); fig.savefig(F/'f74_stations.png', dpi=150); plt.close()
# 2) バリオグラム
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
from pykrige import variogram_models as vm
for i, nm in enumerate(['raw','resid']):
    v = vg[f'{nm}_spherical']; ax[i].scatter(v['lags'], v['semivar'], s=14, c='k', label='経験バリオグラム')
    h = np.linspace(0, max(v['lags']), 200)
    for mdl, c in [('spherical','#4c78a8'),('exponential','#f58518'),('gaussian','#54a24b')]:
        p = vg[f'{nm}_{mdl}']['params']; f = getattr(vm, mdl+'_variogram_model')
        ax[i].plot(h, f(p, h), c=c, label={'spherical':'球形','exponential':'指数','gaussian':'ガウス'}[mdl])
    ax[i].set_xlabel('2地点の距離（km）'); ax[i].set_ylabel('半分散（℃²）'); ax[i].grid(alpha=.3)
    ax[i].set_title({'raw':'年平均気温そのもの','resid':'緯度・経度・標高で説明した残り'}[nm], loc='left', fontsize=12)
ax[0].legend(frameon=False, fontsize=9)
fig.suptitle('離れるほど気温はどれだけ違うか（バリオグラム）', x=0.01, ha='left', fontsize=13); fig.tight_layout(); fig.savefig(F/'f74_variogram.png', dpi=150); plt.close()
# 3) 手法 × 分け方の RMSE（年平均）
a = cv[cv.target=='annual'].pivot(index='method', columns='scheme', values='rmse').loc[METHODS]
fig, ax = plt.subplots(figsize=(9, 4.6)); w = .26
lab = {'point':'地点をランダムに分ける','area':'予報区ごとに外す','block':'100km四方ごとに外す'}
for j, s in enumerate(['point','area','block']):
    ax.bar(np.arange(len(METHODS))+(j-1)*w, a[s], w, label=lab[s], color=['#4c78a8','#f58518','#e45756'][j])
    for i, v in enumerate(a[s]): ax.text(i+(j-1)*w, v+.02, f'{v:.2f}', ha='center', fontsize=8)
ax.set_xticks(range(len(METHODS))); ax.set_xticklabels(['IDW','通常クリギング','線形回帰\n（緯度・経度・標高）','回帰クリギング','LightGBM']); ax.set_ylabel('外れ（RMSE, ℃）')
ax.set_title('年平均気温を観測点で隠して当てたときの外れ', loc='left', fontsize=13); ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.3, axis='y')
fig.tight_layout(); fig.savefig(F/'f74_cv_rmse.png', dpi=150); plt.close()
# 4) 標高帯別
eb = pd.read_csv(R/'rmse_by_altitude.csv')
fig, ax = plt.subplots(figsize=(9, 4.4))
for m in METHODS: ax.plot(eb.altbin, eb[m], marker='o', label={'OK':'通常クリギング','RK':'回帰クリギング'}.get(m, m), c=COL[m])
ax.set_ylabel('外れ（RMSE, ℃）'); ax.set_xlabel('観測点の標高（カッコ内は地点数）')
ax.set_xticks(range(len(eb))); ax.set_xticklabels([f'{b}\n（{n}）' for b, n in zip(eb.altbin, eb.n)])
ax.set_title('高い場所ほど、標高を使わない手法は外れる', loc='left', fontsize=13); ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(F/'f74_by_altitude.png', dpi=150); plt.close()
# 5) 月別
mm = ['m1','m4','m8','m10','annual']; lab2 = ['1月','4月','8月','10月','年平均']
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for k, s in enumerate(['point','block']):
    for m in METHODS:
        v = [cv[(cv.target==t)&(cv.scheme==s)&(cv.method==m)].rmse.iloc[0] for t in mm]
        ax[k].plot(lab2, v, marker='o', c=COL[m], label={'OK':'通常クリギング','RK':'回帰クリギング'}.get(m, m))
    ax[k].set_title({'point':'地点をランダムに分ける','block':'100km四方ごとに外す'}[s], loc='left', fontsize=12); ax[k].grid(alpha=.3)
ax[0].set_ylabel('外れ（RMSE, ℃）'); ax[0].legend(frameon=False, fontsize=9)
fig.suptitle('月によって当てやすさは変わる（冬は外れが大きい）', x=0.01, ha='left', fontsize=13); fig.tight_layout(); fig.savefig(F/'f74_by_month.png', dpi=150); plt.close()
# 6) 地図：通常クリギングの予測（標高は使えない）と、観測点で隠して当てたときの通常クリギングの外れ
from scipy.spatial import cKDTree
P = pd.read_csv(R/'cv_pred_annual_point.csv', dtype={'id':str})
main = (d.lon.between(128.5, 146.5)) & (d.lat.between(30.5, 46))
x, y = xy(d)
gx, gy = np.meshgrid(np.linspace(-750, 850, 330), np.linspace(-620, 1110, 360))
tr = cKDTree(np.c_[x, y]); dd, _ = tr.query(np.c_[gx.ravel(), gy.ravel()])
z, s, _ = ok(x, y, d.annual.values, gx.ravel(), gy.ravel())
Z = np.where(dd > 20, np.nan, z).reshape(gx.shape)
fig, ax = plt.subplots(1, 2, figsize=(11, 6.2))
im = ax[0].pcolormesh(gx, gy, Z, cmap='RdYlBu_r', shading='auto', vmin=0, vmax=20); fig.colorbar(im, ax=ax[0], label='℃', shrink=.8)
ax[0].set_title('通常クリギングの年平均気温（観測点から20km以内）', loc='left', fontsize=11)
e = (P['OK'] - P['obs']).values; mm = main.values
sc = ax[1].scatter(x[mm], y[mm], c=np.clip(e[mm], -3, 3), cmap='RdBu_r', s=np.where(np.abs(e[mm])>1.5, 22, 6), vmin=-3, vmax=3)
fig.colorbar(sc, ax=ax[1], label='予測 − 実際（℃）', shrink=.8)
ax[1].set_title('通常クリギングの外れ（赤＝高く当てすぎ）', loc='left', fontsize=11)
for a_ in ax: a_.set_aspect(1); a_.set_xticks([]); a_.set_yticks([]); a_.set_xlim(-750, 850); a_.set_ylim(-620, 1110)
fig.text(0.01, 0.01, '沖縄・小笠原などの離島は図の外（分析には含む）。富士山頂は外れ+18℃のため色の上限で表示', fontsize=8)
fig.tight_layout(); fig.savefig(F/'f74_map.png', dpi=150); plt.close()
print('figs ok')
