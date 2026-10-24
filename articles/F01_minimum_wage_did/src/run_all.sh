#!/bin/sh
# 上から順に実行（04 は wild bootstrap と並べ替え検定で数分かかります）
set -e
cd "$(dirname "$0")"
python 01_build_panel.py
python 02_twfe.py
python 03_event_study.py
python 04_robustness.py
python 05_figures.py
