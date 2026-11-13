-- T-SQL：未検証（SQL Server では動かしていない）
-- DATEDIFF(month, ...) は「月の境目をまたいだ回数」を返す（1/31 → 2/1 でも 1）
SELECT contract_id,
       start_date,
       end_date,
       DATEDIFF(month, start_date, end_date) AS months_boundary,
       -- 満月数：日が足りなければ1を引く（月末どうしは満了とみなす）
       DATEDIFF(month, start_date, end_date)
         - CASE WHEN DAY(end_date) < DAY(start_date)
                 AND end_date <> EOMONTH(end_date) THEN 1 ELSE 0 END AS months_full,
       DATEDIFF(day, start_date, end_date) / 30 AS months_days30
FROM contracts;
