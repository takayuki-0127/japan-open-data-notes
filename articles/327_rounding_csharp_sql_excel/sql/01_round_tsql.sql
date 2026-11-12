-- 327 丸め方の違い（T-SQL・C#・Excel の書き方の対応）。どれも本体では動かしていません（未検証）。
-- Python での再現は src/a327_rounding.py にあります。

-- SQL Server：DECIMAL の ROUND は「0から遠いほうへ」の四捨五入。第3引数を 0 以外にすると切り捨て
SELECT ROUND(CAST(2.5 AS DECIMAL(9,2)), 0)     AS half_away,   -- 3
       ROUND(CAST(-2.5 AS DECIMAL(9,2)), 0)    AS half_away_n, -- -3
       ROUND(CAST(2.5 AS DECIMAL(9,2)), 0, 1)  AS truncated;   -- 2

-- C#（参考）
--   Math.Round(2.5m)                                  → 2   （既定は偶数丸め MidpointRounding.ToEven）
--   Math.Round(2.5m, MidpointRounding.AwayFromZero)   → 3   （SQL Server の ROUND と同じ向き）
--   Math.Truncate(2.5m)                               → 2
-- Excel（参考）
--   =ROUND(2.5,0) → 3、=ROUND(-2.5,0) → -3、=ROUNDDOWN(2.5,0) → 2

-- 偶数丸めを T-SQL でそろえたいときの一例（正の値・小数第0位）
SELECT CASE WHEN x - FLOOR(x) = 0.5 AND FLOOR(x) % 2 = 0 THEN FLOOR(x) ELSE ROUND(x, 0) END AS half_even
FROM (VALUES (CAST(2.5 AS DECIMAL(9,2))), (3.5), (2.4), (2.6)) v(x);
