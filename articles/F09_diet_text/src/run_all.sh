#!/bin/sh
# 01 は API を叩くので時間がかかる（約1,200回、1.2秒間隔）。data/ にある取得済みのファイルを使うなら 02 から
set -e
cd "$(dirname "$0")"
# python 01_fetch_api.py
python 02_tokenize.py
python 03_freq.py
python 04_cooc_topics.py
python lda_labels.py
python 05_figures.py
