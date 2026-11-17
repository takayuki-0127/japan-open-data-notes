# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）。最終更新日は令和8年11月10日（2026年10月分まで）。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| monthb1.csv | 財務省「対外及び対内証券売買契約等の状況」投資家部門別対外証券投資（合計）、月次、2005年1月〜、億円、Shift_JIS | https://www.mof.go.jp/policy/international_policy/reference/itn_transactions_in_securities/monthb1.csv | 75f39d8545b8 |
| monthb2.csv | 同（株式・投資ファンド持分） | https://www.mof.go.jp/policy/international_policy/reference/itn_transactions_in_securities/monthb2.csv | 42b996f4d8f8 |
| monthb3.csv | 同（中長期債） | https://www.mof.go.jp/policy/international_policy/reference/itn_transactions_in_securities/monthb3.csv | 5e777489f70f |
| monthb4.csv | 同（短期債） | https://www.mof.go.jp/policy/international_policy/reference/itn_transactions_in_securities/monthb4.csv | d8a84b7bbd08 |

注（ファイルの注記より）：端数の関係で合計が合わないことがある。取得超を正、処分超を負で示す。2007年9月30日の金融商品取引法の施行にあわせて部門の区分が変わり、それより前は旧区分で集計されている。投資信託委託会社等には資産運用会社（投資顧問など）を含む。
