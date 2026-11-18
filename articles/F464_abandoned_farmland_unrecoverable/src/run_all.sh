#!/bin/sh
# オフラインで 02 → 03 → 03b → 04 を順に流す（01_fetch.py・01b_extract.py は呼ばない）
set -e
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")"
python3 -W ignore 02_build.py
python3 -W ignore 03_analysis.py
python3 -W ignore 03b_requestion.py
python3 -W ignore 04_figures.py
