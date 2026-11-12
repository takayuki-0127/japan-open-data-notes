-- 407 外に出す前の確かめ：残す項目の組み合わせが、何人で同じになっているか（k-匿名性）
-- T-SQL の書き方。SQL Server 本体では動かしていません（未検証）。同じ数え方を DuckDB で実行しています（src/a407_k_anonymity.py）
-- customers(顧客ID, 郵便番号7桁, 郵便番号3桁, 生年月日, 性別)

-- 1) 組み合わせごとの人数 k と、1人だけ・5人未満の行の割合
WITH g AS (
  SELECT 郵便番号7桁, 生年月日, 性別, COUNT(*) AS k
  FROM dbo.customers
  GROUP BY 郵便番号7桁, 生年月日, 性別
)
SELECT SUM(CASE WHEN k = 1 THEN k ELSE 0 END) * 100.0 / SUM(k) AS pct_unique,
       SUM(CASE WHEN k < 5 THEN k ELSE 0 END) * 100.0 / SUM(k) AS pct_under5,
       MIN(k) AS min_k
FROM g;

-- 2) 粗くした組み合わせ（郵便番号の上3桁・生まれた年）で同じ確かめ
WITH g AS (
  SELECT 郵便番号3桁, YEAR(生年月日) AS 生年, 性別, COUNT(*) AS k
  FROM dbo.customers
  GROUP BY 郵便番号3桁, YEAR(生年月日), 性別
)
SELECT SUM(CASE WHEN k = 1 THEN k ELSE 0 END) * 100.0 / SUM(k) AS pct_unique,
       SUM(CASE WHEN k < 5 THEN k ELSE 0 END) * 100.0 / SUM(k) AS pct_under5,
       MIN(k) AS min_k
FROM g;

-- 3) 5人未満の組み合わせの行を出さない（外に出す表）
SELECT c.郵便番号3桁, YEAR(c.生年月日) AS 生年, c.性別
FROM dbo.customers AS c
JOIN (SELECT 郵便番号3桁, YEAR(生年月日) AS 生年, 性別
      FROM dbo.customers
      GROUP BY 郵便番号3桁, YEAR(生年月日), 性別
      HAVING COUNT(*) >= 5) AS ok
  ON ok.郵便番号3桁 = c.郵便番号3桁 AND ok.生年 = YEAR(c.生年月日) AND ok.性別 = c.性別;
