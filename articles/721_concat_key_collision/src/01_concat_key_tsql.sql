-- T-SQL：未検証（SQL Server では動かしていない）
-- 区切りなしでつなぐと '1' + '23' と '12' + '3' が同じ '123' になる
SELECT s.store_cd + s.item_cd AS key_nosep, COUNT(*) AS pairs
FROM (SELECT DISTINCT store_cd, item_cd FROM sales) s
GROUP BY s.store_cd + s.item_cd
HAVING COUNT(*) > 1;

-- 区切り文字を入れる（コードに '-' が出てこないことを先に確かめる）
SELECT CONCAT(s.store_cd, '-', s.item_cd) AS key_sep, SUM(s.amount) AS amount
FROM sales s
GROUP BY CONCAT(s.store_cd, '-', s.item_cd);

-- いちばん安全なのは、2列のまま結合すること
SELECT s.store_cd, s.item_cd, s.amount, t.target
FROM sales s
JOIN targets t ON s.store_cd = t.store_cd AND s.item_cd = t.item_cd;
