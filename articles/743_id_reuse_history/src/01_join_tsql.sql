-- T-SQL：未検証
-- 番号と在籍期間でつなぐ
SELECT m.person_id, m.member_no, p.purchase_id, p.purchased_on, p.amount
FROM dbo.members AS m
JOIN dbo.purchases AS p
  ON p.member_no = m.member_no
 AND p.purchased_on >= m.joined_on
 AND (m.left_on IS NULL OR p.purchased_on < m.left_on);
