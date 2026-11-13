-- もとの件数どうしと、来店客数で割った比率どうしの相関（DuckDB で実行）
SELECT corr(inquiries, returns)                                         AS r_raw,
       corr(inquiries * 1.0 / visitors, returns * 1.0 / visitors)       AS r_ratio,
       COUNT(*)                                                         AS n_stores
FROM stores;
