-- F237：A/B テストの日別データから、累積の購入率・z・止める判定を出す（SQL Server / T-SQL）
-- テーブル
--   ab_daily(day INT, arm CHAR(1), visitors INT, conversions INT)   -- arm は 'A'（いまの画面）と 'B'（新しい画面）
--   seq_bounds(day INT, bound FLOAT)                                -- 事前に決めた「見る日」と境界（O'Brien-Fleming の α 消費、4回）
-- 2つの割合の差の z（併合した割合で標準誤差）を毎日出し、
--   naive_stop：毎日 1.96 で判定した場合（やってはいけない例）
--   seq_stop  ：決めた日にだけ、決めた境界で判定した場合
-- を並べる。止める判定は「最初に越えた日」以降は 1 のまま（累積の最大）。
WITH cum AS (
    SELECT day, arm,
           SUM(visitors)    OVER (PARTITION BY arm ORDER BY day ROWS UNBOUNDED PRECEDING) AS n_cum,
           SUM(conversions) OVER (PARTITION BY arm ORDER BY day ROWS UNBOUNDED PRECEDING) AS c_cum
    FROM ab_daily
), wide AS (
    SELECT day,
           MAX(CASE WHEN arm = 'A' THEN n_cum END) AS nA, MAX(CASE WHEN arm = 'A' THEN c_cum END) AS cA,
           MAX(CASE WHEN arm = 'B' THEN n_cum END) AS nB, MAX(CASE WHEN arm = 'B' THEN c_cum END) AS cB
    FROM cum GROUP BY day
), z AS (
    SELECT w.day, w.nA, w.cA, w.nB, w.cB,
           CAST(w.cA AS FLOAT) / w.nA AS pA,
           CAST(w.cB AS FLOAT) / w.nB AS pB,
           (CAST(w.cB AS FLOAT) / w.nB - CAST(w.cA AS FLOAT) / w.nA)
             / SQRT( (CAST(w.cA + w.cB AS FLOAT) / (w.nA + w.nB)) * (1 - CAST(w.cA + w.cB AS FLOAT) / (w.nA + w.nB))
                     * (1.0 / w.nA + 1.0 / w.nB) ) AS z
    FROM wide AS w
)
SELECT z.day, z.nA, z.cA, z.nB, z.cB, z.pA, z.pB,
       z.pB / NULLIF(z.pA, 0) - 1 AS lift, z.z,
       b.bound,
       MAX(CASE WHEN ABS(z.z) >= 1.959964 THEN 1 ELSE 0 END)
           OVER (ORDER BY z.day ROWS UNBOUNDED PRECEDING) AS naive_stop,
       MAX(CASE WHEN b.bound IS NOT NULL AND ABS(z.z) >= b.bound THEN 1 ELSE 0 END)
           OVER (ORDER BY z.day ROWS UNBOUNDED PRECEDING) AS seq_stop
FROM z LEFT JOIN seq_bounds AS b ON b.day = z.day
ORDER BY z.day;
