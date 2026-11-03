# F129 02 整形：NDBオープンデータ（内服・外来）と人口推計を、薬効分類×都道府県、薬効分類×性×年齢の表にまとめる
import csv, re, sys, pathlib
import openpyxl, pandas as pd
RAW = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'raw')
OUT = pathlib.Path(__file__).resolve().parent.parent / 'data'
AGES = ['0-4','5-9','10-14','15-19','20-24','25-29','30-34','35-39','40-44','45-49','50-54','55-59','60-64','65-69','70-74','75-79','80-84','85+']

def num(x):
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip()
    if s in ('-', '‐', '－', ''): return None  # 1000未満の秘匿
    try: return float(s.replace(',', ''))
    except ValueError: return None

def read_ndb(path, kind):
    wb = openpyxl.load_workbook(path, read_only=True); ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    head = rows[3]
    recs = []; cls = None; cname = None
    for r in rows[4:]:
        if r[0] is not None: cls, cname = int(r[0]), r[1]
        if r[2] is None: continue
        unit, price = r[4], num(r[6]) or 0.0
        vals = r[9:]
        rec = dict(cls=cls, cname=cname, unit=unit, price=price)
        recs.append((rec, vals))
    out = []
    for rec, vals in recs:
        tab = rec['unit'] in ('錠', 'カプセル')
        if kind == 'pref':
            for j in range(47):
                v = num(vals[j]); masked = v is None
                out.append((rec['cls'], rec['cname'], f'{j+1:02d}', v or 0.0, masked, rec['price'], tab))
        else:
            for s, off in (('M', 0), ('F', 21)):
                for j in range(21):
                    v = num(vals[off + j]); masked = v is None
                    a = AGES[min(j, 17)]
                    out.append((rec['cls'], rec['cname'], s, a, v or 0.0, masked, rec['price'], tab))
    return out


def build(year, suffix):
    pref = pd.DataFrame(read_ndb(RAW / f'gaiin_pref{suffix}.xlsx', 'pref'), columns=['cls','cname','pref','qty','masked','price','tab'])
    age = pd.DataFrame(read_ndb(RAW / f'gaiin_age{suffix}.xlsx', 'age'), columns=['cls','cname','sex','age','qty','masked','price','tab'])
    for df in (pref, age):
        df['yen'] = df.qty * df.price
        df['tabs'] = df.qty.where(df.tab, 0.0)
        df['n_masked'] = df.masked.astype(int)
    p = pref.groupby(['cls','cname','pref'], as_index=False)[['yen','tabs','n_masked']].sum()
    a = age.groupby(['cls','cname','sex','age'], as_index=False)[['yen','tabs','n_masked']].sum()
    p.insert(0, 'year', year); a.insert(0, 'year', year)
    return p, a

def read_pop(path, year):
    rows = list(csv.reader(open(path, encoding='utf-8')))
    data = [r for r in rows if r and re.fullmatch(r'\d{5}', r[0].strip())]
    recs = []
    for k, sex in ((1, 'M'), (2, 'F')):
        block = data[48 * k: 48 * (k + 1)]
        for i, r in enumerate(block):
            nums = [float(x.replace(',', '').strip()) for x in r[12:31] if x.strip() != '']
            assert len(nums) == 19, (len(nums), r)
            pref = '00' if i == 0 else f'{i:02d}'
            for a, v in zip(AGES, nums[1:]):
                recs.append((year, pref, sex, a, v * 1000))
    return pd.DataFrame(recs, columns=['year','pref','sex','age','pop'])

if __name__ == '__main__':
    P, A, POP = [], [], []
    for year, suf, popf in ((2024, '', 'f129_pop2024_t10.csv'), (2023, '10', 'f129_pop2023_t10.csv')):
        p, a = build(year, suf); P.append(p); A.append(a)
        POP.append(read_pop(RAW / popf, year))
    pd.concat(P).to_csv(OUT / 'ndb_pref_class.csv', index=False)
    pd.concat(A).to_csv(OUT / 'ndb_sexage_class.csv', index=False)
    pd.concat(POP).to_csv(OUT / 'pop_pref_sex_age.csv', index=False)
    # 院内（2024年度のみ、頑健性用）

    pi = pd.DataFrame(read_ndb(RAW / 'innai_pref.xlsx', 'pref'), columns=['cls','cname','pref','qty','masked','price','tab'])
    ai = pd.DataFrame(read_ndb(RAW / 'innai_age.xlsx', 'age'), columns=['cls','cname','sex','age','qty','masked','price','tab'])
    for df in (pi, ai):
        df['yen'] = df.qty * df.price; df['tabs'] = df.qty.where(df.tab, 0.0); df['n_masked'] = df.masked.astype(int)
    pi.groupby(['cls','cname','pref'], as_index=False)[['yen','tabs','n_masked']].sum().to_csv(OUT / 'ndb_innai_pref_class_2024.csv', index=False)
    ai.groupby(['cls','cname','sex','age'], as_index=False)[['yen','tabs','n_masked']].sum().to_csv(OUT / 'ndb_innai_sexage_class_2024.csv', index=False)
    print('ok')
