-- 並べ替えたあとの表を、元の表と顧客番号で照合する（DuckDB）
SELECT COUNT(*)                                                   AS n_rows,
       COUNT(*) FILTER (WHERE s.amount <> o.amount)               AS n_moved,      -- 別の顧客の購入額が入った行
       SUM(ABS(s.amount - o.amount))                              AS abs_gap,
       SUM(s.amount) - SUM(o.amount)                              AS total_gap     -- 合計は変わらない
FROM sorted_table AS s
JOIN original AS o USING (customer_id);
