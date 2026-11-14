-- Q1 1日・ja・必要な列だけ
SELECT COUNT(*) AS n_rows, SUM(views) AS views FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE DATE(datehour) = '2025-11-01' AND wiki = 'ja' -- c5q1
-- Q2 7日・ja
SELECT COUNT(*) AS n_rows, SUM(views) AS views FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE DATE(datehour) BETWEEN '2025-11-01' AND '2025-11-07' AND wiki = 'ja' -- c5q2
-- Q3 1日・全言語（クラスタが効かない）
SELECT wiki, SUM(views) AS views FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE DATE(datehour) = '2025-11-01' GROUP BY wiki ORDER BY views DESC LIMIT 20 -- c5q3
-- Q4 1日・SELECT * LIMIT 10
SELECT * FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE DATE(datehour) = '2025-11-01' LIMIT 10 -- c5q4
-- Q5 7日・ja・正確な重複なし件数
SELECT COUNT(DISTINCT title) AS n_title FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE DATE(datehour) BETWEEN '2025-11-01' AND '2025-11-07' AND wiki = 'ja' -- c5q5
-- Q6 7日・ja・近似の重複なし件数
SELECT APPROX_COUNT_DISTINCT(title) AS n_title FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE DATE(datehour) BETWEEN '2025-11-01' AND '2025-11-07' AND wiki = 'ja' -- c5q6
-- Q7 パーティションの絞り込みなし（エラーになるか）
SELECT SUM(views) FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE wiki = 'ja' -- c5q7
-- Q8 関数で包んだ日付（TIMESTAMP の範囲で書いた場合と比べる）
SELECT COUNT(*) AS n_rows, SUM(views) AS views FROM `bigquery-public-data.wikipedia.pageviews_2025` WHERE datehour >= TIMESTAMP '2025-11-01' AND datehour < TIMESTAMP '2025-11-02' AND wiki = 'ja' -- c5q8
