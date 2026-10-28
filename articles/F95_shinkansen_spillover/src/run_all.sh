#!/bin/sh
# F95 を最初から再現する（src で実行。03 は約2〜3分）
set -e
python3 01_取得.py
python3 02_整形.py
python3 03_分析.py | tee ../results/run_log.txt
python3 04_図.py
