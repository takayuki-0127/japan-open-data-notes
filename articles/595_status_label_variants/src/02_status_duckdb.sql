-- ステータスの表記ゆれをそろえてから数える（DuckDB）
-- ① そのまま ② 前後の空白（半角・全角）を除く ③ 対応表（status_map）で正規の名前にそろえる
WITH t AS (
  SELECT
    task_id, status AS raw,
    trim(replace(status, '　', ' ')) AS cleaned      -- 全角空白を半角にしてから前後を除く
  FROM tasks
)
SELECT
  COUNT(DISTINCT raw)                                                 AS groups_raw,
  COUNT(DISTINCT cleaned)                                             AS groups_cleaned,
  COUNT(DISTINCT COALESCE(m.canonical, t.cleaned))                    AS groups_mapped,
  AVG(CASE WHEN raw = '完了' THEN 1.0 ELSE 0.0 END)                   AS done_rate_raw,
  AVG(CASE WHEN cleaned = '完了' THEN 1.0 ELSE 0.0 END)               AS done_rate_cleaned,
  AVG(CASE WHEN COALESCE(m.canonical, t.cleaned) = '完了' THEN 1.0 ELSE 0.0 END) AS done_rate_mapped,
  COUNT(*) FILTER (WHERE m.canonical IS NULL)                         AS unmapped_rows
FROM t
LEFT JOIN status_map m ON m.variant = t.cleaned;
