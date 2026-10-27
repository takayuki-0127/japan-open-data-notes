"""F69 データの取得：新しい調査データは取らず、前の記事のフォルダにある元データを GitHub から取ってくる"""
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / 'data' / 'raw'
RAW.mkdir(parents=True, exist_ok=True)
BASE = 'https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/'
FILES = {
    'ssds_municipal.json': 'F16_childcare_dml/data/raw/f16_ssds_municipal.json',          # T1 社会・人口統計体系
    'kakei_000040270646.csv': 'F11_tax_hike_event/data/raw/kakei_000040270646.csv',       # T2 家計調査 支出金額
    'kakei_000040270647.csv': 'F11_tax_hike_event/data/raw/kakei_000040270647.csv',       # T2 名目増減率
    'kakei_000040270648.csv': 'F11_tax_hike_event/data/raw/kakei_000040270648.csv',       # T2 実質増減率
    'idwr_teiten_flu.json': 'F52_influenza_spread/data/raw/f52_teiten_flu.json',          # T3 IDWR 定点
    'vital_hokenjo_muni.json': 'F27_disease_map_bym2/data/raw/f27_raw.json',              # T4 人口動態保健所・市区町村別
    'census2020_lfs_pref.json': 'F31_retirement_rdd/data/raw/f31_census2020_pref.json',   # T5 国勢調査2020
}
for name, path in FILES.items():
    out = RAW / name
    if out.exists():
        print('あり', name); continue
    print('取得', name)
    urllib.request.urlretrieve(BASE + path, out)
