# 元データの出典（取得日と URL）

取得日：2026-11-18（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| mokuzai_jukyu_ruinen_total.xlsx | 木材需要（供給）量累年統計（用途別の需要・国内生産・輸入、自給率）1955〜2024年 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040370311&fileKind=0 | 3e9bb3562cba |
| mokuzai_jukyu_ruinen_demand.xlsx | 需要量（国内消費量、輸出量）累年統計 1955〜2024年 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040370312&fileKind=0 | 0f19992518bf |
| mokuzai_jukyu_ruinen_supply.xlsx | 供給量（国内生産量、輸入量）累年統計（輸入の丸太・製品の別）1955〜2024年 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040370313&fileKind=0 | 38a03e9a96f0 |

- 統計表一覧（木材需給表 長期累年）：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00501000&tstat=000001021364&cycle=0&tclass1=000001031549
- 単位は丸太に換算した体積（千m3）。2024年は令和6年木材需給表（2025-11-21 公表）の値。
- 出典：林野庁「木材需給表」（e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。
