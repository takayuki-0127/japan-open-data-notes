-- 430 在庫の評価の方法と月の粗利（T-SQL 版。SQL Server 本体では未検証）
-- purchases(item_id int, d date, seq int, qty int, unit_cost decimal(12,2))   … 期首の在庫も、最初の仕入れとして入れる
-- sales(item_id int, d date, seq int, qty int, unit_price decimal(12,2))

-- ① 先入先出：仕入れと販売を「累計の数量の区間」に直し、重なった数量に仕入れ値を掛ける
WITH p AS (
  SELECT item_id, unit_cost,
         SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING) - qty AS q_from,
         SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING)       AS q_to
  FROM purchases
),
s AS (
  SELECT item_id, d, qty * unit_price AS amount,
         SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING) - qty AS q_from,
         SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING)       AS q_to
  FROM sales
)
SELECT DATEFROMPARTS(YEAR(s.d), MONTH(s.d), 1) AS ym,
       SUM((CASE WHEN s.q_to < p.q_to THEN s.q_to ELSE p.q_to END
          - CASE WHEN s.q_from > p.q_from THEN s.q_from ELSE p.q_from END) * p.unit_cost) AS cogs_fifo
FROM s JOIN p ON p.item_id = s.item_id AND p.q_from < s.q_to AND p.q_to > s.q_from
GROUP BY DATEFROMPARTS(YEAR(s.d), MONTH(s.d), 1)
ORDER BY ym;

-- ② 総平均（月ごと）は、「月初の在庫の金額＋その月の仕入れ」÷「月初の数量＋その月の仕入れの数量」を
--    月の単価にする。月初の金額が前の月の単価で決まるので、月を順にたどる（再帰 CTE かループ）。
-- ③ 移動平均は、仕入れのたびに単価を作り直すので、取引を1件ずつ順にたどる。
