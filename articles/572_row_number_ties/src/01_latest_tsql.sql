-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 同じ updated_at の行が複数あるとき、ORDER BY updated_at DESC だけでは選ばれる行が決まらない
WITH t AS (
  SELECT member_id, status,
         ROW_NUMBER() OVER (PARTITION BY member_id
                            ORDER BY updated_at DESC, seq DESC) AS rn  -- 連番で同順位をなくす
  FROM dbo.status_log
)
SELECT member_id, status
FROM t
WHERE rn = 1;

-- 同順位がどれだけあるかを先に数える
SELECT COUNT(*) AS tied_members
FROM (
  SELECT member_id
  FROM dbo.status_log l
  WHERE updated_at = (SELECT MAX(updated_at) FROM dbo.status_log x WHERE x.member_id = l.member_id)
  GROUP BY member_id
  HAVING COUNT(*) > 1
) z;
