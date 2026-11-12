-- 461 区分ごとのユニーク人数（T-SQL 版）
-- ※ SQL Server 本体では動かしていません（未検証）。同じ中身を DuckDB で実行して確かめています（a461_distinct.py）。
-- 表：dbo.purchase_log(cust_id INT, day INT, store INT, dept INT, amount INT)

-- 本当の人数（月に1回以上買った人）
SELECT COUNT(DISTINCT cust_id) AS n_customers FROM dbo.purchase_log;

-- やってはいけない足し算：店ごとのユニーク人数を足す
SELECT SUM(n) AS summed
FROM (SELECT store, COUNT(DISTINCT cust_id) AS n FROM dbo.purchase_log GROUP BY store) AS s;

-- 日ごと・部門ごとも同じ形
SELECT SUM(n) FROM (SELECT [day], COUNT(DISTINCT cust_id) AS n FROM dbo.purchase_log GROUP BY [day]) AS d;
SELECT SUM(n) FROM (SELECT dept, COUNT(DISTINCT cust_id) AS n FROM dbo.purchase_log GROUP BY dept) AS p;

-- 先に「人×店」の表を作ってから数える（店ごとの人数も、全体の人数も、この表から出せる）
WITH cust_store AS (SELECT DISTINCT cust_id, store FROM dbo.purchase_log)
SELECT store, COUNT(*) AS n FROM cust_store GROUP BY store;

WITH cust_store AS (SELECT DISTINCT cust_id, store FROM dbo.purchase_log)
SELECT COUNT(DISTINCT cust_id) AS n_customers FROM cust_store;

-- 店ごとと全体を1回で出す（全体の行は、足し算ではなく数え直し）
SELECT store, COUNT(DISTINCT cust_id) AS n
FROM dbo.purchase_log
GROUP BY GROUPING SETS ((store), ());

-- 照合：金額と行数は足して一致する。人数は一致しない
SELECT (SELECT SUM(a) FROM (SELECT store, SUM(amount) AS a FROM dbo.purchase_log GROUP BY store) AS s)
     - (SELECT SUM(amount) FROM dbo.purchase_log) AS amount_diff;
