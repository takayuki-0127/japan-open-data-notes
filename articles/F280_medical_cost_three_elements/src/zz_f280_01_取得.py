"""F280 01 取得：厚生労働省「医療保険に関する基礎資料」（各年度PDF）と、総務省「人口推計」を取る。

- PDF は data/raw/pdf/ に置く（リポジトリには入れない。.gitignore）。md5 は data/raw/MANIFEST.json。
- PDF から pdftotext -layout で文字を出し、使う3つの節（年齢階級別1人当たり医療費、三要素（入院）、
  三要素（入院外））と「医療費の伸び率の要因分解」だけを、年度ごとに1つのファイル data/raw/sections/<年度>.txt に保存する（これはリポジトリに入れる）。
  pdftotext は日本語の言語パック（poppler-data）が要る。
- 人口推計：長期時系列 第3表（2000〜2020年、statInfId=000013168603）と、各年10月1日現在 第1表
  （2021年 000032191042、2022年 000040045487、2023年 000040166025）。
使い方：python zz_f280_01_取得.py [--download]
  --download を付けないときは、data/raw/pdf/ か data/raw/txt/ にあるものを使う。
"""
import hashlib, json, os, re, subprocess, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'data', 'raw')
YEARS = ['h23','h24','h25','h26','h27','h28','h29','h30','r01','r02','r03','r04','r05']
BASE = 'https://www.mhlw.go.jp/content/kiso_{}.pdf'
POP = {'estat_pop_t3_2000_2020.xlsx': '000013168603', 'estat_pop_t1_2021.xlsx': '000032191042',
       'estat_pop_t1_2022.xlsx': '000040045487', 'estat_pop_t1_2023.xlsx': '000040166025'}

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

def get(url, path):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, 'wb') as f:
        f.write(r.read())

def sections(txt):
    """使う節だけを抜き出す。"""
    L = txt.split('\n')
    out = {}
    def grab(pat, n=60, last=True):
        idx = [i for i, l in enumerate(L) if re.search(pat, l)]
        if not idx:
            return None
        i = idx[-1] if last else idx[0]
        return '\n'.join(L[i:i + n])
    out['cost'] = grab(r'年齢階級別１人当たり医療費（.*年度.*医療保険')
    out['in'] = grab(r'三要素（入院、')
    out['out'] = grab(r'三要素（入院外、')
    out['decomp'] = grab(r'医療費の伸び率の要因分解', n=70)
    return out

def main():
    dl = '--download' in sys.argv
    os.makedirs(os.path.join(RAW, 'pdf'), exist_ok=True)
    os.makedirs(os.path.join(RAW, 'txt'), exist_ok=True)
    os.makedirs(os.path.join(RAW, 'sections'), exist_ok=True)
    man = {}
    for y in YEARS:
        pdf = os.path.join(RAW, 'pdf', f'kiso_{y}.pdf')
        txt = os.path.join(RAW, 'txt', f'kiso_{y}.txt')
        if dl and not os.path.exists(pdf):
            get(BASE.format(y), pdf)
        if os.path.exists(pdf):
            man[f'kiso_{y}.pdf'] = md5(pdf)
            if not os.path.exists(txt):
                subprocess.run(['pdftotext', '-layout', pdf, txt], check=True)
        if os.path.exists(txt):
            s = sections(open(txt, encoding='utf-8').read())
            body = ''.join(f'##### {k}\n{v}\n' for k, v in s.items() if v)
            open(os.path.join(RAW, 'sections', f'{y}.txt'), 'w', encoding='utf-8').write(body)
    for f, sid in POP.items():
        p = os.path.join(RAW, f)
        if dl and not os.path.exists(p):
            get(f'https://www.e-stat.go.jp/stat-search/file-download?statInfId={sid}&fileKind=0', p)
        if os.path.exists(p):
            man[f] = md5(p)
    old = {}
    mp = os.path.join(RAW, 'MANIFEST.json')
    if os.path.exists(mp):
        old = json.load(open(mp))
    for k, v in man.items():
        if k in old and old[k] != v:
            print('md5 が違う：', k)
    old.update(man)
    json.dump(old, open(mp, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    print('ok', len(man), 'files')

if __name__ == '__main__':
    main()
