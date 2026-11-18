# 元データの出典（取得日と URL）

取得日：2026-11-18（src/01_fetch.py で取得）

農林水産省「農業経営統計調査 経営形態別経営統計（個別経営）」（e-Stat）。各年の表は、e-Stat の一覧のページの節の見出し（「農業の主副業別統計表」「都府県経営耕地規模別統計表」、2012年以降は「全国農業地域別・経営耕地規模別統計表」の都府県）と表の題（「経営の概要と分析指標」）の文字で選んだ。選んだ表の ID は maff/manifest.json にある。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| maff/long_1_1.xls | 長期累年 全国年次別統計表 (1) 経営の概要と分析指標（平成16〜30年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031978010&fileKind=0 | f37aedd1ccb6 |
| maff/shufuku_2004_1.xls | 2004年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000005317260&fileKind=0 | 7d12e4fd64ac |
| maff/kibo_tofuken_2004_1.xls | 2004年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000005317305&fileKind=0 | b75e1dc6773e |
| maff/shufuku_2005_1.xls | 2005年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000001167430&fileKind=0 | 7d02cc62d371 |
| maff/kibo_tofuken_2005_1.xls | 2005年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000001167466&fileKind=0 | f65f2e823c6f |
| maff/shufuku_2006_1.xls | 2006年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000002038751&fileKind=0 | a063f8dc7dcb |
| maff/kibo_tofuken_2006_1.xls | 2006年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000002038796&fileKind=0 | 26da046c31bd |
| maff/shufuku_2007_1.xls | 2007年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000007340974&fileKind=0 | ece3254379d9 |
| maff/kibo_tofuken_2007_1.xls | 2007年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000007341019&fileKind=0 | a8dc97102e0f |
| maff/shufuku_2008_1.xls | 2008年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000008642800&fileKind=0 | 35233cfb4a36 |
| maff/kibo_tofuken_2008_1.xls | 2008年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000008642845&fileKind=0 | 5053120d175d |
| maff/shufuku_2009_1.xls | 2009年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000009060537&fileKind=0 | b05d7c552824 |
| maff/kibo_tofuken_2009_1.xls | 2009年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000009060582&fileKind=0 | 6438ed7bad28 |
| maff/shufuku_2010_1.xls | 2010年 農業の主副業別統計表 経営の概要と分析指標（その1） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013160096&fileKind=0 | 8f88824435a0 |
| maff/shufuku_2010_2.xls | 2010年 農業の主副業別統計表 経営の概要と分析指標（その2） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013160097&fileKind=0 | 744f0e5ef1e5 |
| maff/kibo_tofuken_2010_1.xls | 2010年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013160140&fileKind=0 | 9cdb22df12c2 |
| maff/shufuku_2011_1.xls | 2011年 農業の主副業別統計表 経営の概要と分析指標（その1） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000020586016&fileKind=0 | aed5c691eb05 |
| maff/shufuku_2011_2.xls | 2011年 農業の主副業別統計表 経営の概要と分析指標（その2） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000020586017&fileKind=0 | 1b755fdf7723 |
| maff/kibo_tofuken_2011_1.xls | 2011年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000020586060&fileKind=0 | c73aef01ff31 |
| maff/shufuku_2012_1.xls | 2012年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000023631650&fileKind=0 | c32b31d7c10c |
| maff/kibo_tofuken_2012_1.xls | 2012年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000023631705&fileKind=0 | 0ac09890f6c4 |
| maff/shufuku_2013_1.xls | 2013年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000029961470&fileKind=0 | 593f19ea4cc2 |
| maff/kibo_tofuken_2013_1.xls | 2013年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000029961525&fileKind=0 | 32ebe19c6885 |
| maff/shufuku_2014_1.xls | 2014年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031433527&fileKind=0 | 2a425b5b5c07 |
| maff/kibo_tofuken_2014_1.xls | 2014年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031433582&fileKind=0 | 934cd301e887 |
| maff/shufuku_2015_1.xls | 2015年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031589866&fileKind=0 | 04d32f658082 |
| maff/kibo_tofuken_2015_1.xls | 2015年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031589921&fileKind=0 | 7be99a319e84 |
| maff/shufuku_2016_1.xls | 2016年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031701252&fileKind=0 | 69266ecf8f23 |
| maff/kibo_tofuken_2016_1.xls | 2016年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031701307&fileKind=0 | 62ace61a017f |
| maff/shufuku_2017_1.xls | 2017年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031805027&fileKind=0 | be18c3bed052 |
| maff/kibo_tofuken_2017_1.xls | 2017年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031805057&fileKind=0 | 322b6a541e7b |
| maff/shufuku_2018_1.xls | 2018年 農業の主副業別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031928318&fileKind=0 | 2d01a7a6262a |
| maff/kibo_tofuken_2018_1.xls | 2018年 都府県の経営耕地規模別統計表 経営の概要と分析指標 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031928366&fileKind=0 | ce1693556f1d |

- 統計表の一覧（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00500201&tstat=000001013460
- 調査の説明（農林水産省）：https://www.maff.go.jp/j/tokei/kouhyou/noukei/
- 2010・2011年の主副業別の表は2つのファイルに分かれている。所得の項目は「その1」にある（02_build.py は「その1」を読む）。
- 2019年からの「個人経営体」の表（例：2024年の表番号6 農業の主副業別統計表 https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040429857&fileKind=0 ）には、農外所得・年金等の収入・総所得の項目がない。このため2018年までを使った（このファイルは分析に使わないので同梱していない）。

出典：農林水産省「農業経営統計調査」。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。
