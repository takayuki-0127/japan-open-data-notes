-- 月次レポートの KPI 表（全社・既存店の前年比・前年差）。サンプルマート（架空）。
-- 書き方は SQL Server でも動くように CTE・CAST・CONCAT・SUBSTRING・集計だけにそろえた。実際に流したのは DuckDB（SQL Server そのものでは動かしていない）。
-- 入力：store_month（F247 の mart、店×月）、fact_member_month（会員の月次）
-- 出力：ym ごとに K00〜K10（%：前年比、pt：前年差）
WITH cur AS (            -- 当月の既存店
    SELECT ym, store_id, sales, receipts, items, gross_profit, waste, labor_hours, labor_cost
    FROM store_month WHERE is_existing = 1 AND ym >= '2025-04'
),
prv AS (                 -- 前年同月の同じ店（12か月前の ym をつなぐ）
    SELECT c.ym, p.store_id, p.sales, p.receipts, p.items, p.gross_profit, p.waste, p.labor_hours, p.labor_cost
    FROM cur c
    JOIN store_month p
      ON p.store_id = c.store_id
     AND p.ym = CONCAT(CAST(CAST(SUBSTRING(c.ym, 1, 4) AS INT) - 1 AS VARCHAR(4)), SUBSTRING(c.ym, 5, 3))
),
a AS (SELECT ym, SUM(sales) s, SUM(receipts) r, SUM(items) i, SUM(gross_profit) g, SUM(waste) w, SUM(labor_hours) h, SUM(labor_cost) l FROM cur GROUP BY ym),
b AS (SELECT ym, SUM(sales) s, SUM(receipts) r, SUM(items) i, SUM(gross_profit) g, SUM(waste) w, SUM(labor_hours) h, SUM(labor_cost) l FROM prv GROUP BY ym),
mc AS (SELECT c.ym, SUM(f.member_receipts) mr, SUM(f.active_members) am
       FROM (SELECT DISTINCT ym, store_id FROM cur) c JOIN fact_member_month f ON f.store_id = c.store_id AND f.ym = c.ym GROUP BY c.ym),
mp AS (SELECT c.ym, SUM(f.member_receipts) mr, SUM(f.active_members) am
       FROM (SELECT DISTINCT ym, store_id FROM cur) c JOIN fact_member_month f
         ON f.store_id = c.store_id AND f.ym = CONCAT(CAST(CAST(SUBSTRING(c.ym, 1, 4) AS INT) - 1 AS VARCHAR(4)), SUBSTRING(c.ym, 5, 3))
       GROUP BY c.ym),
allc AS (SELECT ym, SUM(sales) s, SUM(operating_profit) op FROM store_month GROUP BY ym),
allp AS (SELECT CONCAT(CAST(CAST(SUBSTRING(ym, 1, 4) AS INT) + 1 AS VARCHAR(4)), SUBSTRING(ym, 5, 3)) AS ym, SUM(sales) s, SUM(operating_profit) op
         FROM store_month GROUP BY ym)
SELECT a.ym,
       (ac.op / ap.op - 1) * 100                                   AS K00,  -- 営業利益（全店）
       (ac.s / ap.s - 1) * 100                                     AS K10,  -- 売上（全店）
       (a.s / b.s - 1) * 100                                       AS K01,  -- 既存店売上
       (a.r / b.r - 1) * 100                                       AS K02,  -- 客数
       ((a.i / a.r) / (b.i / b.r) - 1) * 100                       AS K03,  -- 買上点数（1回）
       ((a.s / a.i) / (b.s / b.i) - 1) * 100                       AS K04,  -- 一品単価
       ((mc.mr / mc.am) / (mp.mr / mp.am) - 1) * 100               AS K05,  -- 来店頻度（会員）
       (a.g / a.s - b.g / b.s) * 100                               AS K06,  -- 粗利率（廃棄後）
       (a.w / a.s - b.w / b.s) * 100                               AS K07,  -- 廃棄率
       ((a.g / a.h) / (b.g / b.h) - 1) * 100                       AS K08,  -- 人時粗利
       (a.l / a.s - b.l / b.s) * 100                               AS K09   -- 人件費率
FROM a
JOIN b    ON b.ym = a.ym
JOIN mc   ON mc.ym = a.ym
JOIN mp   ON mp.ym = a.ym
JOIN allc ac ON ac.ym = a.ym
JOIN allp ap ON ap.ym = a.ym
ORDER BY a.ym;
