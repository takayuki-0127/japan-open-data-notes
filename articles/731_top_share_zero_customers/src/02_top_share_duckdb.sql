-- DuckDB で実行（1スレッド）。期間 :months か月の「上位10%の売上シェア」を2通りで出す
-- buyers  : その期間に買った人だけを並べる
-- members : 会員全員（買わなかった人は0円）を並べる
WITH amt AS (
    SELECT m.member_id, COALESCE(SUM(p.amount), 0) AS amount
    FROM members m
    LEFT JOIN purchases p ON p.member_id = m.member_id AND p.month <= :months
    GROUP BY m.member_id
), ranked AS (
    SELECT member_id, amount,
           ROW_NUMBER() OVER (ORDER BY amount DESC, member_id)                      AS rn_all,
           COUNT(*) OVER ()                                                         AS n_all,
           ROW_NUMBER() OVER (PARTITION BY amount > 0 ORDER BY amount DESC, member_id) AS rn_buy,
           SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) OVER ()                      AS n_buy
    FROM amt
)
SELECT 'members' AS base, SUM(CASE WHEN rn_all <= CEIL(0.1 * n_all) THEN amount ELSE 0 END) / SUM(amount) AS top10_share,
       MAX(n_all) AS people
FROM ranked
UNION ALL
SELECT 'buyers', SUM(CASE WHEN amount > 0 AND rn_buy <= CEIL(0.1 * n_buy) THEN amount ELSE 0 END) / SUM(amount),
       MAX(n_buy)
FROM ranked
ORDER BY base;
