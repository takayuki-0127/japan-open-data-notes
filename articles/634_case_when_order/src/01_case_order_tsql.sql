-- T-SQL：未検証（SQL Server では動かしていない）
-- 並べ方A：VIP → 常連 → 新規 → 休眠（上から順に、最初に当てはまった区分になる）
SELECT seg, COUNT(*) AS n FROM (
  SELECT CASE WHEN spend >= 100000 THEN N'VIP'
              WHEN orders >= 6 THEN N'常連'
              WHEN days_since_first <= 90 THEN N'新規'
              WHEN days_since_last > 180 THEN N'休眠'
              ELSE N'その他' END AS seg
  FROM dbo.cust) AS t GROUP BY seg ORDER BY seg;
-- 重なりの確認
SELECT k, COUNT(*) AS n FROM (
  SELECT IIF(spend >= 100000, 1, 0) + IIF(orders >= 6, 1, 0) + IIF(days_since_first <= 90, 1, 0) + IIF(days_since_last > 180, 1, 0) AS k
  FROM dbo.cust) AS t GROUP BY k ORDER BY k;
