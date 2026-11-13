-- 案件の売上を、担当者に3通りで付ける（T-SQL、未検証）
SELECT
  m.person_id,
  SUM(CASE WHEN m.role = N'主' THEN d.amount ELSE 0 END)        AS main_only,
  SUM(CAST(d.amount AS decimal(18, 2)) / d.team_size)            AS equal_split,
  SUM(CAST(d.amount AS decimal(18, 2)) * m.involvement)          AS by_involvement
FROM dbo.deal_members AS m
JOIN dbo.deals AS d ON d.deal_id = m.deal_id
GROUP BY m.person_id
ORDER BY by_involvement DESC;
