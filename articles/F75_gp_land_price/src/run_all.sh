#!/bin/bash
# 上から順に実行すると、図と数字がすべて再現できる（GP は計算に時間がかかる：2コアで合計1〜2時間ほど）
set -e
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python3 01_prepare.py
python3 02_cv.py
python3 03_map.py
python3 04_robust.py
python3 05_figures.py
