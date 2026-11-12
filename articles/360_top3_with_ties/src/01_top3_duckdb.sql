-- 店ごとの「販売数の上位3件」を4通りで取る（DuckDB で実行した版）
-- store_sales(store_id, product_id, units, amount)
WITH r AS (
  SELECT store_id, product_id, units,
         ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY units DESC)             AS rn,       -- 同点の順は決まっていない
         ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY units DESC, product_id) AS rn_tie,   -- 同点は商品番号の小さい順
         RANK()       OVER (PARTITION BY store_id ORDER BY units DESC)             AS rk,
         DENSE_RANK() OVER (PARTITION BY store_id ORDER BY units DESC)             AS dr
  FROM store_sales
)
SELECT store_id,
       COUNT(*) FILTER (WHERE rn     <= 3) AS n_row_number,
       COUNT(*) FILTER (WHERE rn_tie <= 3) AS n_row_number_tiebreak,
       COUNT(*) FILTER (WHERE rk     <= 3) AS n_rank,
       COUNT(*) FILTER (WHERE dr     <= 3) AS n_dense_rank
FROM r GROUP BY store_id ORDER BY store_id;
