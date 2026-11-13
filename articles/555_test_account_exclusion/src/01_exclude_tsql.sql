-- テスト用アカウントを外して、利用者数・売上・購入した人の割合を出す（T-SQL 版。SQL Server では動かしていない：未検証）
WITH test_users AS (
  SELECT user_id FROM dbo.users
  WHERE email LIKE N'%@corp.example' OR user_id BETWEEN 900000 AND 900999 OR is_test_flag = 1),
active AS (SELECT DISTINCT s.user_id FROM dbo.sessions AS s WHERE NOT EXISTS (SELECT 1 FROM test_users AS t WHERE t.user_id = s.user_id)),
buy AS (SELECT o.user_id, SUM(o.amount) AS amount FROM dbo.orders AS o
        WHERE NOT EXISTS (SELECT 1 FROM test_users AS t WHERE t.user_id = o.user_id) GROUP BY o.user_id)
SELECT (SELECT COUNT(*) FROM active) AS active_users,
       (SELECT COUNT(*) FROM buy) AS buyers,
       (SELECT SUM(amount) FROM buy) AS sales,
       100.0 * (SELECT COUNT(*) FROM buy) / NULLIF((SELECT COUNT(*) FROM active), 0) AS conversion_pct;
