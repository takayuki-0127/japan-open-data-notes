-- 口座ごとの残高の累計を3通りで出す（DuckDB で実行した版）
-- tx(acct, d, seq, amount)：seq は同じ口座・同じ日の中での順番
SELECT acct, d, seq, amount,
       -- ① 枠を書かない（既定は RANGE … CURRENT ROW）：同じ日の行は、その日の最後までを足した値になる
       SUM(amount) OVER (PARTITION BY acct ORDER BY d) AS bal_range,
       -- ② ROWS と書くが、並べる列は日付だけ：同じ日の中の順番は決まっていない
       SUM(amount) OVER (PARTITION BY acct ORDER BY d
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS bal_rows_date_only,
       -- ③ ROWS と書き、並べる列を一意にする（日付＋その日の中の順番）
       SUM(amount) OVER (PARTITION BY acct ORDER BY d, seq
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS bal_rows_unique
FROM tx;
