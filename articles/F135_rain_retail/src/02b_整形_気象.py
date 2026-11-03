# 気象庁「過去の気象データ」日別値（9地点）を、地点×月の降水日数などに集計する
import json, re, pandas as pd, numpy as np, pathlib, datetime as dt, jpholiday
A = pathlib.Path(__file__).resolve().parents[1]
W = json.load(open(A/'data/raw/f135_jma_daily.json'))
REGION = {'札幌': '北海道', '仙台': '東北', '東京': '関東', '名古屋': '中部', '大阪': '近畿',
          '広島': '中国', '高松': '四国', '福岡': '九州', '那覇': '沖縄'}

def val(s):
    s = s.replace(')', '').replace(']', '').strip()
    if s in ('--',):
        return 0.0          # 「--」は降水なし
    try: return float(s)
    except: return np.nan   # ×・///・空欄は欠測

rec = []
for k, rows in W.items():
    st, y, m = k.split('_'); y, m = int(y), int(m)
    for d_, p, t, sun in rows:
        day = dt.date(y, m, int(d_))
        off = day.weekday() >= 5 or jpholiday.is_holiday(day)
        rec.append(dict(地点=st, 地域=REGION[st], date=day, ym=f'{y}-{m:02d}', p=val(p), t=val(t), off=off))
daily = pd.DataFrame(rec)
g = daily.groupby(['地点', '地域', 'ym'])
mon = pd.DataFrame({
    'rain1': g.p.apply(lambda s: (s >= 1.0).sum()),
    'rain10': g.p.apply(lambda s: (s >= 10.0).sum()),
    'ptot': g.p.sum(min_count=20),
    'tmean': g.t.mean(),
    'rain1_off': g.apply(lambda x: ((x.p >= 1.0) & x.off).sum(), include_groups=False),
    'rain1_wd': g.apply(lambda x: ((x.p >= 1.0) & ~x.off).sum(), include_groups=False),
    'n_off': g.off.sum(), 'n_days': g.p.size(), 'n_miss': g.p.apply(lambda s: s.isna().sum()),
}).reset_index()
mon.to_csv(A/'data/weather_monthly.csv', index=False)
print(mon.groupby('地点')[['rain1', 'rain10', 'ptot', 'tmean', 'n_miss']].mean().round(2).to_string())
print(len(mon), mon.ym.min(), mon.ym.max())
