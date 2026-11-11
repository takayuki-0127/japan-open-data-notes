# 01 取得：ブラウザで取得した JSON（base64）を元のファイルに戻して data/raw/ に置く
# 取得方法：農林水産省・総務省統計局のページから in-page fetch、日本銀行は API（getDataCode）。
import json, base64, os, sys, re, shutil
SRC = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/Desktop'
RAW = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(RAW, exist_ok=True)
idx = []
for fn, sub in [('f266_maff_kakaku_past.json', 'maff_past'), ('f266_maff_aitai_now.json', 'maff_now'),
                ('f266_maff_pdfs.json', 'maff_pdf'), ('f266_stat_kouri.json', 'stat_kouri')]:
    d = json.load(open(os.path.join(SRC, fn)))
    os.makedirs(os.path.join(RAW, sub), exist_ok=True)
    for x in d:
        if 'b64' not in x: continue
        name = x['u'].split('/')[-1]
        p = os.path.join(RAW, sub, name)
        open(p, 'wb').write(base64.b64decode(x['b64']))
        idx.append({'dir': sub, 'file': name, 'url': x['u'], 'label': x.get('t', ''), 'bytes': os.path.getsize(p)})
shutil.copy(os.path.join(SRC, 'f266_boj_cgpi_rice.csv'), os.path.join(RAW, 'boj_cgpi_rice.csv'))
json.dump(idx, open(os.path.join(RAW, 'index.json'), 'w'), ensure_ascii=False, indent=1)
print(len(idx), 'files')
