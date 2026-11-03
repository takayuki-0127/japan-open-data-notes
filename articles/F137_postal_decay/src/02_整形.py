"""02 整形: 年度×種類の引受物数（千通・千個）の表を作る"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
raw = json.load(open(ROOT / 'data/raw/f137_postal_annual.json', encoding='utf-8'))

ZEN = str.maketrans('０１２３４５６７８９', '0123456789')
def fy(label):
    s = label.translate(ZEN)
    m = re.match(r'平成(\d+)年度', s)
    return 1988 + int(m.group(1)) if m else int(s[:4])

KEYS = ['総計','郵便物','普通','第一種','第二種','第三種','第四種','年賀','選挙','特殊','国際(差立)','荷物','ゆうパック','ゆうパケット','ゆうメール']
recs = {}
for src, v in raw['parsed'].items():
    cur, prev = fy(v['yrs'][0]), fy(v['yrs'][1])
    for k, r in v['rows'].items():
        if k not in KEYS: continue
        recs.setdefault((cur, k), (r[0], src, 'current'))            # 当年度欄を優先
        if (prev, k) not in recs or recs[(prev, k)][2] == 'prev':
            recs.setdefault((prev, k), (r[2], src, 'prev'))
        # FY2010 は FY2011 の前年比から逆算（頑健性用）
        if prev == 2011:
            recs.setdefault((2010, k), (round(r[2] / (1 + r[3] / 100)), src, 'derived_from_rate'))

jp = pd.DataFrame([dict(fy=a, item=k, value=v[0], source=v[1], kind=v[2]) for (a, k), v in recs.items()])
# ゆうパック・ゆうパケットは2025年公表版で定義が変わり前年度欄が書き換えられたため、種類別では荷物合計だけを使う

# 総務省資料 FY2003〜2007（百万通→千通）
so = {
 '総計':[25587,25004,24819,24677,24522], '郵便物':[24889,23575,22744,22360,21995],
 '普通':[24261,22956,22116,21712,21318], '第一種':[12335,11658,11194,11048,10729],
 '第二種':[7560,7307,7082,6995,6946], '第三種':[857,687,624,588,533], '第四種':[41,35,31,30,27],
 '年賀':[3359,3226,3120,3035,2980], '選挙':[110,42,65,16,102], '特殊':[543,538,550,573,604],
 '国際(差立)':[84,81,78,76,73], '荷物':[698,1430,2075,2317,2528], 'ゆうパック':[182,215,247,268,272],
 'ゆうメール':[516,1215,1828,2049,2256]}
srows = [dict(fy=2003+i, item=k, value=v*1000, source='総務省 080919_2_si4.pdf', kind='soumu') for k, vs in so.items() for i, v in enumerate(vs)]
df = pd.concat([jp, pd.DataFrame(srows)], ignore_index=True).sort_values(['item','fy'])
df.to_csv(ROOT / 'data/postal_annual_long.csv', index=False, encoding='utf-8')

wide = df[df.kind != 'derived_from_rate'].pivot(index='fy', columns='item', values='value')
wide['はがき(年賀除く)'] = wide['第二種']
wide.to_csv(ROOT / 'data/postal_annual_wide.csv', encoding='utf-8')

# 参考: 情報通信白書 H15 の総引受郵便物数（億通）
pd.DataFrame({'fy': list(range(1992, 2003)), '総引受_億通': [244,245,240,248,255,258,259,261,265,267,262]}).to_csv(
    ROOT / 'data/whitepaper_h15_total.csv', index=False, encoding='utf-8')
print(wide[['総計','郵便物','第一種','第二種','年賀','荷物']].to_string())
