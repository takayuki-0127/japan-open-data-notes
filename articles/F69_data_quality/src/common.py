"""共通：5つの統計表の読み込みと、点検ルール"""
import json, csv, re
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
RES = ROOT / 'results'
FIG = ROOT / 'figures'
SEED = 20261028

# 数値でない「記号」とみなすもの（表の中の値のセル）
SYMBOLS = ['-', '…', '***', 'x', 'X', '/', '', '－', '―', '‐', '…', '...', 'None']


def to_num(s):
    """'1,234' や 1234 を数値に。数値にできなければ None"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).strip().replace(',', '')
    try:
        return float(t)
    except ValueError:
        return None


def sym(s):
    """数値でないセルの記号（そのまま返す）。数値なら None"""
    if to_num(s) is not None:
        return None
    return '' if s is None else str(s).strip()


# ---------------------------------------------------------------- T1 社会・人口統計体系（市区町村）
def load_ssds():
    d = json.load(open(RAW / 'ssds_municipal.json', encoding='utf-8'))
    rows = []
    for key, t in d.items():
        year = int(key[:4])
        head = t[0]
        for r in t[1:]:
            code, name = r[0].split('_', 1)
            for h, v in zip(head[1:], r[1:]):
                item, label = h.split('_', 1)
                unit = re.search(r'【(.*)】', label)
                rows.append((year, code, name, item, label.split(' 【')[0],
                             unit.group(1) if unit else '', str(v).strip(), to_num(v)))
    df = pd.DataFrame(rows, columns=['year', 'code', 'name', 'item', 'label', 'unit', 'raw', 'value'])
    return df.drop_duplicates(['year', 'code', 'item'])


# ---------------------------------------------------------------- T2 家計調査（長期時系列、月次）
def load_kakei():
    out = []
    for sid, kind in [('646', '支出金額'), ('647', '名目増減率'), ('648', '実質増減率')]:
        r = list(csv.reader(open(RAW / f'kakei_000040270{sid}.csv', encoding='utf-8')))
        years = []
        y = None
        for v in r[1][6:]:
            if v.strip():
                y = int(v.replace('年', ''))
            years.append(y)
        months = [int(v.replace('月', '')) for v in r[3][6:]]
        for x in r[4:]:
            if len(x) < 7:
                continue
            item = x[5].strip()
            for j, v in enumerate(x[6:]):
                out.append((kind, x[0], x[1], item, years[j], months[j], v.strip(), to_num(v)))
    return pd.DataFrame(out, columns=['kind', 'row', 'level', 'item', 'year', 'month', 'raw', 'value'])


# ---------------------------------------------------------------- T3 感染症発生動向調査（IDWR 速報、週次）
def load_idwr():
    d = json.load(open(RAW / 'idwr_teiten_flu.json', encoding='utf-8'))
    df = pd.DataFrame(d['rows'], columns=['file', 'week', 'pref', 'reports', 'per_sentinel'])
    df['wk'] = df.file.str.slice(0, 7)
    return df


# ---------------------------------------------------------------- T4 人口動態保健所・市区町村別統計（死亡数・SMR）
def load_vital():
    d = json.load(open(RAW / 'vital_hokenjo_muni.json', encoding='utf-8'))
    names = {'000040174882': '死亡数（第3表）', '000040174884': 'SMR ベイズ推定値（第5表）',
             '000040174885': 'SMR（第6表）'}
    out = []
    for sid, t in d.items():
        for r in t['rows']:
            area = str(r[0]).replace('　', '').strip()
            m = re.match(r'(\d+)(.*)', area)
            code = m.group(1) if m else ''
            kind = 'hokenjo' if '保健所' in area else ('pref' if len(code) == 2 else ('muni' if len(code) == 5 else 'other'))
            for j, v in enumerate(r[1:]):
                out.append((names.get(sid, sid), area, code, kind, j, '' if v is None else str(v).strip(), to_num(v)))
    return pd.DataFrame(out, columns=['table', 'area', 'code', 'kind', 'col', 'raw', 'value'])


# ---------------------------------------------------------------- T5 国勢調査 2020 就業状態等基本集計（都道府県×男女×各歳）
CENSUS_COLS = ['総数', '労働力人口', '就業者', '主に仕事', '家事のほか仕事', '通学のかたわら仕事', '休業者',
               '完全失業者', '非労働力人口', '家事', '通学', 'その他', '不詳', '労働力率']


def load_census():
    d = json.load(open(RAW / 'census2020_lfs_pref.json', encoding='utf-8'))
    rows = [r for r in d['rows'] if r[0] == 'a']
    df = pd.DataFrame([r[1:5] + r[5:] for r in rows],
                      columns=['area', 'nat', 'sex', 'age'] + CENSUS_COLS)
    return df
