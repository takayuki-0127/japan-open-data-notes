-- F249 DAX メジャーの期待値を SQL で出す（DuckDB 1.5 で実行。{P} は powerbi/data のフォルダ）
-- 会社・数字は架空（サンプルマート（架空）、合成データ）。
-- 既存店の前年比は、月ごとに「その月の既存店」と「同じ店の前年同月」を足し、期間（月・FY）で合計してから割る（DAX の SUMX(VALUES(month_start)) と同じ）。
WITH
sd AS (
  SELECT store_id, strftime(biz_date, '%Y-%m') AS ym,
         SUM(sales) AS sales, SUM(receipts) AS receipts, SUM(items) AS items,
         SUM(gross_profit_before_waste) AS gpb, SUM(waste) AS waste, SUM(gross_profit) AS gp,
         SUM(labor_hours) AS lh, SUM(labor_cost) AS lc
  FROM read_csv_auto('{P}/fact_store_day.csv.gz') GROUP BY 1, 2),
fm AS (SELECT store_id, strftime(month_start, '%Y-%m') AS ym, other_cost, is_existing FROM read_csv_auto('{P}/fact_store_month.csv')),
mem AS (SELECT store_id, strftime(month_start, '%Y-%m') AS ym, active_members, member_receipts FROM read_csv_auto('{P}/fact_member_month.csv')),
st AS (SELECT store_id, area FROM read_csv_auto('{P}/dim_store.csv')),
sm AS (
  SELECT sd.*, fm.other_cost AS oc, fm.is_existing, mem.active_members AS am, mem.member_receipts AS mr,
         strftime(CAST(sd.ym || '-01' AS DATE) - INTERVAL 12 MONTH, '%Y-%m') AS ym_ly
  FROM sd JOIN fm USING (store_id, ym) LEFT JOIN mem USING (store_id, ym)),
w AS (SELECT strftime(date, '%Y-%m') AS ym, SUM(day_weight) AS w FROM read_csv_auto('{P}/dim_date.csv') GROUP BY 1),
per AS (
  SELECT ym, ym AS 期間 FROM w WHERE ym >= '2023-04'
  UNION ALL
  SELECT ym, 'FY' || CAST(CASE WHEN CAST(substr(ym, 6, 2) AS INTEGER) >= 4 THEN CAST(substr(ym, 1, 4) AS INTEGER)
                               ELSE CAST(substr(ym, 1, 4) AS INTEGER) - 1 END AS VARCHAR)
  FROM w WHERE ym >= '2023-04'),
scope AS (SELECT store_id, '全社' AS 範囲 FROM st UNION ALL SELECT store_id, area FROM st),
allst AS (
  SELECT sc.範囲, p.期間, SUM(c.sales) AS sales, SUM(c.gp) AS gp, SUM(c.gp - c.lc - c.oc) AS op
  FROM sm c JOIN per p ON p.ym = c.ym JOIN scope sc ON sc.store_id = c.store_id GROUP BY 1, 2),
pair AS (   -- 既存店の当月（c）と、同じ店の前年同月（l）
  SELECT sc.範囲, p.期間,
         SUM(c.sales) AS s1, SUM(l.sales) AS s0, SUM(c.receipts) AS r1, SUM(l.receipts) AS r0,
         SUM(c.items) AS i1, SUM(l.items) AS i0, SUM(c.gpb) AS b1, SUM(l.gpb) AS b0,
         SUM(c.waste) AS w1, SUM(l.waste) AS w0, SUM(c.gp) AS g1, SUM(l.gp) AS g0,
         SUM(c.lh) AS h1, SUM(l.lh) AS h0, SUM(c.lc) AS c1, SUM(l.lc) AS c0, SUM(c.oc) AS o1, SUM(l.oc) AS o0,
         SUM(c.am) AS a1, SUM(l.am) AS a0, SUM(c.mr) AS m1, SUM(l.mr) AS m0
  FROM sm c
  JOIN sm l ON l.store_id = c.store_id AND l.ym = c.ym_ly
  JOIN per p ON p.ym = c.ym
  JOIN scope sc ON sc.store_id = c.store_id
  WHERE c.is_existing = 1
  GROUP BY 1, 2),
cal AS (
  SELECT p.期間, SUM(w1.w) / SUM(w0.w) - 1 AS eff
  FROM per p JOIN w w1 ON w1.ym = p.ym
  JOIN w w0 ON w0.ym = strftime(CAST(p.ym || '-01' AS DATE) - INTERVAL 12 MONTH, '%Y-%m')
  GROUP BY 1)
SELECT a.範囲, a.期間,
  a.sales AS "売上", a.gp AS "粗利_廃棄後", a.op AS "営業利益",
  q.s1 AS "既存店売上", q.s0 AS "既存店売上_前年", q.s1 / q.s0 - 1 AS "既存店売上_前年比",
  k.eff AS "曜日の並びの効果", (q.s1 / q.s0) / (1 + k.eff) - 1 AS "既存店売上_前年比_曜日補正",
  q.r1 / q.r0 - 1 AS "既存店客数_前年比",
  q.i1 / q.r1 AS "既存店買上点数", (q.i1 / q.r1) / (q.i0 / q.r0) - 1 AS "既存店買上点数_前年比",
  q.s1 / q.i1 AS "既存店一品単価", (q.s1 / q.i1) / (q.s0 / q.i0) - 1 AS "既存店一品単価_前年比",
  q.g1 / q.s1 AS "既存店粗利率_廃棄後", q.g1 / q.s1 - q.g0 / q.s0 AS "既存店粗利率_廃棄後_前年差",
  q.w1 / q.s1 AS "既存店廃棄率", q.w1 / q.s1 - q.w0 / q.s0 AS "既存店廃棄率_前年差",
  q.g1 / q.h1 AS "既存店人時粗利", (q.g1 / q.h1) / (q.g0 / q.h0) - 1 AS "既存店人時粗利_前年比",
  q.c1 / q.s1 AS "既存店人件費率", q.c1 / q.s1 - q.c0 / q.s0 AS "既存店人件費率_前年差",
  q.g1 - q.c1 - q.o1 AS "既存店営業利益", q.g0 - q.c0 - q.o0 AS "既存店営業利益_前年",
  (q.g1 - q.c1 - q.o1) / (q.g0 - q.c0 - q.o0) - 1 AS "既存店営業利益_前年比",
  q.m1 / q.a1 AS "来店頻度_会員", (q.m1 / q.a1) / (q.m0 / q.a0) - 1 AS "来店頻度_会員_前年比",
  (q.s1 - q.s0) * (q.b0 / q.s0) AS "橋_売上の伸び",
  q.s1 * (q.b1 / q.s1 - q.b0 / q.s0) AS "橋_廃棄前の粗利率",
  -(q.w1 - q.w0) AS "橋_廃棄", -(q.c1 - q.c0) AS "橋_人件費", -(q.o1 - q.o0) AS "橋_その他経費"
FROM allst a
JOIN pair q ON q.範囲 = a.範囲 AND q.期間 = a.期間
JOIN cal k ON k.期間 = a.期間
ORDER BY a.範囲, a.期間;
