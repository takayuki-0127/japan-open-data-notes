-- 店ごとの申込み率を3通りで出す（DuckDB）
SELECT store_id,
       COUNT(*)                                                    AS days,
       COUNT(applications * 1.0 / NULLIF(visits, 0))              AS days_used,       -- NULLIF で NULL になった日は数えない
       AVG(applications * 1.0 / NULLIF(visits, 0))                AS avg_daily_nullif, -- 来店0の日は黙って消える
       AVG(COALESCE(applications * 1.0 / NULLIF(visits, 0), 0))   AS avg_daily_zero,   -- 来店0の日を率0とする
       SUM(applications) * 1.0 / NULLIF(SUM(visits), 0)           AS rate_total        -- 合計から率
FROM daily
GROUP BY store_id
ORDER BY store_id;
