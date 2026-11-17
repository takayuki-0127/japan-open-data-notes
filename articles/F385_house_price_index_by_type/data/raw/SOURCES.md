# data/raw の出典

取得日：2026-11-17（`src/01_fetch.py` で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| rppi_residential_001473668.xlsx | 国土交通省「不動産価格指数（住宅）」季節調整値・原系列（2010年平均＝100、月次、2008年4月〜2025年12月。東京都・愛知県・大阪府の住宅地・戸建住宅は1984年4月から）。全国・10地方・三大都市圏・東京都・愛知県・大阪府 | https://www.mlit.go.jp/totikensangyo/content/001473668.xlsx | 76ad3577bd28 |
| transactions_001465569.xlsx | 国土交通省「不動産取引件数・面積」（指数の作成に使う、建物と土地の移転登記を突き合わせた件数。月次、2008年4月〜2025年12月） | https://www.mlit.go.jp/common/001465569.xlsx | b1e1498ca867 |
| cpi_middle_class_index.csv | 総務省「消費者物価指数」2025年基準 全国 中分類指数（1970年1月〜2026年9月、CSV、Shift_JIS）。総合だけを使う | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482943&fileKind=1 | 29b63b7aa5cb |

- 不動産価格指数のページ：https://www.mlit.go.jp/totikensangyo/totikensangyo_tk5_000085.html
- 表の注のとおり、東京都の2008年3月以前、愛知県・大阪府の2006年11月以前のデータは、国土交通省のほか（公社）東京都不動産鑑定士協会・（公社）愛知県不動産鑑定士協会・（公社）大阪府不動産鑑定士協会が出典です。
- 取引件数の注：別に公表されている既存住宅販売量指数の販売量とは異なります。
