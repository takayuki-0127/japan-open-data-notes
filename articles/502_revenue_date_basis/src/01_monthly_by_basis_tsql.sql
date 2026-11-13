-- T-SQL 版（SQL Server では動かしていない：未検証）
SELECT o.kind, v.basis, DATEFROMPARTS(YEAR(v.d), MONTH(v.d), 1) AS month_start, SUM(o.amount) AS amount
FROM dbo.orders AS o
CROSS APPLY (VALUES (N'受注日', o.order_date), (N'出荷日', o.ship_date), (N'検収日', o.accept_date)) AS v(basis, d)
WHERE v.d >= '2023-01-01' AND v.d < '2026-01-01'
GROUP BY o.kind, v.basis, DATEFROMPARTS(YEAR(v.d), MONTH(v.d), 1)
ORDER BY o.kind, v.basis, month_start;

-- 前年同月比：LAG で12か月前を取る（月が抜けていないことが前提。抜けがあると 232 のようにずれる）
WITH m AS (
  SELECT kind, basis, month_start, amount,
         LAG(amount, 12) OVER (PARTITION BY kind, basis ORDER BY month_start) AS amount_12m_ago
  FROM dbo.monthly_by_basis
)
SELECT *, CAST(amount AS float) / NULLIF(amount_12m_ago, 0) - 1 AS yoy FROM m;
