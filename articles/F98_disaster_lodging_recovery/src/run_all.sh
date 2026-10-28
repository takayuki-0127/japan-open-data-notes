#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 01_取得.py
python3 02_整形.py
python3 03_分析.py
python3 03b_失われた宿泊.py
python3 04_図.py
