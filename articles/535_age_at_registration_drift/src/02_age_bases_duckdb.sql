-- 満年齢を3通りの日で出す（DuckDB で実行）。誕生日の当日に1つ加わる扱い
-- members(member_id, birth_date, registered_on)、purchases(purchase_id, member_id, purchased_on)
SELECT member_id,
       year(registered_on) - year(birth_date)
         - CASE WHEN month(registered_on) * 100 + day(registered_on) < month(birth_date) * 100 + day(birth_date) THEN 1 ELSE 0 END AS age_at_registration,
       2026 - year(birth_date)
         - CASE WHEN 3 * 100 + 31 < month(birth_date) * 100 + day(birth_date) THEN 1 ELSE 0 END AS age_asof
FROM members
ORDER BY member_id;
SELECT p.purchase_id,
       year(p.purchased_on) - year(m.birth_date)
         - CASE WHEN month(p.purchased_on) * 100 + day(p.purchased_on) < month(m.birth_date) * 100 + day(m.birth_date) THEN 1 ELSE 0 END AS age_at_purchase
FROM purchases AS p JOIN members AS m USING (member_id)
ORDER BY p.purchase_id
