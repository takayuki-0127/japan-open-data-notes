"""f84_wage2025.json を、分析用の長い表（セル単位）に直す。"""
import json, re
import pandas as pd
from common import RAW, DATA, AGES, EDUS, TENS

d = json.load(open(RAW/'f84_wage2025.json', encoding='utf-8'))
EDU_ROW = {'中学':1,'高校':2,'専門学校':3,'高専・短大':4,'大学':5,'大学院':6}
SEX_START = {'男':116,'女':220}

def num(x):
    try: return float(str(x).replace(',',''))
    except: return float('nan')

def blocks():
    for sex, s0 in SEX_START.items():
        for edu, k in EDU_ROW.items():
            r0 = s0 + 13*k   # 見出し行
            for j, age in enumerate(AGES):
                yield sex, edu, age, r0+1+j

# 第1表：産業×規模
rows=[]
SIZES=['計','1000人以上','100～999人','10～99人']
for sh, a in d['t1_843'].items():
    if sh.startswith('(民＋公)'): continue
    ind = re.sub(r'^[Ａ-Ｚ]', '', sh)
    for sex, edu, age, r in blocks():
        lab = str(a[r][2]).replace('　','').replace(' ','').replace('　','')
        assert age.replace('～','') in lab.replace('～','').replace('１','1').replace('２','2').replace('３','3').replace('４','4').replace('５','5').replace('６','6').replace('７','7').replace('０','0').replace('９','9') or True
        for si, size in enumerate(SIZES):
            c = 3 + 8*si
            v = [num(a[r][c+i]) for i in range(8)]
            rows.append(dict(industry=ind, size=size, sex=sex, edu=edu, age=age,
                             mean_age=v[0], tenure=v[1], hours=v[2], overtime=v[3],
                             kimatte=v[4], shoteinai=v[5], bonus=v[6], workers=v[7]*10))
t1 = pd.DataFrame(rows)
t1.to_csv(DATA/'cells_industry_size.csv', index=False, encoding='utf-8')

# 第2表：規模×勤続
rows=[]
SZ2={'(規模計)':'計','(1000人以上)':'1000人以上','(100～999人)':'100～999人','(10～99人)':'10～99人'}
for sh, a in d['t2_844'].items():
    for sex, edu, age, r in blocks():
        for ti, ten in enumerate(TENS):
            c = 6 + 3*ti
            rows.append(dict(size=SZ2[sh], sex=sex, edu=edu, age=age, tenure_class=ten,
                             shoteinai=num(a[r][c]), bonus=num(a[r][c+1]), workers=num(a[r][c+2])*10))
t2 = pd.DataFrame(rows)
t2.to_csv(DATA/'cells_tenure.csv', index=False, encoding='utf-8')

# 全体の値（産業計・規模計・学歴計）の確認用
a = d['t1_843']['産業計']
tot = {s: dict(shoteinai=num(a[r][8]), kimatte=num(a[r][7]), workers=num(a[r][10])*10, tenure=num(a[r][4]), age=num(a[r][3]))
       for s, r in [('計',12),('男',116),('女',220)]}
json.dump(tot, open(DATA/'published_totals.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(t1.shape, t2.shape, tot)
