-- 10件に1件の抜き取りを2通りで行い、区分ごとに10倍して戻す（DuckDB で実行、1回分）
WITH ev_s AS (SELECT cat FROM ev USING SAMPLE 10 PERCENT (bernoulli, 513)),   -- ①イベントごと
     us_s AS (SELECT cat FROM ev WHERE hash(user_id) % 10 = 0),              -- ②利用者ごと（IDのハッシュで選ぶ）
     t AS (SELECT cat, COUNT(*) AS true_n FROM ev GROUP BY cat)
SELECT t.cat, t.true_n,
       COALESCE((SELECT COUNT(*) FROM ev_s WHERE ev_s.cat = t.cat), 0) * 10 AS ev_x10,
       COALESCE((SELECT COUNT(*) FROM us_s WHERE us_s.cat = t.cat), 0) * 10 AS user_x10
FROM t
ORDER BY t.true_n DESC;
