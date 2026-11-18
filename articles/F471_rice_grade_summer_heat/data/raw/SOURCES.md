# 元データの出典（取得日と URL）

取得日：2026-11-18（src/01_fetch.py で取得）

## 農林水産省「米の農産物検査結果」（確定値。各年産の翌年10月31日現在）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| maff/kensa_2006.pdf | 2006年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/pdf/index-44.pdf | 11f923c6ef88 |
| maff/kensa_2007.pdf | 2007年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/pdf/index-41.pdf | e9241ced39be |
| maff/kensa_2008.pdf | 2008年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/pdf/index-40.pdf | 58948e7bcbe1 |
| maff/kensa_2009.pdf | 2009年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/pdf/index-43.pdf | d550e287dd81 |
| maff/kensa_2010.pdf | 2010年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/pdf/index-42.pdf | 88762b0a0b38 |
| maff/kensa_2011.pdf | 2011年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/pdf/23km2410.pdf | 0788c130de2d |
| maff/kensa_2012.pdf | 2012年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/pdf/24km2510b.pdf | 72896b1ded6b |
| maff/kensa_2013.pdf | 2013年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/pdf/25km2510.pdf | 52782965b8fb |
| maff/kensa_2014.pdf | 2014年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/pdf/26km2710_kakutei.pdf | 7f96cc1f7401 |
| maff/kensa_2015.pdf | 2015年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/pdf/index-11.pdf | 9969b12ddc18 |
| maff/kensa_2016.xlsx | 2016年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-2.xlsx | 1758aade778c |
| maff/kensa_2017.xlsx | 2017年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-13.xlsx | d1e325483116 |
| maff/kensa_2018.xlsx | 2018年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-30.xlsx | a434bb778d57 |
| maff/kensa_2019.xlsx | 2019年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-17.xlsx | 37a03f83fa45 |
| maff/kensa_2020.xlsx | 2020年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-18.xlsx | 1ca6fcc3de5e |
| maff/kensa_2021.xlsx | 2021年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-15.xlsx | 4054a1dc630d |
| maff/kensa_2022.xlsx | 2022年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-46.xlsx | aeb7f4240bf3 |
| maff/kensa_2023.xlsx | 2023年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-57.xlsx | 293ba768e200 |
| maff/kensa_2024.xlsx | 2024年産 水稲うるち玄米の等級別検査数量（都道府県別）ほか | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-73.xlsx | 0f0050c79086 |
| maff/ittou_suii_national.xlsx | 水稲うるち玄米 1等比率の推移（全国、照合用） | https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/attach/xls/index-81.xlsx | 32ab6463a7ce |

- 一覧のページ：https://www.maff.go.jp/j/seisan/syoryu/kensa/kome/index.html
- pdf_text/kensa_2006〜2015.txt は、PDF から `pdftotext -layout`（poppler）で取り出した文字（01_fetch.py の最後で作る）。02_build.py はこの txt を読む。

## 気象庁「過去の気象データ検索」日平均気温の月平均値（地点ごとの全年の表）

