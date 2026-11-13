-- 営業時間（平日9〜18時、休業日を除く）で数えた経過分を、カレンダー表から出す（DuckDB で実行）
-- cal(d, biz, mins, cum_before)：その日が営業日か、その日の営業分、その日の0時までの累積の営業分
WITH idx AS (
  SELECT i.id,
         c1.cum_before + CASE WHEN c1.biz THEN LEAST(GREATEST(
             hour(i.received) * 60 + minute(i.received) + second(i.received) / 60.0 - 540, 0), 540) ELSE 0 END AS b_recv,
         c2.cum_before + CASE WHEN c2.biz THEN LEAST(GREATEST(
             hour(i.replied)  * 60 + minute(i.replied)  + second(i.replied)  / 60.0 - 540, 0), 540) ELSE 0 END AS b_repl
  FROM inq AS i
  JOIN cal AS c1 ON c1.d = CAST(i.received AS DATE)
  JOIN cal AS c2 ON c2.d = CAST(i.replied  AS DATE))
SELECT id, b_repl - b_recv AS biz_min FROM idx;
