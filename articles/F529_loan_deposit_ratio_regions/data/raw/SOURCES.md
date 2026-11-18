# 元データの出典（取得日と URL）

| ファイル | 中身 | 系列数または URL | 取得日 |
|---|---|---|---|
| boj_MD12_deposits_total.json | 日本銀行 都道府県別預金・現金・貸出金（MD12） | 56 | 2026-11-19 |
| boj_MD12_deposits_general.json | 日本銀行 都道府県別預金・現金・貸出金（MD12） | 56 | 2026-11-19 |
| boj_MD12_deposits_personal.json | 日本銀行 都道府県別預金・現金・貸出金（MD12） | 56 | 2026-11-19 |
| boj_MD12_deposits_public.json | 日本銀行 都道府県別預金・現金・貸出金（MD12） | 56 | 2026-11-19 |
| boj_MD12_deposits_fin.json | 日本銀行 都道府県別預金・現金・貸出金（MD12） | 56 | 2026-11-19 |
| boj_MD12_cd.json | 日本銀行 都道府県別預金・現金・貸出金（MD12） | 56 | 2026-11-19 |
| boj_MD12_loans.json | 日本銀行 都道府県別預金・現金・貸出金（MD12） | 56 | 2026-11-19 |
| boj_pref_pre2603.xlsx | 日本銀行「都道府県別預金・現金・貸出金（国内銀行）＜2026年3月末＞」公表資料（照らし合わせ用） | https://www.boj.or.jp/statistics/dl/depo/pref/pre2603.xlsx | 2026-11-19 |

- 取得の URL の形：https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=MD12&code=<系列コードをカンマでつないだもの（01_fetch.py の SETS）>
- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/ （API 利用）
- 出典を示して加工して使う（日本銀行の利用規約）。
