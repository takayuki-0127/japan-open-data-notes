-- 会員の番号が使い回されているとき、購入を会員につなぐ（DuckDB）
-- members：番号（member_no）・入会日（joined_on）・退会日（left_on、在籍中は NULL）。同じ番号が2人目に使われることがある
-- (1) 番号だけでつなぐ（使い回しの前の人の購入も、今の人につく）
CREATE OR REPLACE TABLE j_no AS
SELECT m.person_id, m.member_no, p.purchase_id, p.purchased_on, p.amount
FROM members AS m JOIN purchases AS p ON p.member_no = m.member_no;
-- (2) 番号と在籍期間でつなぐ（入会日以上、退会日より前）
CREATE OR REPLACE TABLE j_period AS
SELECT m.person_id, m.member_no, p.purchase_id, p.purchased_on, p.amount
FROM members AS m JOIN purchases AS p
  ON p.member_no = m.member_no
 AND p.purchased_on >= m.joined_on
 AND (m.left_on IS NULL OR p.purchased_on < m.left_on);
SELECT (SELECT COUNT(*) FROM j_no) AS rows_no, (SELECT COUNT(*) FROM j_period) AS rows_period;
