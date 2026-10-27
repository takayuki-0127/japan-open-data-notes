#!/bin/bash
# F37 を上から順に再現する（data/features.csv は F03 と同じもの）
set -e
cd "$(dirname "$0")"
python3 01_conformal_cv.py
python3 02_robustness.py
python3 03_breakdown_figures.py
python3 04_robust_figure.py
