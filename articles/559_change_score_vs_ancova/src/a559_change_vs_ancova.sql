-- 前後の差の比較と、前の値を入れた回帰（共分散分析）の効果（DuckDB で実行）
-- 回帰 y1 = a + 効果 × 施策 + b × y0 の「効果」は、群内でまとめた傾き b を使って
--   (後の差) − b × (前の差) と書ける
WITH g AS (
    SELECT treated,
           AVG(sales_before)                 AS m0,
           AVG(sales_after)                  AS m1,
           AVG(sales_after - sales_before)   AS mchg
    FROM stores GROUP BY treated
), w AS (                                    -- 群内の共分散と分散（群平均を引いて合計）
    SELECT SUM((s.sales_before - g.m0) * (s.sales_after - g.m1)) AS sxy,
           SUM((s.sales_before - g.m0) * (s.sales_before - g.m0)) AS sxx
    FROM stores s JOIN g USING (treated)
), t AS (
    SELECT MAX(CASE WHEN treated = 1 THEN m0 END) - MAX(CASE WHEN treated = 0 THEN m0 END)     AS pre_gap,
           MAX(CASE WHEN treated = 1 THEN m1 END) - MAX(CASE WHEN treated = 0 THEN m1 END)     AS post_gap,
           MAX(CASE WHEN treated = 1 THEN mchg END) - MAX(CASE WHEN treated = 0 THEN mchg END) AS change_score_diff
    FROM g
)
SELECT t.change_score_diff,
       w.sxy / w.sxx                              AS pooled_slope,
       t.post_gap - (w.sxy / w.sxx) * t.pre_gap   AS ancova_effect
FROM t, w;
