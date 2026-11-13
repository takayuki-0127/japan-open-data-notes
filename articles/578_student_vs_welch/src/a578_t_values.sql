-- 2群の平均の差について、ふつうのt検定（等分散）とウェルチの検定の t 値・自由度を計算する（DuckDB）
WITH g AS (
    SELECT grp, COUNT(*) AS n, AVG(value) AS m, VAR_SAMP(value) AS v
    FROM obs
    GROUP BY grp
), w AS (
    SELECT MAX(CASE WHEN grp = 'A' THEN n END) AS n1, MAX(CASE WHEN grp = 'A' THEN m END) AS m1, MAX(CASE WHEN grp = 'A' THEN v END) AS v1,
           MAX(CASE WHEN grp = 'B' THEN n END) AS n2, MAX(CASE WHEN grp = 'B' THEN m END) AS m2, MAX(CASE WHEN grp = 'B' THEN v END) AS v2
    FROM g
)
SELECT
    -- ふつうのt検定：2群の分散を合わせた1つの値（合併分散）を使う
    (m1 - m2) / SQRT(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2) * (1.0 / n1 + 1.0 / n2)) AS t_student,
    n1 + n2 - 2 AS df_student,
    -- ウェルチの検定：群ごとの分散をそのまま使う
    (m1 - m2) / SQRT(v1 / n1 + v2 / n2) AS t_welch,
    POWER(v1 / n1 + v2 / n2, 2) / (POWER(v1 / n1, 2) / (n1 - 1) + POWER(v2 / n2, 2) / (n2 - 1)) AS df_welch
FROM w;
