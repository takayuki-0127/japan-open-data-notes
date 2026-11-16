# data/raw の出典

取得日：2026-11-16（`src/01_fetch.py` で取得）

| ファイル | 内容 | URL |
|---|---|---|
| nies_ghg_1990_2024_L5-7gas_2026_gioweb_ver1.0.xlsx | 国立環境研究所 温室効果ガスインベントリオフィス（GIO）「日本の温室効果ガス排出量データ（1990〜2024年度）」 | https://www.nies.go.jp/gio/archive/ghgdata/k6efli000007q2e2-att/L5-7gas_2026_gioweb_ver1.0.xlsx （一覧：https://www.nies.go.jp/gio/archive/ghgdata/index.html） |

使ったシート：1.Summary（エネルギー起源・非エネルギー起源 CO2、温室効果ガスの合計）、3.Allocated_CO2-sector（電気・熱配分後の部門別 CO2）、5.CO2-fuel（燃料別 CO2、各部門の電力の行）、9.GHG-capita（人口）、10.GHG-GDP（実質 GDP、支出側）。Excel の式のセルは、ファイルに保存された計算済みの値を読んでいる。部門の合計はエネルギー起源 CO2 と一致した。

一次エネルギー供給（資源エネルギー庁「総合エネルギー統計」）は、サイトがこの作業の環境からの自動取得を受け付けなかったため使っていない。
