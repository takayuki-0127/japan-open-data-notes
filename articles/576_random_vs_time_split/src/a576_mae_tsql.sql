-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 時間順に分ける：日付の順で最後の20%を確かめ用にする
WITH s AS (
    SELECT d.*, NTILE(5) OVER (ORDER BY d.day_index) AS fifth
    FROM dbo.daily_values AS d
)
SELECT CASE WHEN fifth = 5 THEN 'test' ELSE 'train' END AS part,
       MIN(day_index) AS first_day, MAX(day_index) AS last_day, COUNT(*) AS n
FROM s
GROUP BY CASE WHEN fifth = 5 THEN 'test' ELSE 'train' END;

-- 予測を入れた表から、確かめ方ごとの MAE
SELECT method, COUNT(*) AS n, AVG(ABS(actual - pred)) AS mae
FROM dbo.preds
GROUP BY method
ORDER BY method;
