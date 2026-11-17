# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| L5-7gas_2026_gioweb_ver1.0.xlsx | 2026年版（1990〜2024年度） | https://www.nies.go.jp/gio/archive/ghgdata/k6efli000007q2e2-att/L5-7gas_2026_gioweb_ver1.0.xlsx | 351fdd30ea5f |
| L5-7gas_2025_gioweb_1.0.xlsx | 2025年版（1990〜2023年度）照合用 | https://www.nies.go.jp/gio/archive/ghgdata/jqjm1000000ie8om-att/L5-7gas_2025_gioweb_1.0.xlsx | 5333343888d6 |

出典：国立環境研究所 温室効果ガスインベントリオフィス（GIO）「日本の温室効果ガス排出量データ」（https://www.nies.go.jp/gio/archive/ghgdata/index.html）。
使うシート：1.Summary（ガス別の排出量）、8.F-gas（代替フロン等4ガスの用途別）。単位は百万トンCO2換算（Summary）、千トンCO2換算（F-gas）。
