-- 「直近30日」の4つの定義で、件数と金額を出す（DuckDB）。:now に実行時刻を入れる
WITH p AS (SELECT TIMESTAMP ':now' AS now_ts, CAST(TIMESTAMP ':now' AS DATE) AS today)
SELECT
  -- A 今日を含む30日（日付で切る。今日はその時刻までの途中の分）
  COUNT(*) FILTER (WHERE CAST(t.ts AS DATE) BETWEEN p.today - 29 AND p.today AND t.ts <= p.now_ts) AS a_n,
  SUM(amount) FILTER (WHERE CAST(t.ts AS DATE) BETWEEN p.today - 29 AND p.today AND t.ts <= p.now_ts) AS a_amt,
  -- B 今日を含まない30日（昨日までの30日分）
  COUNT(*) FILTER (WHERE CAST(t.ts AS DATE) BETWEEN p.today - 30 AND p.today - 1) AS b_n,
  SUM(amount) FILTER (WHERE CAST(t.ts AS DATE) BETWEEN p.today - 30 AND p.today - 1) AS b_amt,
  -- C 時刻で切る（今から720時間前まで）
  COUNT(*) FILTER (WHERE t.ts > p.now_ts - INTERVAL 30 DAY AND t.ts <= p.now_ts) AS c_n,
  SUM(amount) FILTER (WHERE t.ts > p.now_ts - INTERVAL 30 DAY AND t.ts <= p.now_ts) AS c_amt,
  -- D 両端を含めて31日分になる書き方（today - 30 から今日まで）
  COUNT(*) FILTER (WHERE CAST(t.ts AS DATE) BETWEEN p.today - 30 AND p.today AND t.ts <= p.now_ts) AS d_n,
  SUM(amount) FILTER (WHERE CAST(t.ts AS DATE) BETWEEN p.today - 30 AND p.today AND t.ts <= p.now_ts) AS d_amt
FROM transactions t, p;
