"""共通：データの読み込みと変数の作成"""
import json, numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261027

plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False

Y = '子ども女性比'
# 説明変数。持ち家率・一戸建て率は住宅・土地統計調査（2013年）で、小さい町村は値がない
XMISS = ['持ち家率']
XFULL = ['65歳以上の割合', '大卒の割合', '第1次産業の割合', 'log人口密度', '単独世帯の割合', '女性の労働力率', 'log所得']
XALL = XMISS + XFULL
FOCUS = '持ち家率'


def is_ward(code):
    # 政令指定都市の区（例 01101）は除き、市全体（例 01100）を残す。東京23区は残す
    return code[2] == '1' and code[4] != '0' and code[:2] != '13'


def wide(year):
    p = pd.read_csv(ROOT / 'data/panel_long.csv', dtype={'code': str})
    return p[p.year == year].set_index('code')


def make_data(house_year=2013, year=2015, edu_year=2010):
    """市区町村×1年の分析用の表。持ち家率・一戸建て率だけが欠ける（他は欠けない行に絞る）"""
    g = wide(year); h = wide(house_year); e = wide(edu_year)
    d = pd.DataFrame(index=g.index)
    d['name'] = g['name']
    d['人口'] = g.A1101
    # 子ども女性比：0〜5歳人口 ÷ 15〜64歳女性人口 ×1000（出生の多さの目安）
    d[Y] = 1000 * g.A1405 / g.A130202
    d['持ち家率'] = 100 * h.H1310.reindex(d.index) / h.H1101.reindex(d.index)
    d['一戸建て率'] = 100 * h.H1401.reindex(d.index) / h.H1101.reindex(d.index)
    d['65歳以上の割合'] = 100 * g.A1303 / g.A1101
    d['大卒の割合'] = 100 * e.E9106.reindex(d.index) / e.E9101.reindex(d.index)
    ind = g.F2201 + g.F2211 + g.F2221
    d['第1次産業の割合'] = 100 * g.F2201 / ind
    d['log人口密度'] = np.log(g.A1101 / (g.B1103 / 100))
    d['単独世帯の割合'] = 100 * g.A810105 / g.A7101
    d['女性の労働力率'] = 100 * g.F110102 / (g.F110102 + g.F110802)
    d['log所得'] = np.log(g.C120110 / g.C120120 / 10)
    d['pref'] = [c[:2] for c in d.index]
    d = d.replace([np.inf, -np.inf], np.nan)
    d = d.dropna(subset=[Y] + XFULL)
    d = d[d['人口'] > 0]
    return d


def standardize_cols(d, cols, ref=None):
    """平均0・標準偏差1にそろえる（ref があれば ref の平均と標準偏差を使う）"""
    ref = d if ref is None else ref
    z = d.copy()
    for c in cols:
        z[c] = (d[c] - ref[c].mean()) / ref[c].std()
    return z
