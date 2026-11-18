# 元データの出典（取得日と URL）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| esri_qe2026q2_2nd_gaku-mcy2622.csv | 内閣府「四半期別GDP速報」2026年4-6月期2次速報 名目暦年（10億円） | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-mcy2622.csv | 670fd1130075 |
| esri_qe2026q2_2nd_gaku-jcy2622.csv | 同 実質暦年（2020暦年連鎖価格、10億円） | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-jcy2622.csv | 643aa68da128 |
| esri_qe2026q2_2nd_def-cy2622.csv | 同 暦年デフレーター（2020暦年＝100） | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/def-cy2622.csv | 63feb78a211a |
| cpi2025_middle_annual_cy.csv | 総務省「消費者物価指数」2025年基準 全国 中分類指数 **年平均（暦年）**（1970〜2025年）。e-Stat statInfId 000040482829 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482829&fileKind=1 | f639475ca393 |

- どの CSV も Shift_JIS（cp932）。
- CPI は暦年の表を使った。e-Stat には同じ形の「年度平均」の表（000040482957）があるが、GDP の暦年の値と比べるため使っていない。
- GDP の速報値は、のちの年次推計で改訂される。ここでは2026年4-6月期2次速報の時点の値。
- 出典：内閣府「国民経済計算（四半期別GDP速報）」、総務省統計局「消費者物価指数」（政府統計の総合窓口 e-Stat）。
