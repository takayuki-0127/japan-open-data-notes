#!/bin/sh
set -e
cd "$(dirname "$0")"
python 01_build.py
python 02_forest.py
python 03_robustness.py   # 10分ほどかかります
python 04_figures.py
