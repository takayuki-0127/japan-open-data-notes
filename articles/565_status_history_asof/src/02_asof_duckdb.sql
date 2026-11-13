-- 履歴から、:asof の日の終わりに有効だった状態を戻して、状態ごとの件数を出す（DuckDB）
-- valid_to は次の履歴の valid_from。最後の履歴は 9999-12-31 まで有効
WITH h AS (
  SELECT app_id, status, valid_from,
         COALESCE(LEAD(valid_from) OVER (PARTITION BY app_id ORDER BY valid_from, seq),
                  DATE '9999-12-31') AS valid_to
  FROM status_history)
SELECT status, COUNT(*) AS n
FROM h
WHERE valid_from <= DATE ':asof' AND DATE ':asof' < valid_to
GROUP BY status
ORDER BY status;
-- 当時見えていた数にするには、最初に WHERE recorded_on <= DATE ':asof' で履歴を絞ってから LEAD を取る
