# SOURCES（元データの取得元）

取得日：2026-11-19（src/01_fetch.py と同じ URL から取得）。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| 6IIP.xls | 財務省「本邦対外資産負債残高の推移（時系列データ）」（年次改訂後の最新の計数）。暦年末、1996〜2025年、資産・負債の項目別と対外純資産、**単位10億円**。2013年末までは第5版基準の計数を第6版の基準に組み替えたもの。令和8年5月26日に令和6年末を一部改訂 | https://www.mof.go.jp/policy/international_policy/reference/iip/6IIP.xls | 2db386f05fd3 |
| iip_factors_2019.pdf | 財務省「令和元年末 本邦対外資産負債残高 増減要因（試算）」（概要の参考1） | https://www.mof.go.jp/policy/international_policy/reference/iip/2019_g1.pdf | 847e480a2020 |
| iip_factors_2020.pdf | 同 令和2年末 | https://www.mof.go.jp/policy/international_policy/reference/iip/2020_g1.pdf | 2c746a4114e2 |
| iip_factors_2021.pdf | 同 令和3年末 | https://www.mof.go.jp/policy/international_policy/reference/iip/2021_g1.pdf | f8fe9818aedf |
| iip_factors_2022.pdf | 同 令和4年末 | https://www.mof.go.jp/policy/international_policy/reference/iip/2022_g1.pdf | 9ad5b02de219 |
| iip_factors_2023.pdf | 同 令和5年末 | https://www.mof.go.jp/policy/international_policy/reference/iip/2023_g1.pdf | 51672497d9c7 |
| iip_factors_2024.pdf | 同 令和6年末 | https://www.mof.go.jp/policy/international_policy/reference/iip/2024_g1.pdf | 96b320733399 |
| iip_factors_2025.pdf | 同 令和7年末 | https://www.mof.go.jp/policy/international_policy/reference/iip/data/2025_g1.pdf | ef4186b60252 |
| boj_bp01_financial_account.json | 日本銀行 時系列統計データ検索サイト API（db=BP01）。国際収支統計（第6版基準）の金融収支（ネット、項目別、資産・負債別）、月次、1996年1月〜2026年9月、億円 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=（01_fetch.py の BP） | 75244210e368 |
| boj_fm08_usdjpy.json | 同 API（db=FM08）。東京市場 ドル・円 スポット 17時時点／月末（FXERM06） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM06 | b6cd92ce4896 |

## 抜き出し（data/extracted）

- PDF の表は src/01b_extract_pdf.py で pdftotext -layout（poppler-utils 24.02.0）にかけ、行の先頭の見出しの文字（「１．直接投資」「資産合計」「純資産合計」など）で項目を決めて数字を読んだ。テキスト（iip_factors_YYYY.txt）と抜き出し表（iip_factors.csv、fx_denominated.csv）を同梱し、run_all.sh はこの CSV から先だけを流す。
- 読んだ値は、02_build.py で「項目の和＝合計」「前年末比＝取引＋為替＋その他」「前年末＋前年末比＝当年末」が丸めの範囲（10億円で数単位）で成り立つことを確かめた（results/factor_checks.csv）。2019年と2025年の表は、PDF の画面の値とも目で照らした。
- 試算の値は各年の公表時のもので、のちの年次改訂は反映されていない（6IIP.xls の値と少し違う年がある）。
