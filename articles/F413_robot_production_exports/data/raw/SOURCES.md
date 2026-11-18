# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py で取得）

## 同梱しているファイル（data/raw/）

| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |
|---|---|---|---|---|
| mach2012_ts1.xls | 経済産業省「生産動態統計」2012年 年報 機械統計 時系列表その１（2008〜2012年。08 運搬機械及び産業用ロボット を含む） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000022159804&fileKind=0 | 63cfe3cc17a0 | 1341440 |
| mach2017_ts1.xls | 経済産業省「生産動態統計」2017年 年報 機械統計編 時系列表その１（2013〜2017年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031703015&fileKind=0 | a197d847362d | 1134080 |
| mach2020_ts1.xls | 経済産業省「生産動態統計」2020年 年報 機械統計編 時系列表その１（2016〜2020年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031961788&fileKind=0 | cfcac7d40a93 | 1222144 |
| nenpo2021.xlsx | 経済産業省「生産動態統計」2021年 年報（全品目の実数表。2017〜2021年の暦年の列を含む） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032213834&fileKind=0 | 072d896073ca | 3157559 |
| nenpo2022.xlsx | 経済産業省「生産動態統計」2022年 年報（同） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040077080&fileKind=0 | 094ce5a6ee1a | 3099985 |
| nenpo2023.xlsx | 経済産業省「生産動態統計」2023年 年報（同） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040191921&fileKind=0 | 4959c0094cd2 | 3187354 |
| nenpo2024.xlsx | 経済産業省「生産動態統計」2024年 年報（月次） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040293825&fileKind=0 | 14307dab7b1c | 2592344 |
| nenpo2025.xlsx | 経済産業省「生産動態統計」2025年 年報（月次） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040475159&fileKind=0 | b07a16cdf7b3 | 2260480 |
| customs_country_code_e.htm | 財務省 税関「Country code list - Trade Statistics of Japan」（国コード・国名・地域） | https://www.customs.go.jp/toukei/sankou/code/country_e.htm | b26cacd0cccf | 19443 |
| customs_export_robots.csv | 下の品別国別表から、src/01b_extract.py で HS 8479.50（産業用ロボット（他の項に属しないもの））と HS 8428.70（産業用ロボット（持ち上げ・荷扱い用）、2017年から）の行だけを抜き出したもの | — | （01b_extract.py の実行で決まる） | — |

## 同梱していないファイル（data/cache/、合計で約100MB）

| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |
|---|---|---|---|---|
| customs_export_hs84_85_2009.csv | 財務省「貿易統計」2009年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000007064263&fileKind=1 | b678faa3b759 | 6317176 |
| customs_export_hs84_85_2010.csv | 財務省「貿易統計」2010年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000008622880&fileKind=1 | 7136a1bedf7a | 6426417 |
| customs_export_hs84_85_2011.csv | 財務省「貿易統計」2011年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000012679340&fileKind=1 | 3508835436ff | 6331184 |
| customs_export_hs84_85_2012.csv | 財務省「貿易統計」2012年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000018862129&fileKind=1 | f7fcf65a274c | 6184977 |
| customs_export_hs84_85_2013.csv | 財務省「貿易統計」2013年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000023611819&fileKind=1 | 5ac5b76b0d22 | 6211214 |
| customs_export_hs84_85_2014.csv | 財務省「貿易統計」2014年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000028156956&fileKind=1 | 3e50b4f2d5f6 | 6338955 |
| customs_export_hs84_85_2015.csv | 財務省「貿易統計」2015年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031362114&fileKind=1 | ed5147a40d7e | 6321534 |
| customs_export_hs84_85_2016.csv | 財務省「貿易統計」2016年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031528487&fileKind=1 | 8af41bfc2f06 | 6211492 |
| customs_export_hs84_85_2017.csv | 財務省「貿易統計」2017年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031670669&fileKind=1 | d3b2a41af38c | 6258797 |
| customs_export_hs84_85_2018.csv | 財務省「貿易統計」2018年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031792505&fileKind=1 | 7270bd4e6982 | 6255715 |
| customs_export_hs84_85_2019.csv | 財務省「貿易統計」2019年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031907283&fileKind=1 | ce3067b3937d | 6091576 |
| customs_export_hs84_85_2020.csv | 財務省「貿易統計」2020年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032046051&fileKind=1 | 24d7457c9a9b | 5679181 |
| customs_export_hs84_85_2021.csv | 財務省「貿易統計」2021年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032254729&fileKind=1 | e5af4c3def61 | 5831510 |
| customs_export_hs84_85_2022.csv | 財務省「貿易統計」2022年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040117436&fileKind=1 | d1425164fd28 | 5991775 |
| customs_export_hs84_85_2023.csv | 財務省「貿易統計」2023年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040223224&fileKind=1 | 713492632c5a | 6052873 |
| customs_export_hs84_85_2024.csv | 財務省「貿易統計」2024年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040368848&fileKind=1 | 822d898658fc | 6051166 |
| customs_export_hs84_85_2025.csv | 財務省「貿易統計」2025年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040524633&fileKind=1 | 681ac3a164aa | 6063700 |

- e-Stat の一覧：生産動態統計 https://www.e-stat.go.jp/stat-search/files?toukei=00550200&tstat=000001022932 、普通貿易統計 https://www.e-stat.go.jp/stat-search/files?toukei=00350300&tstat=000001013141
- 経済産業省のサイト（www.meti.go.jp/statistics/）は 2026-11-18 に 403 を返したため、同じ年報を e-Stat から取った。
- 品別国別表の国コードは 103 韓国、105 中国、106 台湾、304 米国 など。対応は customs_country_code_e.htm。

出典：経済産業省「生産動態統計」、財務省「貿易統計」。
