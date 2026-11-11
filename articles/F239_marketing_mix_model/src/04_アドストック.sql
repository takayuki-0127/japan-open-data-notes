-- 04 アドストック（広告の効き目の持ち越し）を SQL で計算する（SQL Server / T-SQL の書き方）
-- 入力：sim_weekly（週, テレビ, Web, チラシ, 売上）  ※架空の会社「みどりホーム（架空）」のシミュレーションデータ
-- アドストック：a_t = 広告費_t + 減り方 × a_{t-1}（テレビの減り方 0.6）
WITH ad AS (
    SELECT 週, CAST(テレビ AS FLOAT) AS a
    FROM sim_weekly
    WHERE 週 = 0
    UNION ALL
    SELECT s.週, s.テレビ + 0.6 * ad.a
    FROM sim_weekly AS s
    JOIN ad ON s.週 = ad.週 + 1
)
SELECT
    COUNT(*)                         AS 週数,
    SUM(a)                           AS アドストック合計,
    MAX(a)                           AS アドストック最大,
    AVG(a)                           AS アドストック平均
FROM ad
OPTION (MAXRECURSION 0);
-- 媒体別の広告費と、売上の 52 週移動平均（ダッシュボード用）
SELECT 週,
       SUM(テレビ + Web + チラシ) OVER (ORDER BY 週 ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS 広告費_4週計,
       AVG(売上) OVER (ORDER BY 週 ROWS BETWEEN 51 PRECEDING AND CURRENT ROW)            AS 売上_52週平均
FROM sim_weekly
ORDER BY 週;
