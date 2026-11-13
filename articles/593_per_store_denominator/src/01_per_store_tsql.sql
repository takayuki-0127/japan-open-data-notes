-- 月ごとの「1店あたり売上」を3つの分母で出す（T-SQL、未検証）
WITH months AS (
  SELECT DISTINCT DATEFROMPARTS(YEAR(sold_on), MONTH(sold_on), 1) AS m FROM dbo.daily_sales
), sales_m AS (
  SELECT DATEFROMPARTS(YEAR(sold_on), MONTH(sold_on), 1) AS m, SUM(amount) AS amount
  FROM dbo.daily_sales
  GROUP BY DATEFROMPARTS(YEAR(sold_on), MONTH(sold_on), 1)
), store_m AS (
  SELECT
    mo.m,
    SUM(CASE WHEN s.open_date <= EOMONTH(mo.m)
              AND (s.close_date IS NULL OR s.close_date > EOMONTH(mo.m)) THEN 1 ELSE 0 END) AS stores_end,
    SUM(CASE WHEN s.open_date <= mo.m
              AND (s.close_date IS NULL OR s.close_date >= mo.m) THEN 1 ELSE 0 END)          AS stores_begin,
    SUM(CASE WHEN x.d_from <= x.d_to THEN DATEDIFF(day, x.d_from, x.d_to) + 1 ELSE 0 END)  AS store_days
  FROM months AS mo
  CROSS JOIN dbo.stores AS s
  CROSS APPLY (SELECT
      CASE WHEN s.open_date > mo.m THEN s.open_date ELSE mo.m END AS d_from,
      CASE WHEN s.close_date IS NOT NULL AND s.close_date < EOMONTH(mo.m) THEN s.close_date ELSE EOMONTH(mo.m) END AS d_to) AS x
  GROUP BY mo.m
)
SELECT
  m, amount, stores_end, stores_begin, store_days,
  amount / stores_end                                        AS per_store_month_end,
  amount / ((stores_begin + stores_end) / 2.0)               AS per_store_avg,
  amount / store_days * DAY(EOMONTH(m))                      AS per_store_open_days
FROM sales_m JOIN store_m ON store_m.m = sales_m.m
ORDER BY m;
