#!/bin/sh
# 02_build → 03_analysis → 04_figures（オフライン。01_fetch は呼ばない）
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
set -e
cd "$(dirname "$0")"
python3 -W ignore 02_build.py > /dev/null
python3 -W ignore 03_analysis.py > /dev/null
python3 -W ignore 04_figures.py
