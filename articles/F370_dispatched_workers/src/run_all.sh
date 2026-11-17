#!/bin/sh
# オフラインで 02 → 03 → 04 を流す（01_fetch.py は呼ばない）
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261116
set -e
cd "$(dirname "$0")"
python3 -I 02_build.py > /dev/null
python3 -I 03_analysis.py > /dev/null
python3 -I 04_figures.py
