"""01 取得：F01〜F120 の README（言えないこと・手法）と、作業ログの「設計から変えたこと」を1行1項目の表にする。
README は japan-open-data-notes の articles/ 以下にある。作業ログは data/design_changes_raw.tsv に同梱。"""
import re, glob, sys, csv, pathlib
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '..')   # articles/ フォルダ
OUT = pathlib.Path(__file__).resolve().parent.parent / 'data'
fs = sorted(glob.glob(str(ROOT / 'F[0-9]*' / 'README.md')), key=lambda p: int(re.search(r'/F(\d+)_', p).group(1)))
rows = []
for f in fs:
    fid = 'F' + re.search(r'/F(\d+)_', f).group(1)
    if int(fid[1:]) > 120: continue
    txt = open(f, encoding='utf-8').read()
    title = txt.splitlines()[0].lstrip('# ').strip()
    # 手法：見出し「手法」の本文 + タイトルの（ ）
    m = re.search(r'\n## 手法[^\n]*\n(.*?)(?=\n## )', txt, re.S)
    meth = (m.group(1) if m else '')
    paren = re.findall(r'（([^）]*)）', title)
    rows.append(dict(fid=fid, kind='title', text=title))
    rows.append(dict(fid=fid, kind='method', text=(' '.join(paren) + ' ' + meth)[:1500].replace('\n', ' ')))
    # 言えないこと
    m = re.search(r'\n## [^\n]*言えないこと[^\n]*\n(.*?)(?=\n## |\Z)', txt, re.S)
    if m:
        for l in m.group(1).splitlines():
            l = l.strip()
            if l.startswith(('- ', '* ', '・')) or re.match(r'\d+\. ', l):
                rows.append(dict(fid=fid, kind='cannot', text=re.sub(r'^(- |\* |・|\d+\. )', '', l)))
    # 設計からの変更（README にある場合）
    m = re.search(r'\n## 設計[^\n]*\n(.*?)(?=\n## |\Z)', txt, re.S)
    if m:
        for l in m.group(1).splitlines():
            l = l.strip()
            if l.startswith(('- ', '* ', '・')):
                rows.append(dict(fid=fid, kind='change_readme', text=l[2:]))
# 作業ログ（設計から変えたこと）
for l in open(OUT / 'design_changes_raw.tsv', encoding='utf-8'):
    fid, txt = l.rstrip('\n').split('\t', 1)
    for it in re.split(r'[。；;]|、(?=[^、]{0,40}(?:→|は|を|で))', txt):
        it = it.strip(' 、')
        if len(it) >= 6:
            rows.append(dict(fid=fid, kind='change', text=it))
with open(OUT / 'items.csv', 'w', newline='', encoding='utf-8') as fo:
    w = csv.DictWriter(fo, fieldnames=['fid', 'kind', 'text']); w.writeheader(); w.writerows(rows)
print(len(fs), 'READMEs', len(rows), 'rows')
