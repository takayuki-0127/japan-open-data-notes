"""データの取得。

e-Stat のファイルは、ブラウザで次の statInfId を開いて Excel を保存し、data/raw/ に置く
（この記事では、ブラウザ上で Excel を CSV にして 1 つの JSON / CSV にまとめたものを data/raw/ に置いている）。

1) 住民基本台帳人口移動報告（総務省）
   - 長期時系列表 第11表「移動前の住所地別転入者数及び移動後の住所地別転出者数」
     1990年（平成2年） statInfId=000014898778
     2000年（平成12年）statInfId=000014898788
     2010年（平成22年）statInfId=000014898798
   - 年報（実数）2025年 表2「移動前の住所地、男女別都道府県間移動者数」 statInfId=000040407039
   → data/raw/f10_migration_raw.json（{年: {シート名: CSV文字列}}）
2) 令和2年国勢調査 従業地・通学地による人口・就業状態等集計 第3表
   「男女，就業・通学，従業地・通学地別就業者・通学者数（常住地）」総数（男女）
     埼玉県 000032214185／千葉県 000032214188／東京都 000032214196／神奈川県 000032214199
   → 男女「総数」の行だけを残し、15歳以上就業者数を data/raw/f10_commute.csv にまとめた
     （列：src,res_code,level,cat,work_code,workers15、最後に #NAMES 以下でコードと名前の対応）
3) 都道府県の人口：統計センター SSDSE-B-2026（data/raw/SSDSE-B-2026.csv、手作業でダウンロード）
4) 境界：smartnews-smri/japan-topography（国土数値情報 行政区域 2021 の簡略版、CC BY 4.0）
"""
import urllib.request
from common import RAW

RAW.mkdir(parents=True, exist_ok=True)
url = ("https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/"
       "data/municipality/topojson/s0010/N03-21_210101.json")
dst = RAW / "N03-21_210101.json"
if not dst.exists():
    urllib.request.urlretrieve(url, dst)
for f in ["f10_migration_raw.json", "f10_commute.csv", "SSDSE-B-2026.csv", "N03-21_210101.json"]:
    print(f, (RAW / f).exists())
