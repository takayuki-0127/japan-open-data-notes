# SOURCES（元データの取得元）

取得日：2026-11-18（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| fbs_wheat_ruinen_r6.csv | 食料需給表 確報 令和6年度 品目別累年表 穀類／小麦（1960〜2024年度、CSV・Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040422813&fileKind=1 | a594e0674438 |
| fbs_r7_gaisan.xlsx | 食料需給表 令和7年度（概算）統計表（シート1：令和7年度概算、シート2：令和6年度確定） | https://www.maff.go.jp/j/zyukyu/fbs/attach/xls/index-4.xlsx | 85388aa0ed08 |
| crop_wheat_000040383862.xls | 作物統計 収穫量累年統計 小麦 全国（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383862&fileKind=0 | 9996bde2dcfd |
| crop_wheat_000040383863.xls | 作物統計 収穫量累年統計 小麦 北海道（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383863&fileKind=0 | 153475cac744 |
| crop_wheat_000040383864.xls | 作物統計 収穫量累年統計 小麦 都府県（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383864&fileKind=0 | 1fbb493155c3 |
| crop_wheat_000040383865.xls | 作物統計 収穫量累年統計 小麦 東北（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383865&fileKind=0 | 8277f9dac4b3 |
| crop_wheat_000040383866.xls | 作物統計 収穫量累年統計 小麦 北陸（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383866&fileKind=0 | 1f89779d02a0 |
| crop_wheat_000040383867.xls | 作物統計 収穫量累年統計 小麦 関東・東山（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383867&fileKind=0 | ca91554a8f93 |
| crop_wheat_000040383868.xls | 作物統計 収穫量累年統計 小麦 東海（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383868&fileKind=0 | 14712d39add4 |
| crop_wheat_000040383869.xls | 作物統計 収穫量累年統計 小麦 近畿（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383869&fileKind=0 | 65400b02be3a |
| crop_wheat_000040383870.xls | 作物統計 収穫量累年統計 小麦 中国（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383870&fileKind=0 | 2fcbf9ea0600 |
| crop_wheat_000040383871.xls | 作物統計 収穫量累年統計 小麦 四国（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383871&fileKind=0 | bebc93482437 |
| crop_wheat_000040383872.xls | 作物統計 収穫量累年統計 小麦 九州（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383872&fileKind=0 | 05e915937965 |
| crop_wheat_000040383873.xls | 作物統計 収穫量累年統計 小麦 沖縄（Excel） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040383873&fileKind=0 | 1325a2d29842 |

- 食料需給表の掲載ページ：https://www.maff.go.jp/j/zyukyu/fbs/ （令和6年度確報の e-Stat：https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist&toukei=00500300&tstat=000001017950&cycle=8&tclass1=000001032890&tclass2=000001241316 ）
- 作物統計 長期累年の一覧：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00500215&tstat=000001013427&cycle=0&tclass1=000001032288&tclass2=000001034728&layout=datalist
- 食料需給表は「年度」（4月〜翌3月）。作物統計は「産年」（その年に収穫した麦）。小麦は初夏に収穫するため、需給表の t 年度の国内生産量は t 年産の収穫量と同じ値になる（02_build.py で照合）。

出典：農林水産省「食料需給表」「作物統計」。
