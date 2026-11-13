-- 履歴から、@asof の日の終わりに有効だった状態を戻す（T-SQL、SQL Server では未検証）
DECLARE @asof date = '2024-12-31';
WITH h AS (
  SELECT app_id, status, valid_from,
         COALESCE(LEAD(valid_from) OVER (PARTITION BY app_id ORDER BY valid_from, seq),
                  CAST('9999-12-31' AS date)) AS valid_to
  FROM dbo.status_history
  -- 当時見えていた数にするには、ここに WHERE recorded_on <= @asof を足す
)
SELECT status, COUNT(*) AS n
FROM h
WHERE valid_from <= @asof AND @asof < valid_to
GROUP BY status
ORDER BY status;
