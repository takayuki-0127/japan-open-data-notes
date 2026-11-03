# 商業動態統計（経済産業省）の月次表を、業態×地域×月の長い表に整える
import json, re, pandas as pd, pathlib
A = pathlib.Path(__file__).resolve().parents[1]
d = json.load(open(A/'data/raw/f135_meti_monthly.json'))

def ym(s):
    m = re.match(r'(\d{4})年\s*(\d{1,2})月', str(s))
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else None

def num(x):
    try: return float(str(x).replace(',', ''))
    except: return None

rows = []
# 百貨店・スーパー（全国・商品別）：販売額と既存店伸び率
for gy, key in [('百貨店', '百貨店'), ('スーパー', 'スーパー')]:
    for kind in ['販売額', '既存店']:
        tab = d['h2slt31j'][f'{key}　{kind}　月次']
        hdr = next(r for r in tab if r and len(r) > 3 and r[2] == '合計')
        for r in tab:
            t = next((ym(c) for c in r[:3] if ym(c)), None)
            if not t: continue
            for j, name in enumerate(hdr):
                if j < 2 or name is None: continue
                v = num(r[j])
                if v is not None:
                    rows.append(dict(ym=t, 業態=gy, 地域='全国', 品目=name, 指標=kind, 値=v))

# コンビニ・家電・ドラッグ・ホームセンター：全国の販売額と経済産業局別の販売額
for f, gy in [('h2slt41j', 'コンビニ'), ('h2slt42j', '家電大型専門店'), ('h2slt43j', 'ドラッグストア'), ('h2slt44j', 'ホームセンター')]:
    o = d[f]
    nat = [k for k in o if '局別' not in k][0]
    tab = o[nat]
    hdr = next(r for r in tab if r and any(c in ('合計', '商品販売額') for c in r if isinstance(c, str)))
    for r in tab:
        t = next((ym(c) for c in r[:4] if ym(c)), None)
        if not t: continue
        for j, name in enumerate(hdr):
            if not isinstance(name, str) or '店舗数' in name: continue
            v = num(r[j])
            if v is not None:
                rows.append(dict(ym=t, 業態=gy, 地域='全国', 品目=name, 指標='販売額', 値=v))
    tab = o[[k for k in o if '局別' in k][0]]
    reg = next(r for r in tab if r and sum(isinstance(c, str) and ('経済産業局' in c or '総合事務局' in c) for c in r) >= 5)
    kind = next(r for r in tab if r and any(c == '販売額' for c in r))
    for r in tab:
        t = next((ym(c) for c in r[:4] if ym(c)), None)
        if not t: continue
        for j, (rg, kd) in enumerate(zip(reg, kind)):
            if isinstance(rg, str) and '経済産業局' in rg and '＋' not in rg and kd == '販売額':
                v = num(r[j])
                if v is not None:
                    rows.append(dict(ym=t, 業態=gy, 地域=rg.replace('経済産業局', '').replace('沖縄総合事務局', '沖縄'), 品目='販売額', 指標='販売額', 値=v))
    for j, rg in enumerate(reg):
        if isinstance(rg, str) and '沖縄' in rg and kind[j] == '販売額':
            for r in tab:
                t = next((ym(c) for c in r[:4] if ym(c)), None)
                v = num(r[j]) if t else None
                if v is not None:
                    rows.append(dict(ym=t, 業態=gy, 地域='沖縄', 品目='販売額', 指標='販売額', 値=v))

df = pd.DataFrame(rows).drop_duplicates(['ym', '業態', '地域', '品目', '指標'])
df.to_csv(A/'data/retail_monthly.csv', index=False)
print(df.groupby(['業態', '地域', '指標']).agg(n=('値', 'size'), start=('ym', 'min'), end=('ym', 'max')).to_string())
print(df[df.地域 == '全国'].groupby('業態').品目.unique().to_string())
