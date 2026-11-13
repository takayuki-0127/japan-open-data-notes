-- T-SQL：未検証（SQL Server では動かしていない）
-- 週の途中の比べ方。dbo.daily(store, d date, sales)。週は月曜始まり。@asof の日の終わりに見る
DECLARE @wk date = DATEADD(day, -((DATEPART(weekday, @asof) + @@DATEFIRST - 2) % 7), @asof);  -- その週の月曜
SELECT
  SUM(CASE WHEN d >= @wk AND d <= @asof THEN sales END)                                    AS this_week_to_date,
  SUM(CASE WHEN d >= DATEADD(day, -7, @wk) AND d < @wk THEN sales END)                     AS last_week_total,
  SUM(CASE WHEN d >= DATEADD(day, -7, @wk) AND d <= DATEADD(day, -7, @asof) THEN sales END) AS last_week_to_same_day
FROM dbo.daily
WHERE store = @store;
