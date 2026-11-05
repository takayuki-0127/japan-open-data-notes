# F206 図とダッシュボードの見本（静的な HTML）を作る
import os, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus'] = False
H = os.path.dirname(os.path.abspath(__file__)) + '/..'; R = H + '/results'; FG = H + '/figures'; DB = H + '/dashboard'
os.makedirs(FG, exist_ok=True); os.makedirs(DB, exist_ok=True)
C1, C2, C3, CG = '#2a6fdb', '#e8833a', '#3a9d5d', '#888888'
main = json.load(open(f'{R}/main.json'))

# 図1 そろえる前の矛盾：合計の予測と（東京＋関西の予測）の差
g = pd.read_csv(f'{R}/A_incoherence_daily.csv', parse_dates=['date'])
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(g.date, g.gap_pct, width=1.0, color=np.where(g.gap_pct > 0, C2, C1))
ax.axhline(0, color='k', lw=0.8)
ax.set_ylabel('合計の予測−（東京＋関西）\n実績比％・日平均', fontsize=9)
ax.set_title(f'別々に当てると、合計と内訳が合わない（1時間ごとの差の平均 {main["A_矛盾_合計比_平均絶対"]:.1f}%、上位5%は {main["A_矛盾_合計比_95点"]:.1f}% 以上）', fontsize=11)
fig.tight_layout(); fig.savefig(f'{FG}/f206_1_incoherence.png', dpi=150); plt.close(fig)

# 図2 そろえ方ごとの外れ（MAPE）
t = pd.read_csv(f'{R}/A_reconcile_main.csv')
lab = {'base': 'そろえない\n（別々の予測）', 'BU': '下から足す\n（ボトムアップ）', 'TD': '上から割る\n（トップダウン）',
       'OLS': '等しい重み\n（OLS）', 'WLS': '外れの大きさで重み\n（WLS）', 'MinT': '外れの相関も使う\n（MinT）'}
x = np.arange(len(t)); w = 0.27
fig, ax = plt.subplots(figsize=(10, 4.6))
for i, (c, col) in enumerate([('合計', C3), ('東京', C1), ('関西', C2)]):
    ax.bar(x + (i - 1) * w, t[c], w, label=c, color=col)
    for xi, v in zip(x, t[c]): ax.text(xi + (i - 1) * w, v + 0.03, f'{v:.2f}', ha='center', fontsize=7.5)
ax.set_xticks(x); ax.set_xticklabels([lab[m] for m in t['方法']], fontsize=9)
ax.set_ylabel('1時間ごとの MAPE（%）'); ax.set_ylim(0, 4.2); ax.legend(ncol=3, loc='upper left')
ax.set_title('2026年1〜9月：合計は「下から足す」と「MinT」が同じくらい良く、「上から割る」は内訳を悪くした', fontsize=11)
fig.tight_layout(); fig.savefig(f'{FG}/f206_2_reconcile_mape.png', dpi=150); plt.close(fig)

# 図3 MinT −「下から足す」の差（週ブロック・ブートストラップの95%区間）、条件を変えて
b = pd.read_csv(f'{R}/A_boot_mint.csv'); b = b[b['比べる相手'] == 'BU']
conds = list(dict.fromkeys(b['条件'])); lv = ['合計', '東京', '関西']; cols = {'合計': C3, '東京': C1, '関西': C2}
fig, ax = plt.subplots(figsize=(9, 4.6))
for j, l in enumerate(lv):
    s = b[b['レベル'] == l].set_index('条件').reindex(conds)
    y = np.arange(len(conds)) + (j - 1) * 0.22
    ax.errorbar(s['差'], y, xerr=[s['差'] - s['下限'], s['上限'] - s['差']], fmt='o', color=cols[l], label=l, capsize=3)
