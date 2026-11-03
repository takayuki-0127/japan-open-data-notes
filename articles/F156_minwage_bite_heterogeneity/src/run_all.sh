#!/bin/sh
# 01_取得.py は e-Stat から取った JSON（リポジトリ外）が必要。data/raw/wage_short_pref_2009_2025.csv があれば 02 から動く
set -e
cd "$(dirname "$0")"
python 02_整形.py
python 03_分析.py
python 03b_頑健性.py
python 04_図.py
