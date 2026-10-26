"""データの取得。
1) 地域保健・健康増進事業報告 健康増進編 市区町村表 第20-1表
   「健康診査、肺がん検診及び大腸がん検診対象者数・受診者数・受診率・（再掲）国民健康保険の被保険者，市区町村」
   e-Stat のファイル（CSV）。statInfId は次のとおり。
     令和3年度 000040038221 / 令和4年度 000040165455 / 令和5年度 000040262026 / 令和6年度 000040423652
   URL: https://www.e-stat.go.jp/stat-search/file-download?statInfId=<id>&fileKind=1 （Shift_JIS）
   ※ 実行環境から e-Stat に届かない場合は、ブラウザで取得したものを
     data/raw/f19_cancer_screening_raw.json（{"R3": csvテキスト, ...}）として置く（今回はこちら）。
2) SSDSE-A-2026（統計センター、共変量）… data/raw/SSDSE-A-2026.csv
3) 市区町村の境界（smartnews-smri/japan-topography、国土数値情報 行政区域 2021 の簡略版、CC BY 4.0）
"""
import json, urllib.request
from common import RAW

IDS = {"R3": "000040038221", "R4": "000040165455", "R5": "000040262026", "R6": "000040423652"}
dst = RAW / "f19_cancer_screening_raw.json"
if not dst.exists():
    out = {}
    for y, i in IDS.items():
        b = urllib.request.urlopen(f"https://www.e-stat.go.jp/stat-search/file-download?statInfId={i}&fileKind=1").read()
        out[y] = b.decode("cp932")
    json.dump(out, open(dst, "w"), ensure_ascii=False)
topo = RAW / "N03-21_210101.json"
if not topo.exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/"
                               "data/municipality/topojson/s0010/N03-21_210101.json", topo)
print("ok", dst.exists(), topo.exists(), (RAW / "SSDSE-A-2026.csv").exists())
