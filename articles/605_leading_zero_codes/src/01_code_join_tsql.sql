-- T-SQL：未検証（SQL Server では動かしていない）
-- 先頭の0を戻すには、コードの桁数が決まっている必要がある。桁数の違うコードが混ざるときは、取り込みの時点で文字として読むしかない
-- 6桁に0で埋めて結合（桁数が6桁に決まっているコード体系のときだけ正しい）
SELECT d.line_id, m.code, m.item_name
FROM dbo.lines AS d
LEFT JOIN dbo.master AS m
  ON RIGHT(REPLICATE('0', 6) + m.code, 6) = RIGHT(REPLICATE('0', 6) + d.code_raw, 6);
-- 数として同じになるコードがマスタの中にあるかを先に確かめる
SELECT CAST(code AS INT) AS code_num, COUNT(*) AS n
FROM dbo.master
GROUP BY CAST(code AS INT)
HAVING COUNT(*) > 1;
