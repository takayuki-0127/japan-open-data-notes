#!/bin/sh
# オフラインで 02 → 03 → 03b → 04 を順に流す（01_fetch.py は呼ばない）
set -e
python3 "$(dirname "$0")/00_join_parts.py"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")"
python3 02_build.py
python3 03_analysis.py > /dev/null
python3 03b_requestion.py > /dev/null
python3 04_figures.py
