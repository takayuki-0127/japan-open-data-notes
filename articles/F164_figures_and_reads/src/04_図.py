import pandas as pd, numpy as np, json, pathlib, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.spines.top'] = False; plt.rcParams['axes.spines.right'] = False
B = pathlib.Path(__file__).resolve().parents[1]; R = B/'results'; F = B/'figures'; F.mkdir(exist_ok=True)
df = pd.read_csv(B/'data/articles.csv'); S = json.load(open(R/'summary.json'))
C = {'0枚':'#9aa5b1','1〜2枚':'#7fb3d5','3〜4枚':'#2e86c1','5〜6枚':'#1b4f72'}
# 図1 公開からの日数とスキ
fig, ax = plt.subplots(figsize=(8,4.8)); rng = np.random.default_rng(1)
for k, g in df.groupby('fig_bin'):
    ax.scatter(g.days, g.like + rng.uniform(-0.12,0.12,len(g)), s=60, color=C[k], label=f'図{k}（{len(g)}本）', alpha=.85, edgecolor='white')
ax.set_xscale('log'); ax.set_xlabel('公開からの日数（2026年11月4日 8:54 時点、対数）'); ax.set_ylabel('スキの数（重なりを少しずらしている）')
ax.set_yticks([0,1,2,3]); ax.legend(frameon=False, fontsize=9, loc='upper left')
ax.set_title('34本のうち22本はスキ0。数が少なく、図の枚数で分かれた形は見えない', fontsize=12, loc='left')
fig.tight_layout(); fig.savefig(F/'fig1_days_vs_likes.png', dpi=150); plt.close()
# 図2 図の枚数ごとの、30日あたりのスキ（95%区間）
t = pd.read_csv(R/'by_figures.csv')
fig, ax = plt.subplots(figsize=(8,4.6)); x = np.arange(len(t))
ax.bar(x, t.likes_per30d, color=[C[k] for k in t.fig_bin], width=.6)
ax.errorbar(x, t.likes_per30d, yerr=[t.likes_per30d-t.ci_lo, t.ci_hi-t.likes_per30d], fmt='none', ecolor='#333', capsize=5)
for i, r in t.iterrows(): ax.text(i, r.ci_hi+.15, f'{r.n}本・スキ{r.likes}\n日数計{r.days:.0f}日', ha='center', fontsize=9)
ax.set_xticks(x, [f'図{k}' for k in t.fig_bin]); ax.set_ylabel('30日あたりのスキ（日数で割った率）'); ax.set_ylim(0, t.ci_hi.max()+1.3)
ax.set_title('日数で割ると「図5〜6枚」が高く見えるが、この群は新しい記事ばかり', fontsize=12, loc='left')
fig.tight_layout(); fig.savefig(F/'fig2_rate_by_figures.png', dpi=150); plt.close()
# 図3 日数の扱いで、図5枚以上の「倍率」がどう変わるか（10/17以降の30本）
e = pd.read_csv(R/'exposure_sensitivity.csv')
fig, ax = plt.subplots(figsize=(8,4.2)); y = np.arange(len(e))[::-1]
ax.barh(y, e.rate_ratio, color='#2e86c1', height=.55); ax.axvline(1, color='#555', lw=1, ls='--')
for yi, r in zip(y, e.itertuples()): ax.text(r.rate_ratio+.08, yi, f'{r.rate_ratio:.1f}倍（p={r.binom_p:.3f}）', va='center', fontsize=10)
ax.set_yticks(y, e.exposure); ax.set_xlabel('図5枚以上の記事のスキ ÷ 図4枚以下の記事のスキ'); ax.set_xlim(0, e.rate_ratio.max()+1.6)
ax.set_title('同じ期間（10/17以降の30本）でも、日数の扱い1つで4.6倍→2.3倍', fontsize=12, loc='left')
fig.tight_layout(); fig.savefig(F/'fig3_exposure_sensitivity.png', dpi=150); plt.close()
# 図4 記事の作りが重なっている（図の枚数・字数・タイトルの長さ）
fig, axs = plt.subplots(1, 2, figsize=(9,4.2))
for k, g in df.groupby('fig_bin'):
    axs[0].scatter(g.n_img+np.random.default_rng(2).uniform(-.15,.15,len(g)), g.chars, color=C[k], s=45)
    axs[1].scatter(g.n_img+np.random.default_rng(3).uniform(-.15,.15,len(g)), g.title_len, color=C[k], s=45)
axs[0].set_xlabel('図の枚数'); axs[0].set_ylabel('本文の字数'); axs[1].set_xlabel('図の枚数'); axs[1].set_ylabel('タイトルの字数')
r1 = df[['n_img','chars']].corr(method='spearman').iloc[0,1]; r2 = df[['n_img','title_len']].corr(method='spearman').iloc[0,1]
axs[0].set_title(f'順位相関 {r1:.2f}', fontsize=10); axs[1].set_title(f'順位相関 {r2:.2f}', fontsize=10)
fig.suptitle('図が多い記事は、字数もタイトルも長い。どれが効いたかは分けられない', fontsize=12, x=.02, ha='left')
fig.tight_layout(); fig.savefig(F/'fig4_overlap.png', dpi=150); plt.close()
# 図5 図1枚あたりのスキの倍率（ポアソン回帰）を条件ごとに
rb = S['robust']; p = S['poisson']['n_img']
items = [('基本（日数で割る・字数とタイトル長も入れる）', p[:3]), ('10/17以降だけ', rb['since1017_poisson_img']), ('スキ＋コメント', rb['like_plus_comment_img_RR']),
         ('日数の平方根で割る', rb['sqrt_days_img_RR']), ('日数で割らない', rb['no_offset_img_RR']), ('「スキが1つ以上」のオッズ比', rb['any_like_logit_img_OR'])]
fig, ax = plt.subplots(figsize=(8.5,4.4)); y = np.arange(len(items))[::-1]
for yi, (lab, (est, lo, hi)) in zip(y, items):
    ax.plot([lo, hi], [yi, yi], color='#1b4f72', lw=2); ax.plot(est, yi, 'o', color='#1b4f72'); ax.text(hi+.05, yi, f'{est:.2f}（{lo:.2f}〜{hi:.2f}）', va='center', fontsize=9)
ax.axvline(1, color='#555', ls='--', lw=1); ax.set_yticks(y, [i[0] for i in items], fontsize=9); ax.set_xscale('log'); ax.set_xlim(.5, 3.5); ax.set_xticks([.5,.75,1,1.5,2,3],['0.5','0.75','1','1.5','2','3']); ax.minorticks_off()
ax.set_xlabel('図が1枚多いときのスキの倍率（95%区間、対数）')
fig.suptitle('どの条件でも区間は1をまたぐか、ぎりぎり。0.7倍も2倍もありうる幅', fontsize=12, x=.02, ha='left')
fig.tight_layout(); fig.savefig(F/'fig5_rr_forest.png', dpi=150); plt.close()
print('ok')
