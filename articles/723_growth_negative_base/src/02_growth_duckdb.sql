-- DuckDB で実行（1スレッド）。前年がマイナスや0に近い店を含む伸び率の3通り
SELECT store_id, profit_prev, profit_cur,
       profit_cur - profit_prev                                         AS diff,
       (profit_cur - profit_prev) / profit_prev                         AS growth_plain,   -- ふつうの式
       (profit_cur - profit_prev) / ABS(profit_prev)                    AS growth_absbase, -- 分母を絶対値
       CASE WHEN profit_prev <= 0 THEN NULL
            ELSE (profit_cur - profit_prev) / profit_prev END           AS growth_or_null, -- 前年がマイナスなら出さない
       SIGN(profit_cur - profit_prev) <> SIGN((profit_cur - profit_prev) / profit_prev) AS direction_flipped
FROM profits
ORDER BY store_id;
