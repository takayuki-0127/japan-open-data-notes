#!/bin/sh
# 上から順に実行（全部で1分ほど）
set -e
cd "$(dirname "$0")"
python 01_load.py
python 02_models.py
python 03_backtest.py
python 04_pref.py
python 05_marriage.py
python 06_figures.py
