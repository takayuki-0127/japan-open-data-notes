# 取得したデータ（2026-10-29、Chrome のページ内で取得）

| ファイル | 内容 | 出典 |
|---|---|---|
| tepco_eria_jukyu_202610_30min.csv | 東京エリアの30分ごとの需要（MW）2026-10-01〜10-29 9:30 の行。分析は10-28までの24時間がそろう日を使う | 東京電力パワーグリッド「エリア需給実績データ」 https://www.tepco.co.jp/forecast/html/images/eria_jukyu_202610_03.csv |
| jma_daily_tokyo_202610.csv | 東京の日別値（平均・最高・最低気温、平均湿度、日照時間、降水量）2026-10-01〜28 | 気象庁「過去の気象データ検索」 https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no=44&block_no=47662&year=2026&month=10&day=&view= |
| births_geppo_gaisu_2026.csv | 2026年1〜5月の出生数（概数）と、同じ表の2025年同月（概数） | 厚生労働省「人口動態統計月報（概数）」令和8年1〜5月分 第1表 https://www.mhlw.go.jp/toukei/saikin/hw/jinkou/geppo/m2026/dl/toukeihyo_0M.pdf （M=1〜5） |
| life_table_2025.csv | 2025年・2024年の平均寿命と65歳の平均余命 | 厚生労働省「令和7年簡易生命表の概況」表1 https://www.mhlw.go.jp/toukei/saikin/hw/life/life25/dl/life25-02.pdf |

それ以外（2026年9月までの電力・気象、2025年までの出生数、F86 の予測、F13・F18・F90 の結果）は、各記事のフォルダのファイルをそのまま使う（`src/01_取得.md`）。
