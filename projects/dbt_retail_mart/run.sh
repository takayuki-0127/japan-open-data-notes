#!/usr/bin/env bash
# 最初から作り直して、dbt build と pandas との突き合わせを回す
set -euo pipefail
cd "$(dirname "$0")"
export DBT_PROFILES_DIR="$PWD"
rm -rf target
python3 tools/generate_data.py
python3 tools/check.py
