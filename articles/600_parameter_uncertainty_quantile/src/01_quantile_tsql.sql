-- 10年分の年間の総損害から、対数正規の 99.5%点を2通りで出す（T-SQL、未検証：SQL Server では動かしていない）
-- 表 dbo.annual_losses(year, total_loss)。@z995 = 2.5758293035489, @t995_df9 = 3.2498355415921（Python で計算して渡す）
DECLARE @z995 float = 2.5758293035489, @t995_df9 float = 3.2498355415921;
WITH s AS (
    SELECT COUNT(*)                    AS n,
           AVG(LOG(total_loss))        AS mu_hat,           -- T-SQL の LOG は自然対数
           STDEVP(LOG(total_loss))     AS sigma_mle,
           STDEV(LOG(total_loss))      AS sigma_s
    FROM dbo.annual_losses
)
SELECT mu_hat, sigma_mle,
       EXP(mu_hat + @z995 * sigma_mle)                             AS q_plugin,
       EXP(mu_hat + @t995_df9 * sigma_s * SQRT(1 + 1.0 / n))       AS q_bayes
FROM s;