| ファイル | 地点（都道府県） | URL | sha256 の先頭12字 |
|---|---|---|---|
| jma/47412.html | 札幌（北海道） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=14&block_no=47412&year=2024&month=&day=&view= | 8c1fbaf16492 |
| jma/47575.html | 青森（青森） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=31&block_no=47575&year=2024&month=&day=&view= | d1990d71b725 |
| jma/47584.html | 盛岡（岩手） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=33&block_no=47584&year=2024&month=&day=&view= | 70eaeeb37221 |
| jma/47590.html | 仙台（宮城） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=34&block_no=47590&year=2024&month=&day=&view= | c185778e0f9f |
| jma/47582.html | 秋田（秋田） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=32&block_no=47582&year=2024&month=&day=&view= | d8c125e7c34d |
| jma/47588.html | 山形（山形） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=35&block_no=47588&year=2024&month=&day=&view= | 100ab4f00fbf |
| jma/47595.html | 福島（福島） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=36&block_no=47595&year=2024&month=&day=&view= | 19b0cc687109 |
| jma/47629.html | 水戸（茨城） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=40&block_no=47629&year=2024&month=&day=&view= | 50957a6da6e5 |
| jma/47615.html | 宇都宮（栃木） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=41&block_no=47615&year=2024&month=&day=&view= | 1dd709b8c9a3 |
| jma/47624.html | 前橋（群馬） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=42&block_no=47624&year=2024&month=&day=&view= | 153d921cdfde |
| jma/47626.html | 熊谷（埼玉） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=43&block_no=47626&year=2024&month=&day=&view= | 6149c4c6c8fa |
| jma/47682.html | 千葉（千葉） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=45&block_no=47682&year=2024&month=&day=&view= | a6b57abd5146 |
| jma/47662.html | 東京（東京） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=44&block_no=47662&year=2024&month=&day=&view= | f0af9ce0ef03 |
| jma/47670.html | 横浜（神奈川） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=46&block_no=47670&year=2024&month=&day=&view= | 80be3000bc34 |
| jma/47638.html | 甲府（山梨） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=49&block_no=47638&year=2024&month=&day=&view= | 62a6c8a5f14c |
| jma/47610.html | 長野（長野） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=48&block_no=47610&year=2024&month=&day=&view= | 563c90e62154 |
| jma/47656.html | 静岡（静岡） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=50&block_no=47656&year=2024&month=&day=&view= | b95eb507d566 |
| jma/47604.html | 新潟（新潟） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=54&block_no=47604&year=2024&month=&day=&view= | c1d1fe3c7e9a |
| jma/47607.html | 富山（富山） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=55&block_no=47607&year=2024&month=&day=&view= | c417b5fd6725 |
| jma/47605.html | 金沢（石川） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=56&block_no=47605&year=2024&month=&day=&view= | e2b4509e0a24 |
| jma/47616.html | 福井（福井） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=57&block_no=47616&year=2024&month=&day=&view= | a577314e2418 |
| jma/47632.html | 岐阜（岐阜） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=52&block_no=47632&year=2024&month=&day=&view= | 959a49f26179 |
| jma/47636.html | 名古屋（愛知） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=51&block_no=47636&year=2024&month=&day=&view= | 518cb8752eb4 |
| jma/47651.html | 津（三重） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=53&block_no=47651&year=2024&month=&day=&view= | 165412a3a62c |
| jma/47761.html | 彦根（滋賀） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=60&block_no=47761&year=2024&month=&day=&view= | 73c97ca6abd7 |
| jma/47759.html | 京都（京都） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=61&block_no=47759&year=2024&month=&day=&view= | dd39c6f030b1 |
| jma/47772.html | 大阪（大阪） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=62&block_no=47772&year=2024&month=&day=&view= | 0bc253d533a8 |
| jma/47770.html | 神戸（兵庫） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=63&block_no=47770&year=2024&month=&day=&view= | e4a8959def14 |
| jma/47780.html | 奈良（奈良） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=64&block_no=47780&year=2024&month=&day=&view= | 2b0190c3e131 |
| jma/47777.html | 和歌山（和歌山） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=65&block_no=47777&year=2024&month=&day=&view= | ae524b27678e |
| jma/47746.html | 鳥取（鳥取） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=69&block_no=47746&year=2024&month=&day=&view= | 77975d24d2f5 |
| jma/47741.html | 松江（島根） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=68&block_no=47741&year=2024&month=&day=&view= | 69c3780924a6 |
| jma/47768.html | 岡山（岡山） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=66&block_no=47768&year=2024&month=&day=&view= | b6ceddc0c720 |
| jma/47765.html | 広島（広島） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=67&block_no=47765&year=2024&month=&day=&view= | e240a759debc |
| jma/47784.html | 山口（山口） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=81&block_no=47784&year=2024&month=&day=&view= | d2c734923702 |
| jma/47895.html | 徳島（徳島） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=71&block_no=47895&year=2024&month=&day=&view= | 12b16b336162 |
| jma/47891.html | 高松（香川） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=72&block_no=47891&year=2024&month=&day=&view= | 74bfd2790de5 |
| jma/47887.html | 松山（愛媛） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=73&block_no=47887&year=2024&month=&day=&view= | 9c410810cfe0 |
| jma/47893.html | 高知（高知） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=74&block_no=47893&year=2024&month=&day=&view= | cb6556fb1e75 |
| jma/47807.html | 福岡（福岡） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=82&block_no=47807&year=2024&month=&day=&view= | 70f7c514541c |
| jma/47813.html | 佐賀（佐賀） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=85&block_no=47813&year=2024&month=&day=&view= | 74364e0fa47c |
| jma/47817.html | 長崎（長崎） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=84&block_no=47817&year=2024&month=&day=&view= | bbed2f3533e3 |
| jma/47819.html | 熊本（熊本） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=86&block_no=47819&year=2024&month=&day=&view= | 3edf568d41e1 |
| jma/47815.html | 大分（大分） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=83&block_no=47815&year=2024&month=&day=&view= | 46f1366bb5e0 |
| jma/47830.html | 宮崎（宮崎） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=87&block_no=47830&year=2024&month=&day=&view= | 73d984ba2117 |
| jma/47827.html | 鹿児島（鹿児島） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=88&block_no=47827&year=2024&month=&day=&view= | 7230e07cc039 |
| jma/47936.html | 那覇（沖縄） | https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=91&block_no=47936&year=2024&month=&day=&view= | 47ea7d77420c |

- 過去の気象データ検索：https://www.data.jma.go.jp/stats/etrn/index.php
- 値のあとに「 )」が付く月は準正常値（統計に使う資料の一部が欠けている）。数字はそのまま使い、7〜9月の該当は results/temp_flags_jul_sep.csv に出した。

出典：農林水産省「米の農産物検査結果」、気象庁「過去の気象データ検索」。政府標準利用規約（第2.0版）・気象庁ホームページの利用規約に従い、出典を示して加工して使う。