ax.axvline(0, color='k', lw=0.8); ax.set_yticks(range(len(conds))); ax.set_yticklabels(conds); ax.invert_yaxis()
ax.set_xlabel('MinT の MAPE −「下から足す」の MAPE（ポイント、右ほど MinT が悪い）'); ax.legend(loc='lower right')
ax.set_title('差（点）はどの条件でも ±0.03 ポイント以内。MAPE 2〜3% に比べてごく小さい', fontsize=11)
fig.tight_layout(); fig.savefig(f'{FG}/f206_3_mint_vs_bu.png', dpi=150); plt.close(fig)

# 図4 時間の階層：1日の量を直接当てるか、24時間を足すか
tp = pd.read_csv(f'{R}/B_temporal.csv')
order = ['1日の量を直接', '時間の合計（下から）', '構造の重み', '分散の重み']
nm = {'1日の量を直接': '1日の量を\n直接当てる', '時間の合計（下から）': '24時間の予測を\n足す', '構造の重み': 'そろえる\n（数で重み）', '分散の重み': 'そろえる\n（外れの大きさで重み）'}
fig, ax = plt.subplots(figsize=(9, 4.2)); x = np.arange(len(order)); w = 0.38
for i, (a, col) in enumerate([('東京', C1), ('関西', C2)]):
    s = tp[tp['エリア'] == a].set_index('方法').reindex(order)['1日の量のMAPE']
    ax.bar(x + (i - 0.5) * w, s, w, label=a, color=col)
    for xi, v in zip(x, s): ax.text(xi + (i - 0.5) * w, v + 0.03, f'{v:.2f}', ha='center', fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([nm[o] for o in order]); ax.set_ylabel('1日の電力量の MAPE（%）'); ax.legend()
ax.set_title('1日の量は、直接当てるより「24時間の予測を足す」ほうが外れが小さかった', fontsize=11)
fig.tight_layout(); fig.savefig(f'{FG}/f206_4_temporal.png', dpi=150); plt.close(fig)

# 図6 区間の当たり方（月ごと）と、見張りのアラート
mon = pd.read_csv(f'{R}/C_coverage_monthly_tokyo.csv')
md = pd.read_csv(f'{R}/C_monitor_daily_tokyo.csv', index_col=0, parse_dates=True)
al = pd.read_csv(f'{R}/C_alerts_tokyo.csv', parse_dates=['始まり', '終わり'])
fig, axs = plt.subplots(2, 1, figsize=(9.5, 6.4), gridspec_kw={'height_ratios': [1, 1.2]})
ax = axs[0]; xm = mon['月'].astype(str) + '月'
ax.plot(xm, mon['80%区間'], 'o-', color=C1, label='80%区間に入った割合'); ax.plot(xm, mon['95%区間'], 's-', color=C2, label='95%区間に入った割合')
ax.axhline(80, color=C1, ls='--', lw=0.8); ax.axhline(95, color=C2, ls='--', lw=0.8)
ax.set_ylim(55, 100); ax.set_ylabel('%'); ax.legend(loc='lower left', fontsize=8)
ax.set_title('東京2026年：真夏と真冬は区間から外れやすい（8月は80%区間に63%しか入らない）', fontsize=10.5)
ax = axs[1]; s = md['ずれの7日平均']
ax.plot(s.index, s, color=CG, lw=1); ax.axhline(1.5, color='r', ls='--', lw=0.8); ax.axhline(-1.5, color='r', ls='--', lw=0.8)
for _, r in al.iterrows(): ax.axvspan(r['始まり'], r['終わり'] + pd.Timedelta(days=1), color='r', alpha=0.15)
ax.set_ylabel('（実績−予測）÷実績の\n7日平均（%）'); ax.set_xlim(pd.Timestamp('2025-10-07'), pd.Timestamp('2026-09-30'))
ax.set_title(f'見張り（±1.5%）：1年で{len(al)}回・{int(al["日数"].sum())}日。年末年始・お盆・連休の前後に集まった', fontsize=10.5)
fig.tight_layout(); fig.savefig(f'{FG}/f206_6_coverage_alerts.png', dpi=150); plt.close(fig)

# ---------- ダッシュボードの見本（静的 HTML・外部ファイルなし） ----------
d = pd.read_csv(f'{R}/C_dashboard_day.csv', parse_dates=['ts'])
day = main['dashboard_day']; prev = (pd.Timestamp(day) - pd.Timedelta(days=1)).date()
mprev = md.loc[:str(prev)]
mape7 = float(mprev['日のMAPE'].tail(7).mean()); drift7 = float(mprev['ずれの7日平均'].iloc[-1])
pk = d.loc[d.pred.idxmax()]; margin = 0.033   # F205：足りないが余るの9倍の例で決めた上乗せ（前年度で決めた中央値）
W, Hh, L, B_, T_ = 760, 310, 60, 40, 34
ymin = float(min(d.lo95.min(), d.actual.min())) * 0.97; ymax = float(max(d.hi95.max(), d.actual.max(), pk.pred * (1 + margin))) * 1.02
X = lambda i: L + i * (W - L - 20) / 23
Yv = lambda v: T_ + (ymax - v) * (Hh - T_ - B_) / (ymax - ymin)
def poly(a, b): return ' '.join(f'{X(i):.1f},{Yv(v):.1f}' for i, v in enumerate(a)) + ' ' + ' '.join(f'{X(i):.1f},{Yv(v):.1f}' for i, v in reversed(list(enumerate(b))))
def line(a): return ' '.join(f'{X(i):.1f},{Yv(v):.1f}' for i, v in enumerate(a))
yt = np.linspace(ymin, ymax, 5)
grid = ''.join(f'<line x1="{L}" x2="{W-20}" y1="{Yv(v):.1f}" y2="{Yv(v):.1f}" stroke="#eee"/><text x="{L-6}" y="{Yv(v)+4:.1f}" font-size="11" text-anchor="end" fill="#666">{v/10:,.0f}</text>' for v in yt)
xt = ''.join(f'<text x="{X(i):.1f}" y="{Hh-B_+16}" font-size="11" text-anchor="middle" fill="#666">{i}時</text>' for i in range(0, 24, 3))
svg = f'''<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="翌日の需要の予測と区間">{grid}{xt}
<polygon points="{poly(d.lo95, d.hi95)}" fill="#2a6fdb" opacity="0.12"/><polygon points="{poly(d.lo80, d.hi80)}" fill="#2a6fdb" opacity="0.22"/>
<polyline points="{line(d.pred)}" fill="none" stroke="#2a6fdb" stroke-width="2.5"/>
<polyline points="{line(d.actual)}" fill="none" stroke="#333" stroke-width="1.5" stroke-dasharray="4 3"/>
<line x1="{L}" x2="{W-20}" y1="{Yv(pk.pred*(1+margin)):.1f}" y2="{Yv(pk.pred*(1+margin)):.1f}" stroke="#e8833a" stroke-dasharray="6 4"/>
<text x="{W-24}" y="{Yv(pk.pred*(1+margin))-6:.1f}" font-size="11" text-anchor="end" fill="#e8833a">準備の目安（ピーク予測＋3.3%）</text>
<text x="{L-50}" y="{T_-18}" font-size="11" fill="#666">（万kW）</text></svg>'''
# 直近30日の見張り
m30 = mprev['ずれの7日平均'].tail(30); W2, H2 = 360, 90
yl = 3.5; X2 = lambda i: 10 + i * (W2 - 20) / (len(m30) - 1); Y2 = lambda v: 8 + (yl - v) * (H2 - 16) / (2 * yl)
spark = f'''<svg viewBox="0 0 {W2} {H2}" width="100%"><rect x="10" y="{Y2(1.5):.1f}" width="{W2-20}" height="{Y2(-1.5)-Y2(1.5):.1f}" fill="#3a9d5d" opacity="0.10"/>
<line x1="10" x2="{W2-10}" y1="{Y2(0):.1f}" y2="{Y2(0):.1f}" stroke="#ccc"/><polyline points="{' '.join(f'{X2(i):.1f},{Y2(v):.1f}' for i, v in enumerate(m30))}" fill="none" stroke="#555" stroke-width="1.5"/></svg>'''
ok = abs(drift7) <= 1.5
status = ('<span class="ok">正常（±1.5%以内）</span>' if ok else '<span class="ng">要確認（±1.5%超え）</span>')
html = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>電力需要の予測ダッシュボード（見本）</title>
<style>body{{font-family:"Noto Sans CJK JP","Hiragino Sans","Yu Gothic",sans-serif;margin:0;background:#f6f7f9;color:#222}}
header{{background:#1f3b63;color:#fff;padding:12px 20px}}h1{{font-size:18px;margin:0}}.sub{{font-size:12px;opacity:.85}}
main{{padding:14px 20px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card{{background:#fff;border-radius:8px;padding:12px 14px;box-shadow:0 1px 2px rgba(0,0,0,.08)}}
.k{{font-size:12px;color:#666}}.v{{font-size:24px;font-weight:700;margin-top:4px}}.n{{font-size:11px;color:#777;margin-top:4px}}
.wide{{grid-column:span 4}}.half{{grid-column:span 2}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #eee;padding:6px;text-align:right}}th:first-child,td:first-child{{text-align:left}}
.ok{{color:#3a9d5d;font-weight:700}}.ng{{color:#c0392b;font-weight:700}}.legend span{{display:inline-block;margin-right:14px;font-size:12px}}</style></head><body>
<header><h1>電力需要の予測ダッシュボード（見本）</h1><div class="sub">{prev} 24時に作成｜対象日 {day}｜東京エリア｜※公開データで作った見本。値段の比は例示</div></header>
<main>
<div class="card"><div class="k">明日のピーク（予測）</div><div class="v">{pk.pred/10:,.0f} 万kW</div><div class="n">{int(pk.ts.hour)}時ごろ</div></div>
<div class="card"><div class="k">ピークの95%上限</div><div class="v">{pk.hi95/10:,.0f} 万kW</div><div class="n">過去90日の外れの分布から</div></div>
<div class="card"><div class="k">直近7日の外れ（MAPE）</div><div class="v">{mape7:.1f}%</div><div class="n">1時間ごとの平均</div></div>
<div class="card"><div class="k">ずれの見張り（7日平均）</div><div class="v">{drift7:+.1f}%</div><div class="n">{status}</div></div>
<div class="card wide"><div class="k">明日の24時間：予測（青線）・80%区間（濃い帯）・95%区間（薄い帯）</div>{svg}
<div class="legend"><span>━ 予測</span><span>┅ 実績（あとから重ねたもの）</span><span style="color:#e8833a">┅ 準備の目安</span></div></div>
<div class="card half"><div class="k">直近30日のずれ（緑の帯＝±1.5%）</div>{spark}<div class="n">外れの「大きさ」ではなく「向き」を見る（F205）</div></div>
<div class="card half"><div class="k">読み方のメモ</div><table><tr><th>見るところ</th><th>こうなったら</th></tr>
<tr><td>ずれの見張り</td><td>±1.5%を3日超えたら原因を確認</td></tr><tr><td>95%上限</td><td>真夏・真冬は当たりにくい（8月は81%）</td></tr>
<tr><td>準備の目安</td><td>不足と余りの値段の比で幅を変える</td></tr><tr><td>エリアと合計</td><td>合計はエリアを足した値で出す</td></tr></table></div>
</main></body></html>'''
open(f'{DB}/dashboard_sample.html', 'w', encoding='utf-8').write(html)
print('dashboard ok', day, round(mape7, 2), round(drift7, 2))
