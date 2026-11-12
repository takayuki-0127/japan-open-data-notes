-- NULL の扱いを書いた14本（Q11〜Q14 は素朴な書き方と同じ）。T-SQL の書き方。DuckDB で実行して確かめた（SQL Server 本体では未検証）
-- name: Q01_注文1件あたりの割引額の平均
SELECT AVG(CAST(COALESCE(o.discount, 0) AS FLOAT)) AS v FROM dbo.orders AS o;

-- name: Q02_値引き後の売上の合計
SELECT SUM(o.amount - COALESCE(o.discount, 0)) AS v FROM dbo.orders AS o;

-- name: Q03_注文の件数（顧客番号を数える）
SELECT COUNT(*) AS v FROM dbo.orders AS o;

-- name: Q04_一度も注文していない顧客の数（NOT IN）
SELECT COUNT(*) AS v FROM dbo.customers AS c
WHERE NOT EXISTS (SELECT 1 FROM dbo.orders AS o WHERE o.customer_id = c.customer_id);

-- name: Q05_関東以外の顧客の数（<>）
SELECT COUNT(*) AS v FROM dbo.customers AS c WHERE c.region <> N'関東' OR c.region IS NULL;

-- name: Q06_割引が100円を超えない注文の数（NOT）
SELECT COUNT(*) AS v FROM dbo.orders AS o WHERE COALESCE(o.discount, 0) <= 100;

-- name: Q07_顧客1人あたりの平均年齢（合計÷人数）
SELECT CAST(SUM(2026 - c.birth_year) AS FLOAT) / COUNT(c.birth_year) AS v FROM dbo.customers AS c;

-- name: Q08_宛名が作れた顧客の数（文字をつなぐ）
SELECT COUNT(CONCAT(c.last_name, N' ', c.first_name)) AS v FROM dbo.customers AS c;

-- name: Q09_地域ごとの売上を地域ごとの目標とつないだ合計
SELECT SUM(s.sales) AS v
FROM (SELECT COALESCE(c.region, N'不明') AS region, SUM(o.amount) AS sales
      FROM dbo.orders AS o LEFT JOIN dbo.customers AS c ON c.customer_id = o.customer_id
      GROUP BY COALESCE(c.region, N'不明')) AS s
LEFT JOIN dbo.region_targets AS t ON t.region = s.region;

-- name: Q10_店ごとの売上から返品を引いた合計
SELECT SUM(s.sales - COALESCE(r.returned, 0)) AS v
FROM (SELECT store_code, SUM(amount) AS sales FROM dbo.orders GROUP BY store_code) AS s
LEFT JOIN (SELECT store_code, SUM(amount) AS returned FROM dbo.returns GROUP BY store_code) AS r
       ON r.store_code = s.store_code;

-- ここから下の4本は、NULL を気にしなくても意図どおりになる書き方（比べるために入れた）
-- name: Q11_地域ごとの顧客数を足し直した合計（GROUP BY）
SELECT SUM(g.n) AS v FROM (SELECT c.region, COUNT(*) AS n FROM dbo.customers AS c GROUP BY c.region) AS g;

-- name: Q12_割引があった注文の数（>）
SELECT COUNT(*) AS v FROM dbo.orders AS o WHERE o.discount > 0;

-- name: Q13_関西と中部の顧客の数（IN）
SELECT COUNT(*) AS v FROM dbo.customers AS c WHERE c.region IN (N'関西', N'中部');

-- name: Q14_いちばん若い顧客の生年（MAX）
SELECT MAX(c.birth_year) AS v FROM dbo.customers AS c;
