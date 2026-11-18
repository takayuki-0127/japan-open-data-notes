# SOURCES（元データの取得元）

取得日：2026-11-18（01_fetch.py で取得）

| ファイル | URL | sha256 の先頭12字 |
|---|---|---|
| co2_monthave_ryo.csv | https://www.data.jma.go.jp/ghg/kanshi/obs/co2_monthave_ryo.csv | 41c070309713 |
| co2_monthave_mnm.csv | https://www.data.jma.go.jp/ghg/kanshi/obs/co2_monthave_mnm.csv | 10131a19b14e |
| co2_monthave_yon.csv | https://www.data.jma.go.jp/ghg/kanshi/obs/co2_monthave_yon.csv | fc35b208ef0d |
| page_co2_trend.html | https://www.data.jma.go.jp/ghg/kanshi/ghgp/co2_trend.html | f02f31bb1949 |
| nino3idx.html | https://www.data.jma.go.jp/cpd/db/elnino/index/nino3idx.html | 16c5be70a72f |
| L5-7gas_2026_gioweb_ver1.0.xlsx | https://www.nies.go.jp/gio/archive/ghgdata/k6efli000007q2e2-att/L5-7gas_2026_gioweb_ver1.0.xlsx | 351fdd30ea5f |

CO2 の CSV は Shift_JIS（cp932）。単位は ppm。与那国島は2024年3月末で観測を終えた（気象庁の解説ページ）。
排出量の Excel は国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ（1990〜2024年度）確報値」（https://www.nies.go.jp/gio/archive/ghgdata/index.html）。
