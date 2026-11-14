-- PARTITION BY あり・なしで、4つのウィンドウ関数を並べて出す（DuckDB 版）
-- daily(store_id, sale_date, sales)
SELECT store_id, sale_date, sales,
  -- 店ごとの累計
  SUM(sales) OVER (PARTITION BY store_id ORDER BY sale_date)                                   AS cum_ok,
  SUM(sales) OVER (ORDER BY sale_date)                                                          AS cum_ng,
  -- 7日の移動平均
  AVG(sales) OVER (PARTITION BY store_id ORDER BY sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma7_ok,
  AVG(sales) OVER (ORDER BY store_id, sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)            AS ma7_ng,
  -- 前日の売上
  LAG(sales) OVER (PARTITION BY store_id ORDER BY sale_date)                                    AS prev_ok,
  LAG(sales) OVER (ORDER BY store_id, sale_date)                                                AS prev_ng,
  -- その日の店の順位
  RANK() OVER (PARTITION BY sale_date ORDER BY sales DESC)                                      AS rank_ok,
  RANK() OVER (ORDER BY sales DESC)                                                             AS rank_ng
FROM daily
ORDER BY store_id, sale_date;
-- GROUP BY で累計を出す（自分より前の日を足す）
SELECT a.store_id, a.sale_date, SUM(b.sales) AS cum_groupby
FROM daily AS a JOIN daily AS b ON b.store_id = a.store_id AND b.sale_date <= a.sale_date
GROUP BY a.store_id, a.sale_date
ORDER BY a.store_id, a.sale_date;
