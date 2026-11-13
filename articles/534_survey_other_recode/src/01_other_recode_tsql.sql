-- 「その他」の自由記述をキーワードで振り直し、構成比を前後で比べる（T-SQL 版、SQL Server では未検証）
-- dbo.survey(resp_id, choice NVARCHAR, other_text NVARCHAR)
WITH r AS (
  SELECT resp_id, choice,
         CASE WHEN choice <> N'その他' THEN choice
              WHEN other_text LIKE N'%安%' OR other_text LIKE N'%値段%' OR other_text LIKE N'%価格%' OR other_text LIKE N'%セール%' THEN N'価格'
              WHEN other_text LIKE N'%品質%' OR other_text LIKE N'%丈夫%' OR other_text LIKE N'%長持ち%' THEN N'品質'
              WHEN other_text LIKE N'%デザイン%' OR other_text LIKE N'%色%' OR other_text LIKE N'%見た目%' THEN N'デザイン'
              WHEN other_text LIKE N'%口コミ%' OR other_text LIKE N'%レビュー%' OR other_text LIKE N'%評判%' THEN N'口コミ'
              WHEN other_text LIKE N'%店員%' OR other_text LIKE N'%接客%' THEN N'店員の対応'
              ELSE N'その他' END AS kw_label
  FROM dbo.survey),
b AS (SELECT choice AS opt, COUNT(*) AS n_before FROM r GROUP BY choice),
a AS (SELECT kw_label AS opt, COUNT(*) AS n_after FROM r GROUP BY kw_label)
SELECT COALESCE(b.opt, a.opt) AS opt,
       100.0 * COALESCE(n_before, 0) / SUM(COALESCE(n_before, 0)) OVER () AS pct_before,
       100.0 * COALESCE(n_after, 0)  / SUM(COALESCE(n_after, 0))  OVER () AS pct_after
FROM b FULL OUTER JOIN a ON a.opt = b.opt
ORDER BY pct_after DESC;
