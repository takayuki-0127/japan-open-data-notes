#!/bin/bash
# 2回目以降も同じ結果になる（乱数の種は固定）。全体で7分ほど
set -e
cd "$(dirname "$0")"
python p01_main.py
python p01_figures.py
