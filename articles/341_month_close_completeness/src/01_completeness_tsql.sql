-- 341 締め後 k 営業日の時点で入っている金額（T-SQL 版。SQL Server 本体では動かしていません＝未検証）
-- tx(ym CHAR(7), cat NVARCHAR(20), occ DATE, post DATE, amt DECIMAL(18,0), lag INT)
--   lag = 月の最後の営業日から、計上日までの営業日数（営業日カレンダーの表を別に持って数える）
WITH k AS (SELECT v AS k FROM (VALUES (0),(1),(3),(5),(10),(15),(20)) AS t(v)),
     f AS (SELECT ym, SUM(amt) AS final FROM tx GROUP BY ym)
SELECT t.ym, k.k,
       SUM(CASE WHEN t.lag <= k.k THEN t.amt ELSE 0 END)                       AS cum,
       MAX(f.final)                                                            AS final,
       SUM(CASE WHEN t.lag <= k.k THEN t.amt ELSE 0 END) * 1.0 / MAX(f.final)  AS ratio
FROM tx AS t CROSS JOIN k JOIN f ON f.ym = t.ym
GROUP BY t.ym, k.k
ORDER BY t.ym, k.k;

-- 見込みで補う：過去12か月の「k日目の割合」を区分ごとに出し、今月の入っている分を割り戻して足す
WITH past AS (
  SELECT cat, SUM(CASE WHEN lag <= @k THEN amt ELSE 0 END) * 1.0 / SUM(amt) AS r
  FROM tx WHERE ym >= @from_ym AND ym < @this_ym GROUP BY cat),
cur AS (
  SELECT cat, SUM(CASE WHEN lag <= @k THEN amt ELSE 0 END) AS cum FROM tx WHERE ym = @this_ym GROUP BY cat)
SELECT SUM(cur.cum / past.r) AS estimate FROM cur JOIN past ON past.cat = cur.cat;
