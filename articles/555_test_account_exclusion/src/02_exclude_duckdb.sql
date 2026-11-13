-- テスト用アカウントを外して、利用者数・売上・購入した人の割合を出す（DuckDB 版）
-- users(user_id, email, is_test_flag)、sessions(session_id, user_id, started_at)、orders(order_id, user_id, amount)
-- 条件：メール末尾・ID の範囲・フラグのどれかに当たれば外す（3条件のどれか）
WITH test_users AS (
  SELECT user_id FROM users
  WHERE email LIKE '%@corp.example'          -- 社内のメールの末尾（架空）
     OR user_id BETWEEN 900000 AND 900999    -- テスト用に取ってある ID の範囲（架空）
     OR is_test_flag = 1),
active AS (SELECT DISTINCT user_id FROM sessions WHERE user_id NOT IN (SELECT user_id FROM test_users)),
buy AS (SELECT user_id, SUM(amount) AS amount FROM orders WHERE user_id NOT IN (SELECT user_id FROM test_users) GROUP BY user_id)
SELECT (SELECT COUNT(*) FROM active)                AS active_users,
       (SELECT COUNT(*) FROM buy)                   AS buyers,
       (SELECT SUM(amount) FROM buy)                AS sales,
       100.0 * (SELECT COUNT(*) FROM buy) / (SELECT COUNT(*) FROM active) AS conversion_pct;
