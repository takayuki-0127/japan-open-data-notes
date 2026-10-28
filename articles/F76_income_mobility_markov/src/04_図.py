"""04 図：5〜6枚"""
import json, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import ROOT, C1, C2, C3, G, rank_class
FIG = ROOT / 'figures'; FIG.mkdir(exist_ok=True)
res = json.load(open(ROOT / 'results/summary.json'))
pref = pd.read_csv(ROOT / 'data/pref_panel.csv')
W = pref.pivot(index='code', columns='year', values='r')
rk = W.rank(ascending=False)

# 1. 順位の推移（1955年度の5分位で色分け）
fig, ax = plt.subplots(figsize=(9, 5.2))
q0 = rank_class(W[1955].to_numpy(), 5)
cols = ['#c0392b', '#e67e22', '#bbbbbb', '#5dade2', '#1f4e79']
for i, code in enumerate(W.index):
    ax.plot(rk.columns, rk.loc[code], color=cols[q0[i]], lw=1.1 if q0[i] in (0, 4) else 0.6, alpha=0.9 if q0[i] in (0, 4) else 0.5)
ax.invert_yaxis(); ax.set_ylabel('1人当たり県民所得の順位（46都道府県）'); ax.set_xlabel('年度')
ax.set_title('1955年度に下位20%の県の56%、上位20%の33%が2022年度も同じ区分（入れ替わりがでたらめなら20%）', fontsize=10)
from matplotlib.lines import Line2D
ax.legend([Line2D([0], [0], color=cols[4], lw=2), Line2D([0], [0], color=cols[3], lw=2), Line2D([0], [0], color=cols[2], lw=2),
           Line2D([0], [0], color=cols[1], lw=2), Line2D([0], [0], color=cols[0], lw=2)],
          ['1955年度に上位20%', '上位20〜40%', '中位', '下位20〜40%', '下位20%'], fontsize=8, loc='lower left', ncol=2)
ax.set_yticks([1, 10, 20, 30, 40, 46]); fig.tight_layout(); fig.savefig(FIG / 'f76_rankpaths.png', dpi=150); plt.close()

# 2. 遷移行列（都道府県 全期間 vs 市区町村 2015→20）
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, P, t in [(axs[0], np.array(res['pref_all']['P']), '都道府県（5年後、1955〜2022年度）'),
                 (axs[1], np.array(res['muni']['2015->2020_k5']['P']), '市区町村（2015→2020年度）')]:
    ax.imshow(P, cmap='Blues', vmin=0, vmax=1)
    for i in range(5):
        for j in range(5):
            ax.text(j, i, f'{P[i,j]*100:.0f}%', ha='center', va='center', color='white' if P[i, j] > 0.5 else 'black', fontsize=9)
    lab = ['下位\n20%', '', '中位', '', '上位\n20%']
    ax.set_xticks(range(5)); ax.set_xticklabels(lab, fontsize=8); ax.set_yticks(range(5)); ax.set_yticklabels(lab, fontsize=8)
    ax.set_xlabel('5年後の区分'); ax.set_ylabel('はじめの区分'); ax.set_title(t, fontsize=10)
fig.suptitle('所得の5分位の遷移行列：対角線（同じ区分にとどまる）が太い', fontsize=11)
fig.tight_layout(); fig.savefig(FIG / 'f76_matrix.png', dpi=150); plt.close()

# 3. 順位の相関の減り方と、マルコフの仮定による予測
fig, ax = plt.subplots(figsize=(8, 4.6))
h = np.array([int(k) for k in res['pref_rankcorr']]); v = np.array(list(res['pref_rankcorr'].values()))
ax.plot(h, v, color=C1, lw=2, label='都道府県：t年度とt+h年度の順位相関（実際）')
mc = {k: v for k, v in res['muni_rankcorr'].items()}
ax.scatter([5, 5, 5, 15], [mc['2005->2010'], mc['2010->2015'], mc['2015->2020'], mc['2005->2020']], color=C2, zorder=3, label='市区町村（2005〜2020年度）')
ax.set_xlabel('何年後か（h）'); ax.set_ylabel('スピアマンの順位相関'); ax.set_ylim(0.3, 1.0)
ax.set_title('都道府県の順位は、20年後でも相関0.82、40年後で0.66')
ax.grid(alpha=0.3); ax.legend(fontsize=9); fig.tight_layout(); fig.savefig(FIG / 'f76_rankcorr.png', dpi=150); plt.close()

# 4. マルコフ性の確認：1年の行列を重ねると動きを大きく見積もる
mk = res['markov_check']
fig, ax = plt.subplots(figsize=(7, 4.4))
labs = ['5年後', '20年後']; real = [mk['P5_stay'], mk['P20_stay']]; pred = [mk['P1^5_stay'], mk['P1^20_stay']]
x = np.arange(2)
ax.bar(x - 0.18, real, 0.36, color=C1, label='実際の遷移（その年数の行列）')
ax.bar(x + 0.18, pred, 0.36, color=C2, label='1年の行列を重ねた予測（マルコフの仮定）')
for i in range(2):
    ax.text(x[i] - 0.18, real[i] + 0.01, f'{real[i]*100:.0f}%', ha='center'); ax.text(x[i] + 0.18, pred[i] + 0.01, f'{pred[i]*100:.0f}%', ha='center')
ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylabel('同じ5分位にとどまる割合（行の平均）'); ax.set_ylim(0, 0.85)
ax.set_title('1年の行列を重ねると、順位の入れ替わりを大きく見積もる'); ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig(FIG / 'f76_markov_check.png', dpi=150); plt.close()

# 5. 定常分布（水準の5区分）
fig, ax = plt.subplots(figsize=(8.5, 4.6))
cats = ['0.85未満', '0.85〜0.95', '0.95〜1.05', '1.05〜1.15', '1.15以上']
e = res['ergodic']['全期間']; e3 = res['ergodic']['1995〜2022']
x = np.arange(5); w = 0.2
ax.bar(x - 1.5 * w, e['start'], w, color='#cccccc', label='1955年度（実際）')
ax.bar(x - 0.5 * w, e['end'], w, color=C1, label='2022年度（実際）')
ax.bar(x + 0.5 * w, e['ergodic'], w, color=C3, label='定常分布（1955〜2022年度の遷移）')
ax.bar(x + 1.5 * w, e3['ergodic'], w, color=C2, label='定常分布（1995〜2022年度の遷移）')
ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_xlabel('1人当たり県民所得（46都道府県の幾何平均＝1）'); ax.set_ylabel('都道府県の割合')
ax.set_title('今の動きが続いたときの行き着く先は、今の分布とほぼ同じ'); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / 'f76_ergodic.png', dpi=150); plt.close()

# 6. 頑健性
rob = pd.read_csv(ROOT / 'results/robustness.csv')
fig, ax = plt.subplots(figsize=(8.5, 5.5))
y = np.arange(len(rob))[::-1]
ax.barh(y, rob['shorrocks'], color=[C2 if s.startswith('市区町村') else C1 for s in rob['設定']])
for yi, v in zip(y, rob['shorrocks']): ax.text(v + 0.005, yi, f'{v:.2f}', va='center', fontsize=8)
ax.set_yticks(y); ax.set_yticklabels(rob['設定'], fontsize=8); ax.set_xlabel('Shorrocks の移動性指標（0＝まったく動かない、1＝完全に入れ替わる）')
ax.set_title('移動性は区分の数と年数で変わるが、どの設定でも「よく残る」'); fig.tight_layout(); fig.savefig(FIG / 'f76_robust.png', dpi=150); plt.close()
print('ok')
