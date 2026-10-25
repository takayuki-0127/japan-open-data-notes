#!/bin/sh
# 上から順に実行（PyMC の推定があるので全部で10分ほど）
set -e
cd "$(dirname "$0")"
python 01_load.py
python 02_bsts.py
python 03_did_tokyo.py
python 04_synth.py
python 05_pref.py
python 06_figures.py
