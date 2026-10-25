#!/bin/sh
# 元データ（L01-26_GML, S12-25_GML）を data/raw/ に展開してから実行（別の場所なら F03_RAW=その場所）
set -e
cd "$(dirname "$0")"
python3 01_features.py
python3 02_baseline.py
python3 03_lgbm_cv.py
python3 04_shap.py
python3 05_figures.py
