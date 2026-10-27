"""共通：パス・フォント・市区町村コードの判定・格差の指標"""
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261027
YEARS = [2005, 2010, 2015, 2017, 2020]
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False

PREF = ['北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県','茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県',
        '新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県','静岡県','愛知県','三重県','滋賀県','京都府','大阪府','兵庫県',
        '奈良県','和歌山県','鳥取県','島根県','岡山県','広島県','山口県','徳島県','香川県','愛媛県','高知県','福岡県','佐賀県','長崎県',
        '熊本県','大分県','宮崎県','鹿児島県','沖縄県']
BLOCK = {}
for p in range(1, 48):
    BLOCK[p] = ('北海道' if p == 1 else '東北' if p <= 7 else '関東' if p <= 14 else '中部' if p <= 23 else
                '近畿' if p <= 30 else '中国' if p <= 35 else '四国' if p <= 39 else '九州・沖縄')
METRO = {11, 12, 13, 14, 21, 22, 23, 24, 25, 26, 27, 28, 29}  # 3大都市圏の都府県（東京圏・名古屋圏・大阪圏）
METRO = {11, 12, 13, 14, 23, 26, 27, 28}  # 狭め：首都圏1都3県＋愛知＋京都・大阪・兵庫


def is_ward(code):
    """政令指定都市の区（例 01101）。東京23区は残す"""
    return code[2] == '1' and code[4] != '0' and code[:2] != '13'


def is_tokyo23(code):
    return code[:2] == '13' and code[2] == '1' and code != '13100'


def theil_T(y, w):
    """タイル指数 T（所得で重みづけ）。y=1人あたり所得、w=人数"""
    y = np.asarray(y, float); w = np.asarray(w, float)
    mu = np.sum(w * y) / w.sum(); s = w * y / np.sum(w * y)
    return float(np.sum(s * np.log(y / mu)))


def theil_L(y, w):
    """平均対数偏差（MLD、タイル指数 L）。人数で重みづけ"""
    y = np.asarray(y, float); w = np.asarray(w, float)
    mu = np.sum(w * y) / w.sum(); p = w / w.sum()
    return float(np.sum(p * np.log(mu / y)))


def gini(y, w):
    """人数で重みづけしたジニ係数"""
    y = np.asarray(y, float); w = np.asarray(w, float)
    o = np.argsort(y); y, w = y[o], w[o]
    cw = np.cumsum(w) / w.sum(); cy = np.cumsum(w * y) / np.sum(w * y)
    cw0 = np.r_[0, cw[:-1]]; cy0 = np.r_[0, cy[:-1]]
    return float(1 - np.sum((cw - cw0) * (cy + cy0)))


def decompose(df, group, ycol='y', wcol='w', kind='T'):
    """タイル指数を「グループの間」と「グループの中」に分ける。
    T：between = Σ s_g ln(μ_g/μ)、within = Σ s_g T_g（s_g はグループの所得の割合）
    L：between = Σ p_g ln(μ/μ_g)、within = Σ p_g L_g（p_g はグループの人数の割合）"""
    f = theil_T if kind == 'T' else theil_L
    tot = f(df[ycol], df[wcol]); mu = np.sum(df[wcol] * df[ycol]) / df[wcol].sum()
    rows = []
    for g, d in df.groupby(group):
        W = d[wcol].sum(); Y = np.sum(d[wcol] * d[ycol]); mug = Y / W
        share = Y / np.sum(df[wcol] * df[ycol]) if kind == 'T' else W / df[wcol].sum()
        rows.append({'group': g, 'mu': mug, 'share': share, 'inner': f(d[ycol], d[wcol]) if len(d) > 1 else 0.0,
                     'n': len(d)})
    g = pd.DataFrame(rows)
    if kind == 'T':
        between = float(np.sum(g.share * np.log(g.mu / mu)))
    else:
        between = float(np.sum(g.share * np.log(mu / g.mu)))
    g['within_contrib'] = g.share * g.inner
    within = float(g.within_contrib.sum())
    return {'total': tot, 'between': between, 'within': within, 'between_share': between / tot}, g
