#!/bin/bash
# 上から順に実行すると、図と数字が再現できる（03 は2コアで約40分）
set -e
cd "$(dirname "$0")"
python3 01_取得.py
python3 02_整形.py
python3 03_分析.py main start2014 japanese foreign arima snaive post covid
python3 04_図.py
