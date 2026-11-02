# 02 整形：介護保険事業状況報告（年報）の保険者別の表を、1行＝1保険者×1年度の表にする
import json, csv, io, re
import pandas as pd

RAW = 'data/raw/f130_kaigo_nenpo.json'
d = json.load(open(RAW, encoding='utf-8'))
YEARS = {'R2': 2020, 'R3': 2021, 'R4': 2022, 'R5': 2023, 'R6': 2024}
LEVELS = ['要支援1', '要支援2', '要介護1', '要介護2', '要介護3', '要介護4', '要介護5', '合計']
BANDS = {'③': '65_69', '④': '70_74', '⑤': '75_79', '⑥': '80_84', '⑦': '85_89', '⑧': '90p'}

def num(x):
    x = str(x).strip().replace(',', '')
    if x in ('', '-', '－', '…'):
        return 0.0
    try:
        return float(x)
    except ValueError:
        return None

def rows(text):
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 3:
            continue
        pref, ins = r[0].strip(), r[1].strip()
        if not pref or not ins or pref.startswith('全') or pref == '都道府県':
            continue
        yield pref, ins, r[2:]

out = {}
for yk, yr in YEARS.items():
    for pref, ins, v in rows(d[f'{yk}__02h__02h']):
        vals = [num(x) for x in v[:6]]
        if vals[0] is None:
            continue
        out[(yr, pref, ins)] = dict(year=yr, pref=pref, insurer=ins, ins_total=vals[0],
                                    ins_6574=vals[1], ins_7584=vals[2], ins_85p=vals[3])
    for s, b in BANDS.items():
        for pref, ins, v in rows(d[f'{yk}__04-1-1h__04-1-1h{s}']):
            key = (yr, pref, ins)
            if key not in out:
                continue
            vals = [num(x) for x in v[:8]]
            for lv, x in zip(LEVELS, vals):
                out[key][f'c_{b}_{lv}'] = x
    for pref, ins, v in rows(d[f'{yk}__04-1-1h__04-1-1h②']):
        key = (yr, pref, ins)
        if key in out:
            out[key]['c_1go_total'] = num(v[7])

df = pd.DataFrame(out.values())
cols = [c for c in df.columns if c.startswith('c_')]
df[cols] = df[cols].fillna(0)
df = df.dropna(subset=['ins_total'])
df = df[df.ins_total > 0]
# 年齢の帯を3つにまとめる
for lv in LEVELS:
    df[f'c6574_{lv}'] = df[f'c_65_69_{lv}'] + df[f'c_70_74_{lv}']
    df[f'c7584_{lv}'] = df[f'c_75_79_{lv}'] + df[f'c_80_84_{lv}']
    df[f'c85p_{lv}'] = df[f'c_85_89_{lv}'] + df[f'c_90p_{lv}']
chk = (df['c6574_合計'] + df['c7584_合計'] + df['c85p_合計'] - df['c_1go_total']).abs().max()
chk2 = (df.ins_6574 + df.ins_7584 + df.ins_85p - df.ins_total).abs().max()
print('years', df.year.value_counts().sort_index().to_dict())
print('max diff: certified bands vs 1go total =', chk, '; insured bands vs total =', chk2)
keep = ['year', 'pref', 'insurer', 'ins_total', 'ins_6574', 'ins_7584', 'ins_85p', 'c_1go_total'] + \
       [f'c{b}_{lv}' for b in ['6574', '7584', '85p'] for lv in LEVELS] + \
       [f'c_{b}_合計' for b in BANDS.values()]
df[keep].to_csv('data/insurer_panel.csv', index=False, encoding='utf-8')
print(df[keep].shape)
