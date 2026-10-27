#!/bin/bash
# 上から順に実行すると data/*.csv・results/・figures/ が再現される（乱数は使っていない）
set -e
cd "$(dirname "$0")"
python 01_取得.py
python 02_整形.py
python 03_分析.py
python 04_図.py
