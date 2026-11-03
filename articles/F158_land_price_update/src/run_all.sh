#!/bin/sh
# 03 は2コアで約1.5時間、03b は約1.3時間（strategy_predictions.csv.gz は約34MBのため GitHub には置いていない。03 を回すと作られる）
set -e
cd "$(dirname "$0")"
python3 02_整形.py
python3 03_分析.py
python3 03b_頑健性.py
python3 03c_補正と分解.py
python3 04_図.py
