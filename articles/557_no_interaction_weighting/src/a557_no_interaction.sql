-- 層ごとの施策あり・なしの差と、交互作用なしの回帰が暗に使う重み（DuckDB で実行）
-- 交互作用なし（層のダミーだけ）の係数 = Σ 重み × 層ごとの差、重み ∝ 店数 × p × (1 − p)
WITH by_layer AS (
    SELECT layer,
           COUNT(*)                                        AS n_stores,
           AVG(treated::DOUBLE)                            AS p_treated,
           AVG(CASE WHEN treated = 1 THEN sales END)
             - AVG(CASE WHEN treated = 0 THEN sales END)   AS diff
    FROM stores
    GROUP BY layer
), w AS (
    SELECT *, n_stores * p_treated * (1 - p_treated)       AS w_raw
    FROM by_layer
)
SELECT SUM(w_raw * diff) / SUM(w_raw)                      AS dummy_coef,
       SUM(n_stores * diff) / SUM(n_stores)                AS ate_by_store_share,
       SUM(n_stores * p_treated * diff) / SUM(n_stores * p_treated) AS att_by_treated_share
FROM w;
