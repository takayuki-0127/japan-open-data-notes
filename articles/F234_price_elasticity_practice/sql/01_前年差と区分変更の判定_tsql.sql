-- F234：品目ごとの前年差（対数）と、区分の変更らしき年の判定（SQL Server / T-SQL）
-- 入力テーブル：dbo.kakei_items(code INT, name NVARCHAR(100), grp NVARCHAR(50), unit NVARCHAR(50),
--                                year INT, exp FLOAT, price FLOAT, q FLOAT)
WITH base AS (
    SELECT name, grp, year, exp,
           LOG(price) AS lp, LOG(q) AS lq,
           LAG(year)       OVER (PARTITION BY name ORDER BY year) AS prev_year,
           LAG(LOG(price)) OVER (PARTITION BY name ORDER BY year) AS prev_lp,
           LAG(LOG(q))     OVER (PARTITION BY name ORDER BY year) AS prev_lq,
           LAG(exp)        OVER (PARTITION BY name ORDER BY year) AS prev_exp
    FROM dbo.kakei_items
    WHERE price > 0 AND q > 0
),
d AS (
    SELECT name, grp, year, prev_exp,
           CASE WHEN year - prev_year = 1 THEN lp - prev_lp END AS dlp,
           CASE WHEN year - prev_year = 1 THEN lq - prev_lq END AS dlq
    FROM base
)
SELECT name, grp, year, dlp, dlq,
       CASE WHEN ABS(dlq) > 0.7 OR ABS(dlp) > 0.5 THEN 1 ELSE 0 END AS break_flag,
       prev_exp * 1.0 / SUM(prev_exp) OVER (PARTITION BY year) AS w
INTO dbo.kakei_item_diff
FROM d
WHERE dlp IS NOT NULL;

-- 群ごとの単純な弾力性（年の平均を引いてから、量の変化÷値段の変化の回帰の傾き）
WITH ym AS (
    SELECT year, AVG(dlp) AS mp, AVG(dlq) AS mq
    FROM dbo.kakei_item_diff WHERE break_flag = 0 GROUP BY year
), x AS (
    SELECT k.grp, k.dlp - ym.mp AS p, k.dlq - ym.mq AS q
    FROM dbo.kakei_item_diff k JOIN ym ON ym.year = k.year
    WHERE k.break_flag = 0
)
SELECT grp,
       COUNT(*) AS n,
       (AVG(p * q) - AVG(p) * AVG(q)) / NULLIF(AVG(p * p) - AVG(p) * AVG(p), 0) AS elasticity
FROM x GROUP BY grp ORDER BY elasticity;
