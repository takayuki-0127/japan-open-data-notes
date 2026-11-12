-- 475 月次の解約率を、分母を4通りに変えて出す（T-SQL の書き方）
-- members(member_id, join_date, cancel_date)：cancel_date は最後に在籍した日。在籍中は NULL
-- months(month_start, next_start, days_in_month)／days(d)：カレンダー
-- 記事では DuckDB で実行して pandas の結果と一致を確かめた。SQL Server での実行は未検証
WITH head AS (          -- 期首（1日の時点で在籍）と期末（翌月1日の時点で在籍）
    SELECT m.month_start,
           SUM(CASE WHEN b.join_date < m.month_start AND (b.cancel_date IS NULL OR b.cancel_date >= m.month_start) THEN 1 ELSE 0 END) AS n_start,
           SUM(CASE WHEN b.join_date < m.next_start  AND (b.cancel_date IS NULL OR b.cancel_date >= m.next_start)  THEN 1 ELSE 0 END) AS n_end,
           SUM(CASE WHEN b.join_date >= m.month_start AND b.join_date < m.next_start THEN 1 ELSE 0 END) AS n_join,
           SUM(CASE WHEN b.cancel_date >= m.month_start AND b.cancel_date < m.next_start THEN 1 ELSE 0 END) AS n_cancel,
           SUM(CASE WHEN b.cancel_date >= m.month_start AND b.cancel_date < m.next_start AND b.join_date >= m.month_start THEN 1 ELSE 0 END) AS n_cancel_new
    FROM months AS m
    JOIN members AS b
      ON b.join_date < m.next_start AND (b.cancel_date IS NULL OR b.cancel_date >= m.month_start)
    GROUP BY m.month_start
),
md AS (                 -- 在籍日数：在籍していた日を1日ずつ数える
    SELECT m.month_start, COUNT(*) AS member_days
    FROM months AS m
    JOIN days AS c ON c.d >= m.month_start AND c.d < m.next_start
    JOIN members AS b ON b.join_date <= c.d AND (b.cancel_date IS NULL OR b.cancel_date >= c.d)
    GROUP BY m.month_start
)
SELECT h.month_start, h.n_start, h.n_end, h.n_join, h.n_cancel, h.n_cancel_new, md.member_days,
       100.0 * h.n_cancel / h.n_start                              AS churn_start,     -- ① 期首人数
       100.0 * h.n_cancel / ((h.n_start + h.n_end) / 2.0)          AS churn_avg,       -- ② 期首と期末の平均
       100.0 * h.n_cancel / (h.n_start + h.n_join)                 AS churn_any,       -- ③ その月に1日でも在籍した人数
       100.0 * h.n_cancel / (1.0 * md.member_days / m.days_in_month) AS churn_days     -- ④ 在籍日数（人・月）
FROM head AS h
JOIN md ON md.month_start = h.month_start
JOIN months AS m ON m.month_start = h.month_start
ORDER BY h.month_start;
