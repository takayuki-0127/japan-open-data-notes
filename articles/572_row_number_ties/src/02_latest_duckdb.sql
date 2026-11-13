-- 会員ごとに「最新の1行」を選ぶ（DuckDB）。時刻だけで並べると、同じ時刻の行どうしの順番は決まらない
SELECT member_id, status FROM (
  SELECT member_id, status,
         ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY updated_at DESC) AS rn
  FROM status_log
) t
WHERE rn = 1
ORDER BY member_id;
-- 正しくは、書き込み順の連番まで並びに入れる：ORDER BY updated_at DESC, seq DESC
