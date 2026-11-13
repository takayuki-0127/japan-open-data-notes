-- 505 T-SQL（未検証：SQL Server では実行していない）
-- 次回のお届け日を4通りで出す。subscribers(member, signup_date) と deliveries(member, delivery_date) を想定。

-- (a) 30日後 / (d) 4週ごと
SELECT member, delivery_date,
       DATEADD(day, 30, delivery_date) AS next_d30,
       DATEADD(day, 28, delivery_date) AS next_w4
FROM deliveries;

-- (c) 前回のお届け日に1か月足す：DATEADD(month) は月末で日にちを縮めるので、31日→28日のまま戻らない
SELECT member, delivery_date, DATEADD(month, 1, delivery_date) AS next_drift
FROM deliveries;

-- (b) 毎月同じ日：申込日の日にちを基準にし、その日がない月は月末にする
SELECT d.member, d.delivery_date,
       CASE WHEN DAY(s.signup_date) > DAY(EOMONTH(d.delivery_date, 1))
            THEN EOMONTH(d.delivery_date, 1)
            ELSE DATEFROMPARTS(YEAR(EOMONTH(d.delivery_date, 1)), MONTH(EOMONTH(d.delivery_date, 1)), DAY(s.signup_date))
       END AS next_same_anchor
FROM deliveries AS d
JOIN subscribers AS s ON s.member = d.member;
