# 元データの出典（取得日と URL）

| ファイル | 中身 | URL | 取得日 |
|---|---|---|---|
| boj_FM02_call_rate_monthly.json | 日本銀行 時系列統計データ（FM02：STRACLUCON, STRECLUCON） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM02&code=STRACLUCON,STRECLUCON | 2026-11-19 |
| boj_IR02_posted_monthly.json | 日本銀行 時系列統計データ（IR02：DLDR121N, DLDR43TL61YN, DLDR43TL63MN, DLDR43TL65YN, DLDR43TL41YN） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=IR02&code=DLDR121N,DLDR43TL61YN,DLDR43TL63MN,DLDR43TL65YN,DLDR43TL41YN | 2026-11-19 |
| boj_IR02_posted_weekly_2007.json | 日本銀行 時系列統計データ（IR02：DLDR120N, DLDR43TL31YN, DLDR43TL33MN, DLDR43TL35YN, DLDR43TL11YN） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=IR02&code=DLDR120N,DLDR43TL31YN,DLDR43TL33MN,DLDR43TL35YN,DLDR43TL11YN | 2026-11-19 |
| boj_IR02_posted_weekly_1994_ordinary.json | 日本銀行 時系列統計データ（IR02：DLDR120） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=IR02&code=DLDR120 | 2026-11-19 |
| boj_IR02_posted_weekly_1991_time.json | 日本銀行 時系列統計データ（IR02：DLDR43TL31Y, DLDR43TL33M, DLDR43TL35Y, DLDR43TL11Y） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=IR02&code=DLDR43TL31Y,DLDR43TL33M,DLDR43TL35Y,DLDR43TL11Y | 2026-11-19 |
| boj_IR03_new_time_deposits.json | 日本銀行 時系列統計データ（IR03：DLDRK_DLDR442DB, DLDRK_DLDR442DBKT, DLDRK_DLDR442DBFT, DLDRK_DLDR442DBKT5） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=IR03&code=DLDRK_DLDR442DB,DLDRK_DLDR442DBKT,DLDRK_DLDR442DBFT,DLDRK_DLDR442DBKT5 | 2026-11-19 |

- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/ （API 利用）
- FM02：コールレート、IR02：預金種類別店頭表示金利の平均年利率等、IR03：定期預金の預入期間別平均金利（新規受入分）
- 出典を示して加工して使う（日本銀行の利用規約）。
