-- 月ごとの「1店あたり売上」を3つの分母で出す（DuckDB）
WITH months AS (
  SELECT DISTINCT date_trunc('month', sold_on)::DATE AS m FROM daily_sales
), sales_m AS (
  SELECT date_trunc('month', sold_on)::DATE AS m, SUM(amount) AS amount
  FROM daily_sales GROUP BY 1
), store_m AS (
  SELECT
    mo.m,
    -- 月末に営業している店（閉店日はその日まで営業）
    COUNT(*) FILTER (WHERE s.open_date <= last_day(mo.m)
                       AND (s.close_date IS NULL OR s.close_date > last_day(mo.m))) AS stores_end,
    -- 月初に営業している店
    COUNT(*) FILTER (WHERE s.open_date <= mo.m
                       AND (s.close_date IS NULL OR s.close_date >= mo.m))         AS stores_begin,
    -- 営業日数（店×日）：月の範囲と営業期間の重なり
    SUM(GREATEST(0, date_diff('day',
          GREATEST(s.open_date, mo.m),
          LEAST(COALESCE(s.close_date, DATE '9999-12-31'), last_day(mo.m))) + 1)) AS store_days
  FROM months mo CROSS JOIN stores s
  GROUP BY mo.m
)
SELECT
  m, amount, stores_end, stores_begin, store_days,
  amount / stores_end                                   AS per_store_month_end,
  amount / ((stores_begin + stores_end) / 2.0)          AS per_store_avg,
  amount / store_days * day(last_day(m))                AS per_store_open_days
FROM sales_m JOIN store_m USING (m)
ORDER BY m;
