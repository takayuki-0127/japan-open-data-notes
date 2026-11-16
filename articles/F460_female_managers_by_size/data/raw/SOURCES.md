# 元データの出典（取得日と URL）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| managers_2003.xls | 2003年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000014282664&fileKind=0 | 1bb0f143e7e3 |
| managers_2009.xls | 2009年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000014304203&fileKind=0 | 21d7c1feb2ad |
| managers_2011.xlsx | 2011年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000017074194&fileKind=0 | ca00fbbe56ad |
| managers_2013.xls | 2013年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000027398616&fileKind=0 | 9582e5924f4b |
| managers_2015.xls | 2015年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031495814&fileKind=0 | 52b55b49fd49 |
| managers_2016.xls | 2016年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031642922&fileKind=0 | b9cdb8c5b0ca |
| managers_2017.xls | 2017年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031773423&fileKind=0 | 08e0bb0b7002 |
| managers_2018.xls | 2018年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031852415&fileKind=0 | f82cfb23004c |
| managers_2019.xls | 2019年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031969762&fileKind=0 | c23cbfa2d500 |
| managers_2020.xls | 2020年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032108520&fileKind=0 | 7efdec11d51c |
| managers_2021.xls | 2021年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032218442&fileKind=0 | 441fb70298af |
| managers_2022.xlsx | 2022年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040082653&fileKind=0 | 6cbc05d14c6a |
| managers_2023.xlsx | 2023年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040194846&fileKind=0 | 6305ad27c257 |
| managers_2024.xlsx | 2024年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040302144&fileKind=0 | b8ed565051bc |
| managers_2025.xlsx | 2025年度 雇用均等基本調査（企業調査） 役職別女性管理職（等）割合 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040480856&fileKind=0 | 4a6ae0958435 |

- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450281&tstat=000001051898
- 出典：厚生労働省「雇用均等基本調査」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。
- 2010・2012・2014年度は、この名前の表が見つからなかったため取得していない。
- 2017年度のファイルは1枚目のシートが別の表（コース別雇用管理制度）で、2枚目のシート「第8表」が役職別女性管理職割合。02_build.py は表題に「役職別女性管理職」がある方のシートを読む。
