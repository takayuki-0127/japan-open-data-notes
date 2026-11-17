#!/bin/sh
# オフラインで 02 から最後まで流す（01_fetch.py は呼ばない。data/raw に同梱済み）
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
set -e
cd "$(dirname "$0")/.."
python3 src/02_build.py > /dev/null
python3 src/03_analysis.py > /dev/null
python3 src/03b_requestion.py > /dev/null
python3 src/04_figures.py
