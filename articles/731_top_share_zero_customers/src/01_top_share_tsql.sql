-- T-SQL：未検証（SQL Server では動かしていない）
DECLARE @months int = 12;
WITH amt AS (
    SELECT m.member_id, COALESCE(SUM(p.amount), 0) AS amount
    FROM members m
    LEFT JOIN purchases p ON p.member_id = m.member_id AND p.month <= @months
    GROUP BY m.member_id
), ranked AS (
    SELECT member_id, amount,
           ROW_NUMBER() OVER (ORDER BY amount DESC, member_id) AS rn_all,
           COUNT(*) OVER () AS n_all,
           ROW_NUMBER() OVER (PARTITION BY CASE WHEN amount > 0 THEN 1 ELSE 0 END ORDER BY amount DESC, member_id) AS rn_buy,
           SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) OVER () AS n_buy
    FROM amt
)
SELECT 'members' AS base,
       SUM(CASE WHEN rn_all <= CEILING(0.1 * n_all) THEN amount ELSE 0 END) * 1.0 / SUM(amount) AS top10_share
FROM ranked
UNION ALL
SELECT 'buyers',
       SUM(CASE WHEN amount > 0 AND rn_buy <= CEILING(0.1 * n_buy) THEN amount ELSE 0 END) * 1.0 / SUM(amount)
FROM ranked;
