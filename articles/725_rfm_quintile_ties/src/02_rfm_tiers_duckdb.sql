-- DuckDB で実行（1スレッド）。購入回数で5段に分ける3通り
-- ntile_id   : NTILE(5)、同じ回数の人は顧客番号の順で分かれる
-- ntile_rand : NTILE(5)、同じ回数の人は別の順（ここでは最終購入日の新しい順）で分かれる
-- rank_tier  : 同じ回数の人は同じ段（RANK を人数で割って段を決める）
SELECT customer_id, freq,
       NTILE(5) OVER (ORDER BY freq DESC, customer_id)               AS ntile_id,
       NTILE(5) OVER (ORDER BY freq DESC, last_date DESC, customer_id) AS ntile_recent,
       CAST(FLOOR((RANK() OVER (ORDER BY freq DESC) - 1) * 5.0 / COUNT(*) OVER ()) AS INTEGER) + 1 AS rank_tier
FROM customers
ORDER BY customer_id;
