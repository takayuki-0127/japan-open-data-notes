-- 傾向スコア（ps）が付いた表から、逆確率の重みで平均の差を出す（DuckDB）
-- 正規化した重み付き平均（Hajek 型）。「0.05〜0.95だけ残す」も同じ式で数える
WITH w AS (
    SELECT *, CASE WHEN treated = 1 THEN 1.0 / ps ELSE 1.0 / (1 - ps) END AS wt
    FROM units
)
SELECT
    SUM(CASE WHEN treated = 1 THEN wt * y END) / SUM(CASE WHEN treated = 1 THEN wt END)
  - SUM(CASE WHEN treated = 0 THEN wt * y END) / SUM(CASE WHEN treated = 0 THEN wt END)              AS ipw,
    SUM(CASE WHEN treated = 1 AND ps BETWEEN 0.05 AND 0.95 THEN wt * y END)
      / SUM(CASE WHEN treated = 1 AND ps BETWEEN 0.05 AND 0.95 THEN wt END)
  - SUM(CASE WHEN treated = 0 AND ps BETWEEN 0.05 AND 0.95 THEN wt * y END)
      / SUM(CASE WHEN treated = 0 AND ps BETWEEN 0.05 AND 0.95 THEN wt END)                          AS trim05,
    MAX(wt)                       AS max_weight,
    SUM(wt) * SUM(wt) / SUM(wt * wt) AS effective_n
FROM w;
