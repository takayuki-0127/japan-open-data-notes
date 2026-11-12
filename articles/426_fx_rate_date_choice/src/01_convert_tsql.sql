-- 426 外貨の売上を円に直す：取引日のレート・月中平均・月末レート（T-SQL 版。SQL Server 本体では未検証）
-- rates(rate_date date, usdjpy decimal(9,2))  …  東京市場の営業日だけ
-- txn(txn_id int, txn_date date, usd decimal(18,2))

-- 月ごとの平均レートと月末レート
WITH m AS (
  SELECT DATEFROMPARTS(YEAR(rate_date), MONTH(rate_date), 1) AS ym,
         AVG(usdjpy) AS avg_rate,
         MAX(rate_date) AS last_day
  FROM rates
  GROUP BY DATEFROMPARTS(YEAR(rate_date), MONTH(rate_date), 1)
),
m2 AS (
  SELECT m.ym, m.avg_rate, r.usdjpy AS end_rate,
         LAG(r.usdjpy) OVER (ORDER BY m.ym) AS prev_end_rate
  FROM m JOIN rates r ON r.rate_date = m.last_day
)
SELECT m2.ym,
       SUM(t.usd * r.usdjpy)          AS jpy_txn_date,   -- ① 取引日のレート
       SUM(t.usd) * MAX(m2.avg_rate)  AS jpy_month_avg,  -- ② 月中平均
       SUM(t.usd) * MAX(m2.end_rate)  AS jpy_month_end,  -- ③ 月末レート
       SUM(t.usd) * MAX(m2.prev_end_rate) AS jpy_prev_end -- ④ 前の月の月末レート
FROM txn t
JOIN rates r ON r.rate_date = t.txn_date
JOIN m2 ON m2.ym = DATEFROMPARTS(YEAR(t.txn_date), MONTH(t.txn_date), 1)
GROUP BY m2.ym
ORDER BY m2.ym;
