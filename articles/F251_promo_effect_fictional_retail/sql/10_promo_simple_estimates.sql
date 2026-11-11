-- 架空の販促（サンプルマート（架空））：簡単な3つの測り方を SQL で計算する（DuckDB で実行。SQL Server でも LN/EXP/SUM の形は同じ）。
-- 入力 store_week(store_id, k, treated, sales)：k＝クーポンの1週目を0とした週。対象外は開店・閉店の店（08・16・21・24）を除く。
WITH s AS (
  SELECT store_id, k, treated, sales FROM store_week
  WHERE treated = 1 OR store_id NOT IN (8, 16, 21, 24)
),
g AS (
  SELECT treated,
    SUM(CASE WHEN k BETWEEN 0 AND 7 THEN sales END)     AS promo,      -- 期間の8週
    SUM(CASE WHEN k BETWEEN -8 AND -1 THEN sales END)   AS before8,    -- 直前の8週
    SUM(CASE WHEN k BETWEEN -52 AND -45 THEN sales END) AS lastyear    -- 52週前の同じ8週
  FROM s GROUP BY treated
)
SELECT
  EXP(LN(t.promo / t.before8)) - 1                                   AS m1_before_after,
  EXP(LN(t.promo / t.lastyear)) - 1                                  AS m2_yoy,
  EXP(LN(t.promo / t.lastyear) - LN(c.promo / c.lastyear)) - 1       AS m3_yoy_diff
FROM g t JOIN g c ON t.treated = 1 AND c.treated = 0;
