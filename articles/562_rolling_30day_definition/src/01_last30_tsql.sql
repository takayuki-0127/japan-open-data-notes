-- 「直近30日」の4つの定義（T-SQL、SQL Server では未検証）
DECLARE @now datetime2 = '2025-10-15 09:00:00';
DECLARE @today date = CAST(@now AS date);
SELECT
  -- A 今日を含む30日（今日は途中まで）
  SUM(CASE WHEN CAST(ts AS date) BETWEEN DATEADD(day, -29, @today) AND @today AND ts <= @now THEN amount END) AS a_amt,
  -- B 昨日までの30日
  SUM(CASE WHEN CAST(ts AS date) BETWEEN DATEADD(day, -30, @today) AND DATEADD(day, -1, @today) THEN amount END) AS b_amt,
  -- C 今から720時間前まで
  SUM(CASE WHEN ts > DATEADD(day, -30, @now) AND ts <= @now THEN amount END) AS c_amt,
  -- D 31日分になる書き方
  SUM(CASE WHEN CAST(ts AS date) BETWEEN DATEADD(day, -30, @today) AND @today AND ts <= @now THEN amount END) AS d_amt
FROM dbo.transactions;
