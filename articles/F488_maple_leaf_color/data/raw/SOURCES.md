# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| phenology_015.csv | かえで紅葉（地点別、1953年〜） | https://www.data.jma.go.jp/sakura/data/ruinenchi/015.csv | 278c175a8661 |
| phenology_016.csv | かえで落葉（地点別、1953年〜） | https://www.data.jma.go.jp/sakura/data/ruinenchi/016.csv | 9a6dca67a54e |
| phenology_013.csv | いちょう黄葉（地点別、1953年〜） | https://www.data.jma.go.jp/sakura/data/ruinenchi/013.csv | 62ddc1a01ae2 |
| phenology_014.csv | いちょう落葉（地点別、1953年〜） | https://www.data.jma.go.jp/sakura/data/ruinenchi/014.csv | 7c90dbd3e037 |

出典：気象庁「生物季節観測の情報」生物季節観測累年値ファイル（https://www.data.jma.go.jp/sakura/data/download_ruinenchi.html）。
値は月日（例：1105＝11月5日）、0 は観測なし。各年の右の rm 列は気象庁のファイルフォーマットの説明による注記の符号。CSV は Shift_JIS。
