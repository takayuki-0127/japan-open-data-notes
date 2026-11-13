-- 10年分の年間の総損害から、対数正規の 99.5%点を2通りで出す（DuckDB）
-- 表 annual_losses(year, total_loss)、params(z995, t995_df9)：正規分布の99.5%点と、自由度9の t 分布の99.5%点
WITH s AS (
    SELECT COUNT(*)                     AS n,
           AVG(LN(total_loss))          AS mu_hat,
           STDDEV_POP(LN(total_loss))   AS sigma_mle,      -- 最尤推定（n で割る）
           STDDEV_SAMP(LN(total_loss))  AS sigma_s         -- 標本標準偏差（n − 1 で割る）
    FROM annual_losses
)
SELECT s.mu_hat, s.sigma_mle,
       EXP(s.mu_hat + p.z995 * s.sigma_mle)                              AS q_plugin,   -- 推定値をそのまま使う
       EXP(s.mu_hat + p.t995_df9 * s.sigma_s * SQRT(1 + 1.0 / s.n))      AS q_bayes     -- ベイズの予測分布（無情報の事前分布）
FROM s CROSS JOIN params AS p;
