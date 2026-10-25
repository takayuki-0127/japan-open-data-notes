#!/bin/bash
# 上から順に実行すると data/panel.csv → results/ → figures/ が再現される（PyMC の乱数の種は common.SEED で固定）
set -e
cd "$(dirname "$0")"
python3 01_load.py
python3 03_fit.py      # 02_model.py はここから読み込まれる（約5分）
python3 04_figures.py
