# データの取得（林野庁「森林資源の現況」と、農林水産省「木材統計調査」）
# 作業時はブラウザの中で取得したので、この関数は同じファイルを取りに行くための記録として置いている。
import requests, time
from pathlib import Path
RAW = Path(__file__).resolve().parents[1] / 'data' / 'raw'
RINYA = 'https://www.rinya.maff.go.jp/j/keikaku/genkyou/'
FOREST = {  # 樹種別齢級別 面積(ha)・蓄積(m3)。各年3月31日現在
    'r4_ha.xlsx': 'r4/attach/xls/4-1.xlsx', 'r4_m3.xlsx': 'r4/attach/xls/5-1.xlsx',
    'h29_ha.xls': 'h29/attach/xls/4-1.xls', 'h29_m3.xls': 'h29/attach/xls/5-1.xls',
    'h24_ha.xls': 'h24/other/jyusyu_ha_h24.xls', 'h24_m3.xls': 'h24/other/jyusyu_m3_h24.xls',
    'h19_ha.xls': 'h19/other/jyusyu_ha.xls', 'h19_m3.xls': 'h19/other/jyusyu_m3.xls'}
ESTAT = 'https://www.e-stat.go.jp/stat-search/file-download?fileKind=0&statInfId='
WOOD = {  # 木材需給報告書：樹種別素材生産量（全国・5年分）と、都道府県別の主要部門別・樹種別素材生産量（合計）
    'nat_R6': '000040431136', 'nat_R1': '000032087334', 'nat_H26': '000031323439', 'nat_H21': '000012561137',
    'pref_R6': '000040431166', 'pref_R1': '000032087364', 'pref_H26': '000031323471', 'pref_H21': '000012561169'}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, path in FOREST.items():
        (RAW / name).write_bytes(requests.get(RINYA + path, timeout=60).content); time.sleep(2)
    for name, sid in WOOD.items():
        (RAW / f'{name}.xls').write_bytes(requests.get(ESTAT + sid, timeout=60).content); time.sleep(2)
    # 作業時は木材統計を CSV に変換して data/raw/f142_wood.json（{表名: {シート名: CSV}}）にまとめた

if __name__ == '__main__':
    main()
