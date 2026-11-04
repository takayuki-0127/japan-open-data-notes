# 02 整形：取得したページ本文（data/raw/pages_*.json、GitHub には置かない）から、
# 白書・年ごとに「本文の文」を取り出し、data/raw/sentences.parquet に保存する。
# ・同じ白書・同じ年のページの20%以上に出る行（サイトのメニューなど）を除く
# ・「。」を含まない行（見出し・図表の題・表の行）を除く
# ・「。」で文に分け、5字未満・400字超の文を除く
import json, re, sys, glob, collections
import pandas as pd

RAW = sys.argv[1] if len(sys.argv) > 1 else 'data/raw'
rows = []
for f in sorted(glob.glob(f'{RAW}/pages_*.json')):
    P = json.load(open(f, encoding='utf-8'))
    seen = set(); pages = []
    for p in P:
        k = (p['wp'], p['year'], p['url'])
        if k in seen: continue
        seen.add(k); pages.append(p)
    by = collections.defaultdict(list)
    for p in pages: by[(p['wp'], p['year'])].append(p)
    for (wp, y), ps in by.items():
        ps.sort(key=lambda p: p['ord'])
        cnt = collections.Counter()
        for p in ps:
            for l in set(x.strip() for x in p['text'].split('\n')): cnt[l] += 1
        thr = max(3, 0.2 * len(ps))
        for i, p in enumerate(ps):
            pos = i / max(1, len(ps) - 1)  # ページの順番（0=最初、1=最後）
            for l in p['text'].split('\n'):
                l = l.strip()
                if not l or cnt[l] >= thr or '。' not in l: continue
                l = re.sub(r'^[　\s]+', '', l)
                for s in re.split(r'(?<=。)', l):
                    s = s.strip()
                    if not s.endswith('。'): continue
                    n = len(re.sub(r'\s', '', s))
                    if 5 <= n <= 400:
                        rows.append((wp, y, p['url'], pos, s))
df = pd.DataFrame(rows, columns=['wp', 'year', 'url', 'pos', 'sent'])
df = df[df.year <= 2025].drop_duplicates(['wp', 'year', 'sent'])  # 2026年版は取得時点で一部だけなので除く
df.to_parquet(f'{RAW}/sentences.parquet')
print(df.groupby('wp').agg(years=('year', 'nunique'), y0=('year', 'min'), y1=('year', 'max'), sents=('sent', 'size')))
