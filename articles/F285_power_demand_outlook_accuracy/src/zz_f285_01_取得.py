"""01 取得：元データの確認（手元にあれば md5 を記録、なければ取り直す）。
- OWID energy-data（日本の発電電力量・GDP）: https://github.com/owid/energy-data
- 電気事業連合会「電気事業60年の統計」12 使用電力量 / 2-1 発電電力量: https://www.fepc.or.jp/pr/data/60tokei/
- 総合エネルギー統計 2024年度確報 概要（PDF）から転記した 2010〜2024年度の値: enecho_fy2010_2024.csv
- 見通しの値（各資料から転記）: projections.csv / gdp_assumptions.csv
"""
import hashlib, json, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, '..', 'data', 'raw')
SRC = {
 'fepc60_0_12.xls': 'https://www.fepc.or.jp/pr/data/60tokei/xls/0_12.xls',
 'fepc60_2_1.xls': 'https://www.fepc.or.jp/pr/data/60tokei/xls/2_1.xls',
}
def get_owid(path):
    import pandas as pd
    url = 'https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv'
    d = pd.read_csv(url)
    j = d[(d.country == 'Japan') & (d.year >= 1985)][['year','electricity_generation','electricity_demand','gdp']]
    j.to_csv(path, index=False)
def main():
    for f, u in SRC.items():
        p = os.path.join(RAW, f)
        if not os.path.exists(p):
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
            open(p, 'wb').write(urllib.request.urlopen(req, timeout=60).read())
    p = os.path.join(RAW, 'owid_japan_electricity_gdp.csv')
    if not os.path.exists(p):
        get_owid(p)
    man = {f: hashlib.md5(open(os.path.join(RAW, f), 'rb').read()).hexdigest() for f in sorted(os.listdir(RAW))}
    json.dump(man, open(os.path.join(RAW, '..', 'MANIFEST.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(man, ensure_ascii=False, indent=1))
if __name__ == '__main__':
    main()
