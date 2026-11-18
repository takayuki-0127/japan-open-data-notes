# SOURCES（元データの取得元）

取得日：2026-11-19（src/01_fetch.py と同じ URL から取得）。資金循環統計の最終更新は2026年9月17日（2026年4〜6月期速報まで）。日本銀行勘定は2026年10月末まで。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_ff_jgb.json | 日本銀行「資金循環統計」（時系列統計データ検索サイト API、db=FF）。国債・財投債（A311）と国庫短期証券（A310）の部門別残高（ストック、時価）、主な部門の取引（フロー）と調整、発行残高（一般政府・財政融資資金、時価と額面）。四半期、1997年10〜12月期〜2026年4〜6月期、億円。系列は 71 本（コードは 01_fetch.py に列挙） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FF&code=（系列コード） | 5f43d8481509 |
| boj_bs01_jgb.json | 日本銀行「日本銀行勘定」（同 API、db=BS01）。国債、短期国債、長期国債の月末残高（MABJMA5・5A・5B）、億円 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BS01&code=MABJMA5,MABJMA5A,MABJMA5B | 1ce553f7e8fa |
| sjlong.xlsx | 日本銀行「資金循環統計」参考図表（時系列表）。照らし合わせだけに使う（シート64：国内発行債券の発行体別かつ保有者別残高、2024年1〜3月期〜） | https://www.boj.or.jp/statistics/sj/sjlong.xlsx | 0711b2e3bf32 |

- 資金循環統計の日付 YYYY0Q は四半期（例 202602＝2026年4〜6月期）。直近の期は速報で、のちに改定される。
- 残高の差＝取引＋調整（調整には時価の変化などを含む）。この恒等式が全期で誤差0で成り立つことを 03_analysis.py で確かめた（results/boj_decomp.csv）。
- 系列のコードと名称の対応は data/series_names.csv。部門の名前は名称の「／部門／」の文字から付けた。
