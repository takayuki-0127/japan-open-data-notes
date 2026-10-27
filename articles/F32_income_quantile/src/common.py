"""共通：データの読み込みと変数の作成"""
import json, numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261027
QS = [0.1, 0.25, 0.5, 0.75, 0.9]
QGRID = [round(q, 2) for q in np.arange(0.05, 0.951, 0.05)]

plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False

# 説明変数（日本語名 → 作り方）。どれも割合は％
XNAMES = ['65歳以上の割合', '15歳未満の割合', '大卒の割合', '第1次産業の割合', '第2次産業の割合',
          'log人口密度', '単独世帯の割合', '昼夜間人口比率', '雇用者のうち正規の割合']
MAIN5 = ['大卒の割合', '65歳以上の割合', '第1次産業の割合', 'log人口密度', '昼夜間人口比率']


def is_ward(code):
    # 政令指定都市の区（例 01101）は除き、市全体（例 01100）を残す。東京23区は残す
    return code[2] == '1' and code[4] != '0' and code[:2] != '13'


def is_seirei(code):
    # 政令指定都市の市全体（例 01100、14100）
    return code[2] == '1' and code[4] == '0' and code[:2] != '13'


def is_tokyo23(code):
    return code[:2] == '13' and code[2] == '1' and code != '13100'


def wide(year):
    p = pd.read_csv(ROOT / 'data/panel_long.csv', dtype={'code': str})
    return p[p.year == year].set_index('code')


def make_xy(year=2020, edu_year=None):
    """納税者1人あたり所得（万円）と説明変数。大卒の割合は国勢調査の年（2010・2020）の値を使う"""
    g = wide(year)
    e = wide(edu_year or (2020 if year >= 2020 else 2010))
    d = pd.DataFrame(index=g.index)
    d['name'] = g['name']
    d['所得'] = g.C120110 / g.C120120 / 10           # 千円 → 万円
    d['log所得'] = np.log(d['所得'])
    d['65歳以上の割合'] = 100 * g.A1303 / g.A1101
    d['15歳未満の割合'] = 100 * g.A1301 / g.A1101
    d['大卒の割合'] = 100 * e.E9106 / e.E9101
    ind = g.F2201 + g.F2211 + g.F2221
    d['第1次産業の割合'] = 100 * g.F2201 / ind
    d['第2次産業の割合'] = 100 * g.F2211 / ind
    d['log人口密度'] = np.log(g.A1101 / (g.B1103 / 100))   # 可住地 1km2 あたり
    d['単独世帯の割合'] = 100 * g.A810105 / g.A7101
    d['昼夜間人口比率'] = g.A6108
    d['雇用者のうち正規の割合'] = 100 * g.F2409 / g.F2401
    d['人口'] = g.A1101
    d['pref'] = [c[:2] for c in d.index]
    d = d.replace([np.inf, -np.inf], np.nan).dropna()
    return d


def standardize(d, cols=XNAMES):
    z = d.copy()
    for c in cols:
        z[c] = (d[c] - d[c].mean()) / d[c].std()
    return z
