-- 口座ごとの残高の累計（T-SQL。SQL Server 本体では動かしていません：未検証）
-- tx(acct, d, seq, amount)：seq は同じ口座・同じ日の中での順番
SELECT acct, d, seq, amount,
       -- ① 枠を書かない：ORDER BY があるときの既定は RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       SUM(amount) OVER (PARTITION BY acct ORDER BY d) AS bal_range,
       -- ② ROWS と書くが、並べる列は日付だけ（同じ日の中の順番は実行のたびに変わりうる）
       SUM(amount) OVER (PARTITION BY acct ORDER BY d
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS bal_rows_date_only,
       -- ③ ROWS と書き、並べる列を一意にする
       SUM(amount) OVER (PARTITION BY acct ORDER BY d, seq
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS bal_rows_unique
FROM tx;
