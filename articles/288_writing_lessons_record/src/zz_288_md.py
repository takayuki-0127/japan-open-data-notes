"""手元の記事 md（note の下書きの原稿）を1本ずつ数えて md_stats.csv に書く
使い方: python zz_288_md.py <md のフォルダ> <出力 csv>
対象：ファイル名が「番号_」「F番号_」「T番号_」で始まる .md
"""
import os, re, sys, csv
D, out = sys.argv[1], sys.argv[2]
IMG = re.compile(r'\s*(!\[|［図[：:])')
rows = []
for fn in sorted(os.listdir(D)):
    m = re.match(r'^(F|T)?(\d+)_.*\.md$', fn)
    if not m:
        continue
    s = open(os.path.join(D, fn), encoding='utf-8').read()
    L = s.split('\n')
    t = next((l[2:].strip() for l in L if l.startswith('# ')), '')
    imgs = sum(1 for l in L if IMG.match(l))
    body = '\n'.join(l for l in L if not IMG.match(l) and not l.startswith('# '))
    body = re.sub(r'https?://\S+', '', body)
    chars = len(re.sub(r'\s', '', body))
    h2 = sum(1 for l in L if l.startswith('## '))
    top = [l for l in L if l.strip()][:12]
    wakaru = any('この記事で分かる' in l for l in top)
    ienai = any(re.search(r'言えないこと|分からないこと|わからないこと|限界', l) for l in L if l.startswith('#')) or bool(re.search(r'\n言えないこと[：:]', s))
    sents = [x for x in re.split(r'。', body) if len(x.strip()) > 3]
    slen = sum(len(re.sub(r'\s', '', x)) for x in sents) / max(1, len(sents))
    rows.append(dict(file_num=(m.group(1) or '') + m.group(2), prefix=m.group(1) or '', num=int(m.group(2)),
                     title_len=len(t), title_q=int('？' in t or '?' in t), title_digits=int(bool(re.search(r'\d', t))),
                     title_after_q=len(t.split('？', 1)[1]) if '？' in t else 0, chars=chars, images=imgs, h2=h2,
                     wakaru_top=int(wakaru), ienai=int(ienai), suisoku=s.count('推測'), sent_len=round(slen, 1)))
w = csv.DictWriter(open(out, 'w', newline='', encoding='utf-8'), fieldnames=list(rows[0]))
w.writeheader(); w.writerows(rows); print(len(rows))
