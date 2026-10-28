#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 01_取得.py
python3 02_整形.py
python3 03_分析.py | tee ../results/run_log.txt
python3 04_図.py
