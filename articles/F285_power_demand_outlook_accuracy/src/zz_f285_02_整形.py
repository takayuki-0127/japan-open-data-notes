"""02 整形：実績の系列をそろえる（年度と暦年）。出力 data/processed/actuals.csv"""
import os, re
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, '..', 'data', 'raw'); OUT = os.path.join(HERE, '..', 'data', 'processed')
os.makedirs(OUT, exist_ok=True)
def fepc_use():
    u = pd.read_excel(os.path.join(RAW, 'fepc60_0_12.xls'), header=None)
    rows = []
    for i in range(len(u)):
        m = re.search(r'\((\d{4})\)', str(u.iloc[i, 1]))
        if m:
            y = int(m.group(1))
            for j in range(max(0, i-3), min(len(u), i+4)):
                if str(u.iloc[j, 2]).replace(' ', '').replace('　', '') == '合計':
                    rows.append((y, float(u.iloc[j, 13]) / 1e5))  # 千kWh -> 億kWh
    s = pd.Series(dict(rows)).sort_index(); s.index.name = 'fy'
    return s
def fepc_sales_general():
    """一般電気事業者の使用電力量（販売、1951〜2010年度、参考）。"""
    u = pd.read_excel(os.path.join(RAW, 'fepc60_0_12.xls'), header=None)
    rows = []
    for i in range(len(u)):
        m = re.search(r'\((\d{4})\)', str(u.iloc[i, 1]))
        if m:
            y = int(m.group(1))
            for j in range(max(0, i-3), min(len(u), i+4)):
                if str(u.iloc[j, 2]).replace(' ', '').replace('\u3000', '') == '一般電気事業者計':
                    rows.append((y, float(u.iloc[j, 13]) / 1e5))
    return pd.Series(dict(rows)).sort_index()
def fepc_gen():
    v = pd.read_excel(os.path.join(RAW, 'fepc60_2_1.xls'), sheet_name='全国計', header=None)
    yrs = [int(re.search(r'(\d{4})', str(x)).group(1)) for x in v.iloc[4, 5:15]]
    tot = v.iloc[50, 5:15].astype(float).values / 1e5  # 合計（自家用込み）
    return pd.Series(tot, index=yrs)
def fepc_gen_utility():
    """電気事業者計の発電電力量（自家用を含まない、2001〜2010年度）。2010年度は卸供給などの区分替えの影響がある（推測）。"""
    v = pd.read_excel(os.path.join(RAW, 'fepc60_2_1.xls'), sheet_name='全国計', header=None)
    yrs = [int(re.search(r'(\d{4})', str(x)).group(1)) for x in v.iloc[4, 5:15]]
    assert str(v.iloc[32, 4]).strip() == '計' and str(v.iloc[50, 4]).strip() == '計'
    return pd.Series(v.iloc[32, 5:15].astype(float).values / 1e5, index=yrs)
def main():
    en = pd.read_csv(os.path.join(RAW, 'enecho_fy2010_2024.csv')).set_index('fy')
    use = fepc_use()
    k = en.loc[2010, 'final_electricity_oku_kwh'] / use.loc[2010]
    dem = pd.concat([use.loc[:2009] * k, en['final_electricity_oku_kwh']])
    g = fepc_gen(); kg = en.loc[2010, 'generation_oku_kwh'] / g.loc[2010]
    gen_fy = pd.concat([g.loc[:2009] * kg, en['generation_oku_kwh']])
    ow = pd.read_csv(os.path.join(RAW, 'owid_japan_electricity_gdp.csv')).set_index('year')
    a = pd.DataFrame({'demand_fy': dem, 'gen_fy': gen_fy, 'gen_utility_fy': fepc_gen_utility(), 'sales_general_fy': fepc_sales_general()})
    a = a.join(ow[['electricity_generation', 'gdp']].rename(columns={'electricity_generation': 'gen_owid_cal_twh', 'gdp': 'gdp_owid_cal'}), how='outer')
    a.index.name = 'year'; a = a.loc[1985:]
    a.to_csv(os.path.join(OUT, 'actuals.csv'))
    print('splice factors demand', round(k, 4), 'gen', round(kg, 4))
    print(a.loc[[2001, 2009],['gen_utility_fy']].round(1).to_string())
    print(a.loc[[1990, 1997, 2000, 2005, 2007, 2010, 2013, 2019, 2020, 2022, 2023, 2024, 2025]].round(1).to_string())
if __name__ == '__main__':
    main()
