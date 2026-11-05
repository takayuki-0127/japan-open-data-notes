"""F01〜F199 の看板記事の README を、コミットを固定して取得する（raw.githubusercontent.com）"""
import os, json, re, time, urllib.request
COMMIT = 'de38ce51a03d811f05262a534e9c6662545f1d90'  # 2026-11-05 時点の main（F199 まで）
BASE = f'https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/{COMMIT}/articles/'
D = os.path.join(os.path.dirname(__file__), '..', 'data')
R = os.path.join(D, 'raw'); os.makedirs(R, exist_ok=True)
folders = [l.strip() for l in open(os.path.join(D, 'folders.txt'), encoding='utf-8') if l.strip()]
for f in folders:
    p = os.path.join(R, f + '.md')
    if os.path.exists(p): continue
    with urllib.request.urlopen(BASE + urllib.request.quote(f) + '/README.md', timeout=60) as r:
        open(p, 'wb').write(r.read())
    time.sleep(0.2)
# 見出し「## 」で本文を区切る
def sections(t):
    out, cur = {}, '_head'
    for line in t.split('\n'):
        m = re.match(r'##\s+(.+)', line)
        if m and not line.startswith('###'): cur = m.group(1).strip(); out.setdefault(cur, ''); continue
        out[cur] = out.get(cur, '') + line + '\n'
    return out
rows = []
for f in folders:
    t = open(os.path.join(R, f + '.md'), encoding='utf-8').read()
    s = sections(t)
    pick = lambda keys: '\n'.join(v for k, v in s.items() if any(k.startswith(x) for x in keys))
    title = t.split('\n', 1)[0].lstrip('# ').strip()
    num = int(re.match(r'F(\d+)_', f).group(1))
    rows.append(dict(article=f, num=num, title=title,
                     method_sec=pick(['手法', '方法']),
                     data_sec=pick(['データ', '出典', 'このデータ']),
                     robust_sec=pick(['頑健性']),
                     full=t))
json.dump(rows, open(os.path.join(D, 'readme_sections.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(len(rows), 'articles; no method section:', [r['article'] for r in rows if not r['method_sec'].strip()])
