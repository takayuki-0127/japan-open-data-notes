#!/bin/sh
# 01_data → 02_design_a → 03_design_b → 04_figures（src/ で実行）
set -e
cd "$(dirname "$0")"
python 01_data.py
python 02_design_a.py
python 03_design_b.py
python 04_figures.py
