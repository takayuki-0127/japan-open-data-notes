-- 割引率の平均を3通りで出す（DuckDB）
SELECT AVG(discount_rate)                                                    AS naive_mean,     -- そのまま平均
       AVG(CASE WHEN discount_rate > 1 THEN discount_rate / 100
                ELSE discount_rate END)                                      AS rule_mean,      -- 1より大きい値だけ100で割る
       AVG(CASE WHEN source = 'manual' THEN discount_rate / 100
                ELSE discount_rate END)                                      AS by_source_mean  -- 入力元で直す
FROM discounts;
