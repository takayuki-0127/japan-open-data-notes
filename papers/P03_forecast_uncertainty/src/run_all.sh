#!/bin/bash
# P03 を最初から流す（b_hier.py は ETS を 2,146 回当てはめるので数分かかる）
set -e
cd "$(dirname "$0")"
python a_conformal.py
python b_hier.py
