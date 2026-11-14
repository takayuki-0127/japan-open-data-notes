-- ダッシュボード（Looker Studio）用の小さい表を作る SQL
-- 置き場所：自分のプロジェクトの c5_demo データセット（サンドボックス）
-- サンドボックスの表は 60 日で消える。消えたら、このファイルを上から流し直す。
-- 読む量の目安：ja_daily と wiki_week で合わせて十数 GB（無料枠 1 TiB/月の内）

-- 1) 日本語版の 1 日ごとの閲覧数（2025年11月）
CREATE OR REPLACE TABLE c5_demo.ja_daily AS
SELECT
  DATE(datehour) AS day,
  SUM(views) AS views,
  COUNT(*) AS n_rows,
  APPROX_COUNT_DISTINCT(title) AS n_title
FROM `bigquery-public-data.wikipedia.pageviews_2025`
WHERE datehour >= TIMESTAMP '2025-11-01'
  AND datehour < TIMESTAMP '2025-12-01'
  AND wiki = 'ja'
GROUP BY day;

-- 2) 言語版ごとの 1 週間の閲覧数（上位 20）
CREATE OR REPLACE TABLE c5_demo.wiki_week AS
SELECT
  wiki,
  SUM(views) AS views
FROM `bigquery-public-data.wikipedia.pageviews_2025`
WHERE datehour >= TIMESTAMP '2025-11-01'
  AND datehour < TIMESTAMP '2025-11-08'
GROUP BY wiki
ORDER BY views DESC
LIMIT 20;

-- 3) 記事で流したクエリ（コメントに c5q を付けたもの）の読む量
--    CREATE 文・JOBS_BY を読むクエリ・キャッシュから返ったものは除く
CREATE OR REPLACE TABLE c5_demo.query_cost AS
SELECT
  CASE
    WHEN query LIKE '%c5q1%' THEN '1日・日本語版'
    WHEN query LIKE '%c5q2%' THEN '7日・日本語版'
    WHEN query LIKE '%c5q3%' THEN '1日・全言語'
    WHEN query LIKE '%c5q4%' THEN '1日・SELECT * LIMIT 10'
    WHEN query LIKE '%c5q5%' THEN '7日・記事数（正確）'
    WHEN query LIKE '%c5q6%' THEN '7日・記事数（近似）'
    WHEN query LIKE '%c5q8%' THEN '1日・日本語版（TIMESTAMP で絞る）'
    WHEN query LIKE '%c5q9%' THEN '30日・日本語版'
    ELSE 'その他'
  END AS label,
  total_bytes_billed / 1e6 AS mb_billed,
  total_slot_ms AS slot_ms,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) AS elapsed_ms
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
WHERE query LIKE '%c5q%'
  AND statement_type = 'SELECT'
  AND query NOT LIKE '%JOBS_BY%'
  AND cache_hit IS NOT TRUE
  AND state = 'DONE'
  AND error_result IS NULL;
