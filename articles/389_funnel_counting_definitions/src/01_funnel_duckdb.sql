-- 389 人で数える通過率（DuckDB で実行）。access_log(user_id, session_id, ts, step_name)
WITH any_order AS (                       -- 順番を問わない：期間のうちに、その段の記録が1つでもある人
  SELECT COUNT(DISTINCT CASE WHEN step_name = '商品ページ'   THEN user_id END) AS n1,
         COUNT(DISTINCT CASE WHEN step_name = 'カート'       THEN user_id END) AS n2,
         COUNT(DISTINCT CASE WHEN step_name = '入力フォーム' THEN user_id END) AS n3,
         COUNT(DISTINCT CASE WHEN step_name = '申込み完了'   THEN user_id END) AS n4
  FROM access_log
),
s1 AS (SELECT user_id, MIN(ts) AS t1 FROM access_log WHERE step_name = '商品ページ' GROUP BY user_id),
s2 AS (SELECT a.user_id, MIN(a.ts) AS t2 FROM access_log AS a JOIN s1 ON s1.user_id = a.user_id
       WHERE a.step_name = 'カート'       AND a.ts > s1.t1 GROUP BY a.user_id),
s3 AS (SELECT a.user_id, MIN(a.ts) AS t3 FROM access_log AS a JOIN s2 ON s2.user_id = a.user_id
       WHERE a.step_name = '入力フォーム' AND a.ts > s2.t2 GROUP BY a.user_id),
s4 AS (SELECT a.user_id, MIN(a.ts) AS t4 FROM access_log AS a JOIN s3 ON s3.user_id = a.user_id
       WHERE a.step_name = '申込み完了'   AND a.ts > s3.t3 GROUP BY a.user_id)
SELECT '順番を問わない' AS 数え方, n1, n2, n3, n4 FROM any_order
UNION ALL                                 -- 順番を問う：前の段より後の時刻に、次の段の記録がある人
SELECT '順番を問う', (SELECT COUNT(*) FROM s1), (SELECT COUNT(*) FROM s2),
       (SELECT COUNT(*) FROM s3), (SELECT COUNT(*) FROM s4);
