-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH by_layer AS (
    SELECT layer,
           COUNT(*)                                                    AS n_stores,
           AVG(CAST(treated AS float))                                 AS p_treated,
           AVG(CASE WHEN treated = 1 THEN CAST(sales AS float) END)
             - AVG(CASE WHEN treated = 0 THEN CAST(sales AS float) END) AS diff
    FROM dbo.stores
    GROUP BY layer
), w AS (
    SELECT *, n_stores * p_treated * (1 - p_treated) AS w_raw
    FROM by_layer
)
SELECT SUM(w_raw * diff) / SUM(w_raw)                                   AS dummy_coef,
       SUM(n_stores * diff) / SUM(CAST(n_stores AS float))              AS ate_by_store_share,
       SUM(n_stores * p_treated * diff) / SUM(n_stores * p_treated)     AS att_by_treated_share
FROM w;
