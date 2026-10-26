"""共通：変数の作成"""
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SEED = 20261026


def wide():
    p = pd.read_csv(ROOT / 'data/panel_long.csv', dtype={'code': str})
    w = {}
    for y, g in p.groupby('year'):
        w[y] = g.set_index('code')
    return w


def lfpr(g):
    """女性の労働力率（%）＝労働力人口（女）÷（労働力人口（女）＋非労働力人口（女））"""
    return 100 * g.F110102 / (g.F110102 + g.F110802)


def emp(g):
    """女性の就業率（%）＝就業者数（女）÷（労働力人口（女）＋非労働力人口（女））"""
    return 100 * g.F110202 / (g.F110102 + g.F110802)


def enroll(g, kodomoen=False):
    """保育所等に通う子ども（0〜5歳100人あたり）"""
    n = g.J2506.copy()
    if kodomoen:
        n = n + g.J2545.fillna(0) + g.J2546.fillna(0)
    return 100 * n / g.A1405


def covariates(w, base=2010):
    """2010年の地域の性格（水準）と、2005→10年の変化（前の傾向）"""
    g = w[base]; g5 = w[2005]
    W15 = g.F110102 + g.F110802            # 15歳以上の女性（労働力状態が分かる人）
    X = pd.DataFrame(index=g.index)
    X['log人口'] = np.log(g.A1101)
    X['log人口密度'] = np.log(g.A1101 / g.B1103)
    X['女性65歳以上の割合'] = 100 * g.A130302 / g.A110102
    X['女性15〜64歳の割合'] = 100 * g.A130202 / g.A110102
    X['0〜5歳の割合'] = 100 * g.A1405 / g.A1101
    X['0〜3歳の割合'] = 100 * g.A1404 / g.A1101
    X['出生率（人口千人あたり）'] = 1000 * g.A4101 / g.A1101
    X['核家族世帯の割合'] = 100 * g.A810102 / g.A7101
    X['単独世帯の割合'] = 100 * g.A810105 / g.A7101
    X['核家族以外の世帯の割合'] = 100 * g.A810103 / g.A7101
    X['母子世帯の割合'] = 100 * g.A8401 / g.A7101
    X['第1次産業の割合'] = 100 * g.F2201 / g.F1102
    X['第2次産業の割合'] = 100 * g.F2211 / g.F1102
    X['第3次産業の割合'] = 100 * g.F2221 / g.F1102
    X['女性の市外への通勤の割合'] = 100 * g.F270502 / g.F110202
    X['昼夜間人口比率'] = g.A6108
    X['納税者1人あたり所得'] = g.C120110 / g.C120120
    X['納税者の割合'] = 100 * g.C120120 / g.A1101
    X['財政力指数'] = g.D2201
    X['子ども1人あたり児童福祉費'] = g.D3203033 / g.A1301
    X['大卒の割合'] = 100 * g.E9106 / g.E9101
    X['短大・高専卒の割合'] = 100 * g.E9105 / g.E9101
    X['雇用者のうち正規の割合'] = 100 * g.F2409 / g.F2401
    X['雇用者のうちパートの割合'] = 100 * g.F2411 / g.F2401
    X['保育所等に通う子ども（2010）'] = enroll(g)
    X['女性の労働力率（2010）'] = lfpr(g)
    X['前の5年の労働力率の変化'] = lfpr(g) - lfpr(g5)
    X['前の5年の在所児の変化'] = enroll(g) - enroll(g5)
    X['前の5年の人口増減率'] = 100 * (g.A1101 / g5.A1101 - 1)
    # 財政力指数は東京23区などで空欄。中央値で埋め、空欄だったことを示す列を足す
    X['財政力指数が空欄'] = X['財政力指数'].isna().astype(float)
    X['財政力指数'] = X['財政力指数'].fillna(X['財政力指数'].median())
    return X


def change_controls(w, a=2010, b=2015):
    """同じ期間の年齢構成などの変化（就業率の変化のうち年齢で決まる分を取り除く）"""
    ga, gb = w[a], w[b]
    C = pd.DataFrame(index=ga.index)
    C['女性65歳以上の割合の変化'] = 100 * (gb.A130302 / gb.A110102 - ga.A130302 / ga.A110102)
    C['女性15〜64歳の割合の変化'] = 100 * (gb.A130202 / gb.A110102 - ga.A130202 / ga.A110102)
    C['0〜5歳の割合の変化'] = 100 * (gb.A1405 / gb.A1101 - ga.A1405 / ga.A1101)
    C['人口増減率'] = 100 * (gb.A1101 / ga.A1101 - 1)
    return C


def pref_dummies(idx):
    pref = pd.Series([c[:2] for c in idx], index=idx)
    return pd.get_dummies(pref, prefix='県', drop_first=True).astype(float)
