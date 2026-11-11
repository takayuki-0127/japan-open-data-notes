"""F280 02 整形：節のテキストから年齢階級別の値を読み、人口と合わせて1つの表にする。

出力：data/processed/panel.csv（年度×5歳階級：1人当たり医療費、入院と入院外の三要素、人口）
      data/processed/revision.csv（診療報酬改定等の率、公表の要因分解）
"""
import os, re, json
import pandas as pd
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'data', 'raw')
OUT = os.path.join(HERE, '..', 'data', 'processed')
YEARS = {'h23': 2011, 'h24': 2012, 'h25': 2013, 'h26': 2014, 'h27': 2015, 'h28': 2016, 'h29': 2017,
         'h30': 2018, 'r01': 2019, 'r02': 2020, 'r03': 2021, 'r04': 2022, 'r05': 2023}
AGES = [f'{a}-{a+4}' for a in range(0, 100, 5)] + ['100+']
ROW = re.compile(r'^\s*(?:（歳）)?\s*(\d{1,3})\s*～\s*(\d{0,2})\s+(.*)$')
NUM = re.compile(r'(?<![\d.])(\d+\.\d+|\d+)(?![\d.%])')

def age_key(a, b):
    a = int(a)
    return '100+' if a == 100 else f'{a}-{a+4}'

def section(tag, key):
    """data/raw/sections/<年度>.txt から、##### key の節の文字を返す。"""
    t = open(os.path.join(RAW, 'sections', f'{tag}.txt'), encoding='utf-8').read()
    parts = re.split(r'^##### (\w+)\n', t, flags=re.M)
    d = dict(zip(parts[1::2], parts[2::2]))
    return d[key]

def parse(text, n):
    """年齢の行から、先頭 n 個の数（% のつかないもの）を読む。
    ページの切れ目で数が年齢のない行に分かれたときは、前後8行の「年齢のない行」から足りない数を補う。"""
    L = text.replace('〜', '～').replace('~', '～').split('\n')
    def nums_of(t):
        return [float(x) for x in NUM.findall(re.sub(r'\d+%', ' ', t))]
    res, used = {}, set()
    for j, l in enumerate(L):
        m = ROW.match(l)
        if not m:
            continue
        k = age_key(m.group(1), m.group(2))
        if k in res:
            continue
        nums = nums_of(m.group(3))
        if len(nums) < n:
            for jj in list(range(j - 1, max(-1, j - 9), -1)) + list(range(j + 1, min(len(L), j + 9))):
                if jj in used or ROW.match(L[jj]) or '年齢' in L[jj] or '%' in L[jj]:
                    continue
                extra = nums_of(L[jj])
                if len(extra) == n - len(nums):
                    nums = nums + extra if jj < j else nums + extra
                    used.add(jj)
                    break
        if len(nums) >= n:
            res[k] = nums[:n]
    return res

def pop_table():
    """総人口・男女計、5歳階級（千人）、2011〜2023年。"""
    pop = {}
    seen = set()  # 表の上（人口・千人）の行だけを使い、下の割合（%）の行は使わない
    wb = openpyxl.load_workbook(os.path.join(RAW, 'estat_pop_t3_2000_2020.xlsx'), read_only=True, data_only=True)
    for sh in ['総人口　男女計（2000年～2015年）', '総人口　男女計 (2015年～2020年)']:
        rows = list(wb[sh].iter_rows(values_only=True))
        yrow = [r for r in rows if r and r[0] == 'Age groups'][0]
        cols = {i: int(v.strip().replace('年', '')) for i, v in enumerate(yrow) if isinstance(v, str) and v.strip().replace('年', '').isdigit()}
        for r in rows:
            if not r or not isinstance(r[0], str):
                continue
            lab = r[0].replace(' ', '').replace('　', '')
            m = re.match(r'^(\d+)～(\d+)(歳)?$', lab)
            if m and int(m.group(2)) == int(m.group(1)) + 4:
                k = age_key(m.group(1), m.group(2))
            elif lab.startswith('100歳以上'):
                k = '100+'
            else:
                continue
            for i, y in cols.items():
                if r[i] is not None and 2011 <= y <= 2020 and (y, k) not in seen:
                    pop[(y, k)] = float(r[i]); seen.add((y, k))
    for y in (2021, 2022, 2023):
        ws = openpyxl.load_workbook(os.path.join(RAW, f'estat_pop_t1_{y}.xlsx'), read_only=True).worksheets[0]
        acc = {}
        for r in ws.iter_rows(values_only=True):
            lab = r[9] if len(r) > 9 else None
            if not isinstance(lab, str):
                continue
            m = re.match(r'^(\d+)歳', lab)
            if not m:
                continue
            a = int(m.group(1))
            k = '100+' if a >= 100 else f'{a//5*5}-{a//5*5+4}'
            acc[k] = acc.get(k, 0) + float(r[10])
        for k, v in acc.items():
            pop[(y, k)] = v
    return pop

def main():
    os.makedirs(OUT, exist_ok=True)
    pop = pop_table()
    rows = []
    for tag, y in YEARS.items():
        c = parse(section(tag, 'cost'), 1)
        i = parse(section(tag, 'in'), 3)
        o = parse(section(tag, 'out'), 3)
        for a in AGES:
            assert a in c and a in i and a in o, (tag, a, a in c, a in i, a in o)
            rows.append(dict(fy=y, age=a, cost_man=c[a][0], in_r=i[a][0], in_d=i[a][1], in_p=i[a][2],
                             out_r=o[a][0], out_d=o[a][1], out_p=o[a][2], pop_k=pop[(y, a)]))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, 'panel.csv'), index=False)
    # 診療報酬改定等（基礎資料 令和5年度版 参考1-2 を書き写した値、%）。空欄の年度は0。
    rev = pd.DataFrame({'fy': list(range(2011, 2024)),
        'revision_pct': [0, 0.004, 0, -1.26 + 1.36, 0, -1.33, 0, -1.19, -0.07, -0.46, -0.9, -0.94, -0.64],
        'official_growth_pct': [3.1, 1.6, 2.2, 1.9, 3.8, -0.5, 2.2, 0.8, 2.3, -3.2, 4.8, 3.7, 3.0],
        'official_pop_pct': [-0.2, -0.2, -0.2, -0.2, -0.1, -0.1, -0.2, -0.2, -0.2, -0.3, -0.5, -0.4, -0.5],
        'official_aging_pct': [1.2, 1.4, 1.3, 1.2, 1.0, 1.0, 1.2, 1.1, 1.0, 1.0, 1.1, 0.9, 0.7],
        'official_other_pct': [2.1, 0.4, 1.1, 0.7, 2.9, -0.1, 1.2, 1.1, 1.6, -3.5, 5.1, 4.2, 3.4]})
    rev.to_csv(os.path.join(OUT, 'revision.csv'), index=False)
    print(df.groupby('fy').size().to_dict())
    print(df[df.fy.isin([2011, 2023])].head(3).to_string())

if __name__ == '__main__':
    main()
