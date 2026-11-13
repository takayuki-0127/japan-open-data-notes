-- 案件の売上を、担当者に3通りで付ける（DuckDB）
-- deals：deal_id・amount・team_size
-- deal_members：deal_id・person_id・role（主／応援）・involvement（案件内で合計1）
SELECT
  m.person_id,
  SUM(CASE WHEN m.role = '主' THEN d.amount ELSE 0 END) AS main_only,       -- 主担当に全額
  SUM(d.amount * 1.0 / d.team_size)                    AS equal_split,     -- 人数で均等割り
  SUM(d.amount * m.involvement)                        AS by_involvement   -- 関与度の比
FROM deal_members m
JOIN deals d ON d.deal_id = m.deal_id
GROUP BY m.person_id
ORDER BY by_involvement DESC;
