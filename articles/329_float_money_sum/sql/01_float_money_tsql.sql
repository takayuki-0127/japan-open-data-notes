-- 329 金額の型（T-SQL 版）。SQL Server 本体では動かしていません（未検証）。DuckDB と NumPy での計算は src/a329_float_money.py。
CREATE TABLE m (id INT PRIMARY KEY, store INT,
                amt_decimal DECIMAL(18,2),   -- 10進の型
                amt_double  FLOAT(53),       -- 8バイトの浮動小数
                amt_real    REAL);           -- 4バイトの浮動小数

-- 合計を型ごとに比べる
SELECT SUM(amt_decimal) AS s_decimal, SUM(amt_double) AS s_double, SUM(amt_real) AS s_real FROM m;

-- 等号の判定：浮動小数どうしは = で比べず、10進の型に直すか、丸めてから比べる
SELECT CASE WHEN CAST(0.1 AS FLOAT) + CAST(0.2 AS FLOAT) = CAST(0.3 AS FLOAT) THEN 'equal' ELSE 'not equal' END AS float_eq,
       CASE WHEN CAST(0.1 AS DECIMAL(9,2)) + CAST(0.2 AS DECIMAL(9,2)) = CAST(0.3 AS DECIMAL(9,2)) THEN 'equal' ELSE 'not equal' END AS decimal_eq;

-- 店ごとの合計と正しい合計の突き合わせ（浮動小数の列は、丸めてから比べる）
SELECT store, SUM(amt_double) AS s, ROUND(SUM(amt_double), 2) AS s_round, SUM(amt_decimal) AS s_true FROM m GROUP BY store;
