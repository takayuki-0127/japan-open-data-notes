-- F243 支出の変化を「値段」と「量」に分ける（シャープレイ＝中点の分け方）。SQL Server（T-SQL）で動く書き方。
-- テーブル kakei_items(code INT, name NVARCHAR, grp NVARCHAR, unit NVARCHAR, year INT, price FLOAT, q FLOAT)
WITH y0 AS (SELECT code, name, grp, unit, price AS p0, q AS q0 FROM kakei_items WHERE year = 2019),
     y1 AS (SELECT code, price AS p1, q AS q1 FROM kakei_items WHERE year = 2024),
     j AS (SELECT y0.code, y0.name, y0.grp, y0.unit, p0, q0, p1, q1 FROM y0 INNER JOIN y1 ON y0.code = y1.code),
     d AS (SELECT grp, p0 * q0 AS e0, p1 * q1 AS e1,
                  (p1 - p0) * (q0 + q1) / 2.0 AS price_eff,
                  (q1 - q0) * (p0 + p1) / 2.0 AS qty_eff
           FROM j)
SELECT grp, SUM(e0) AS e0, SUM(e1) AS e1, SUM(e1) - SUM(e0) AS chg,
       SUM(price_eff) AS price_eff, SUM(qty_eff) AS qty_eff
FROM d GROUP BY grp;

-- 100g あたり平均価格の変化を「品目の値段（率）」と「品目の構成（ミックス）」に分ける
WITH y0 AS (SELECT code, grp, price AS p0, q AS q0 FROM kakei_items WHERE year = 2019 AND unit = N'1g(100g)'),
     y1 AS (SELECT code, price AS p1, q AS q1 FROM kakei_items WHERE year = 2024 AND unit = N'1g(100g)'),
     j AS (SELECT y0.code, grp, p0, q0, p1, q1 FROM y0 INNER JOIN y1 ON y0.code = y1.code),
     s AS (SELECT code, grp, p0, p1,
                  q0 / SUM(q0) OVER (PARTITION BY grp) AS s0,
                  q1 / SUM(q1) OVER (PARTITION BY grp) AS s1
           FROM j)
SELECT grp,
       SUM(s0 * p0) AS avg_p0, SUM(s1 * p1) AS avg_p1,
       SUM((s0 + s1) / 2.0 * (p1 - p0)) AS rate_eff,
       SUM((s1 - s0) * (p0 + p1) / 2.0) AS mix_eff
FROM s GROUP BY grp;
