-- T-SQL：未検証
SELECT AVG(discount_rate)                                                    AS naive_mean,
       AVG(CASE WHEN discount_rate > 1 THEN discount_rate / 100
                ELSE discount_rate END)                                      AS rule_mean,
       AVG(CASE WHEN source = 'manual' THEN discount_rate / 100
                ELSE discount_rate END)                                      AS by_source_mean
FROM dbo.discounts;
