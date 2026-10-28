"""01 取得：新しいダウンロードはしない。F71（県民経済計算をつないだ1人当たり県民所得）と
F40（市町村税課税状況等の調の課税対象所得、社会・人口統計体系）で作った表を使う。
GitHub に置いた F71・F40 の表を data/raw/ に取ってくる（同じものを置いてある）"""
import urllib.request
from common import ROOT
BASE = 'https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/'
for src, dst in [('F71_income_convergence/data/panel_rel_income.csv', 'f71_panel_rel_income.csv'),
                 ('F40_inequality_decomposition/data/panel.csv', 'f40_municipal_panel.csv')]:
    p = ROOT / 'data/raw' / dst
    if p.exists():
        print('あり：', p.name); continue
    urllib.request.urlretrieve(BASE + src, p); print('取得：', p.name)
