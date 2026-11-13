-- 取り出した時刻の違う2つの表をつなぐ（DuckDB 版）
-- orders_snap(order_id, customer_id, ordered_at, amount)：その日の注文
-- customers_snap(customer_id, region)：顧客マスタの写し（取り出した時刻が注文と違う）
-- J1 内部結合：マスタにない顧客の注文は落ちる
SELECT COUNT(*) AS n, SUM(amount) AS amt FROM orders_snap o JOIN customers_snap c USING (customer_id);
-- J2 外部結合：マスタにない顧客は地域が空（「不明」）で残る
SELECT COUNT(*) AS n, SUM(amount) AS amt, COUNT(*) FILTER (WHERE c.region IS NULL) AS n_unknown
FROM orders_snap o LEFT JOIN customers_snap c USING (customer_id);
