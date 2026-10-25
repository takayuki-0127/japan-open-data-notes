# 元データ

| ファイル | 元 | 取り方 |
|---|---|---|
| mhlw_turnover_pdf_text.json | 厚生労働省「新規学卒就職者の離職状況」（https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000137940.html）の PDF：001318985（在職期間別離職状況・全学歴）、001319024（大学・産業別）、001319006（高校・産業別）、001319018（大学・事業所規模別）、001319002（高校・事業所規模別） | ブラウザで PDF を取得し、pdf.js 4.0.379 の getTextContent で文字を取り出し、y 座標で行に、x 座標で並べた（キーは PDF のファイル名）。2026年10月25日取得（令和7年3月卒までを含む版） |
| job_openings_national_annual.csv | 厚生労働省「一般職業紹介状況」の長期時系列（e-Stat） | 同じリポジトリの 090_job_openings_pref/data/pref_annual.csv から「受理地・全国」を抜き出した |
| lt01-a10.xlsx | 総務省統計局「労働力調査 長期時系列データ 基本集計 表1 a-1 主要項目」（e-Stat） | 同じリポジトリの 020_unemployment_sarima/data/raw/ と同じファイル |
