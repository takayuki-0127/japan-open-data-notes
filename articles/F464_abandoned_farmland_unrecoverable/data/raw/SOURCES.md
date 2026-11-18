# 元データの出典（取得日と URL）

取得日：2026-11-18（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| kouhai_2011.pdf | 平成23年の荒廃農地に関する調査の結果について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/pdf/kouhyo6.pdf | fa9f18069aa9 |
| kouhai_2012.pdf | 平成24年の荒廃農地の面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/pdf/00_kouhyo25_tougou.pdf | 88969d24d879 |
| kouhai_2013.pdf | 平成25年の荒廃農地の面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/pdf/00_kouhyo26_tougou.pdf | ef739008e32b |
| kouhai_2014.pdf | 平成26年の荒廃農地の面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/pdf/kouhyo27_tougou.pdf | c89f6be074fe |
| kouhai_2015.pdf | 平成27年の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-1.pdf | 1b3a9939f399 |
| kouhai_2016.pdf | 平成28年の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-5.pdf | 582e0414e8bd |
| kouhai_2017.pdf | 平成29年の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-3.pdf | ecb66b489700 |
| kouhai_2018.pdf | 平成30年の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-6.pdf | fc85c0ebf936 |
| kouhai_2019.pdf | 令和元年の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-7.pdf | e6ec2bcd5230 |
| kouhai_2020.pdf | 令和2年の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-17.pdf | 9f7d293945ac |
| kouhai_2021.pdf | 令和3年度の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-9.pdf | 3cf65078bd9d |
| kouhai_2022.pdf | 令和4年度の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-18.pdf | b52df72ecd4e |
| kouhai_2023.pdf | 令和5年度の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-33.pdf | baf05c0d4e6c |
| kouhai_2024.pdf | 令和6年度の荒廃農地面積について（公表資料。資料2が都道府県別の表） | https://www.maff.go.jp/j/nousin/tikei/houkiti/attach/pdf/index-47.pdf | a16ae4c90601 |

- 掲載ページ：https://www.maff.go.jp/j/nousin/tikei/houkiti/index.html
- 出典：農林水産省「荒廃農地の発生・解消状況に関する調査」（2021年度からは「遊休農地に関する措置の状況に関する調査」とあわせた集計）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。
- 2011〜2020年は暦年の調査（各年の11月30日現在など）、2021年度からは年度末（3月30日・31日）現在。2021年度の調査から調査内容が見直されている（農水省の注記）。
- PDF の表は src/01b_extract.py（pdftotext 24.02.0 を使う）で data/kouhai_pref_raw.csv に抜き出した。run_all.sh はこの CSV から先だけを流す。
