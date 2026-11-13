-- ステータスの表記ゆれをそろえてから数える（T-SQL、未検証）
WITH t AS (
  SELECT task_id, status AS raw,
         LTRIM(RTRIM(REPLACE(status, N'　', N' '))) AS cleaned
  FROM dbo.tasks
)
SELECT
  COUNT(DISTINCT raw)                                                      AS groups_raw,   -- 照合順序によっては、全角・半角や末尾の空白を同じとみなして数が変わる
  COUNT(DISTINCT cleaned)                                                  AS groups_cleaned,
  COUNT(DISTINCT COALESCE(m.canonical, t.cleaned))                         AS groups_mapped,
  AVG(CASE WHEN raw = N'完了' THEN 1.0 ELSE 0.0 END)                       AS done_rate_raw,
  AVG(CASE WHEN cleaned = N'完了' THEN 1.0 ELSE 0.0 END)                   AS done_rate_cleaned,
  AVG(CASE WHEN COALESCE(m.canonical, t.cleaned) = N'完了' THEN 1.0 ELSE 0.0 END) AS done_rate_mapped,
  SUM(CASE WHEN m.canonical IS NULL THEN 1 ELSE 0 END)                     AS unmapped_rows
FROM t
LEFT JOIN dbo.status_map AS m ON m.variant = t.cleaned;
-- 注意：SQL Server の既定の照合順序では、'完了' = '完了 '（末尾の半角空白）が等しいと判定される。
-- DuckDB や Python とは結果が変わりうる
