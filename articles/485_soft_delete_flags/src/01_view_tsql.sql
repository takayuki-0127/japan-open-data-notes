-- 485 論理削除と履歴の期間を、ビューで隠す（T-SQL 版。SQL Server では動かしていない：未検証）
-- orders(order_id, customer_id, order_date, amount, is_deleted bit)
-- customers(customer_id, version, valid_from, valid_to, segment, is_deleted bit)   -- valid_to は含まない
CREATE VIEW dbo.v_orders AS
SELECT o.order_id, o.customer_id, o.order_date, o.amount, c.segment
FROM dbo.orders AS o
JOIN dbo.customers AS c
  ON  c.customer_id = o.customer_id
  AND o.order_date >= c.valid_from
  AND o.order_date <  c.valid_to          -- 注文日に有効だった版だけとつなぐ
WHERE o.is_deleted = 0
  AND c.is_deleted = 0;
GO
-- 集計はこのビューから：
-- SELECT COUNT(*), SUM(amount), COUNT(DISTINCT customer_id) FROM dbo.v_orders;
-- 見落としの例（どれも黙って多く数える）
--   1) WHERE o.is_deleted = 0 を書き忘れる      → キャンセルした注文が入る
--   2) 顧客側の c.is_deleted = 0 を書き忘れる   → テスト用などの顧客の注文が入る
--   3) 期間の条件を書かずに customer_id だけでつなぐ → 履歴の行の数だけ注文が増える
