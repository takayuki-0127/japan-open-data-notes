"""F01〜F120 の README と src から、使ったデータと記事どうしの再利用を集める（このリポジトリの中だけで完結）"""
import re, glob, os, json, csv
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data')
rows, secs = [], []
for d in sorted(glob.glob(os.path.join(ROOT, 'F*'))):
    name = os.path.basename(d)
    m = re.match(r'F(\d+)_', name)
    if not m: continue
    n = int(m.group(1))
    if n > 120: continue
    t = open(os.path.join(d, 'README.md'), encoding='utf-8').read()
    title = t.split('\n', 1)[0].lstrip('# ').strip()
    def sec(pat):
        out = []
        for mm in re.finditer(r'\n## ([^\n]*)\n(.*?)(?=\n## |\Z)', t, re.S):
            if re.search(pat, mm.group(1)): out.append(mm.group(2))
        return '\n'.join(out)
    data_sec = sec(r'データ|使う記事|共通の単位|答え合わせの対象')
    src_sec = sec(r'出典')
    issue_sec = sec(r'設計から|変えた|言えない|注意|つまず')
    code = ''
    for f in glob.glob(os.path.join(d, 'src', '*')):
        if os.path.isfile(f) and f.endswith(('.py', '.js', '.R', '.sql')):
            code += open(f, encoding='utf-8', errors='ignore').read() + '\n'
    size = 0; nfiles = 0
    for root, _, files in os.walk(os.path.join(d, 'data')):
        for f in files:
            size += os.path.getsize(os.path.join(root, f)); nfiles += 1
    rows.append(dict(article=f'F{n:02d}' if n < 100 else f'F{n}', num=n, folder=name, title=title,
                     data_sec=data_sec, src_sec=src_sec, issue_sec=issue_sec, code=code,
                     data_bytes=size, data_files=nfiles))
json.dump(rows, open(os.path.join(OUT, 'readme_sections.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(len(rows), 'articles')
