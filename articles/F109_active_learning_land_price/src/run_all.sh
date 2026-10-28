#!/bin/sh
# F109 を最初から再現する（全体で1.5〜2時間ほど。CPU 1コア想定）
cd "$(dirname "$0")/.."
python3 src/01_取得.py
python3 src/02_整形.py
python3 src/03_能動学習.py main
python3 src/03_能動学習.py full
python3 src/03_能動学習.py robust
python3 src/04_図.py
