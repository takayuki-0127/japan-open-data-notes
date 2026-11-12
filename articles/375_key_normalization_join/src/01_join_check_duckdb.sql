-- 正規化したキー k でつなぎ、つながらない行・別の取引先につながった行・行の増え方を数える（DuckDB）
WITH j AS (
      SELECT i.請求番号, i.正しい取引先ID, i.金額, m.取引先ID
      FROM inv AS i LEFT JOIN mst AS m ON m.k = i.k)
    SELECT COUNT(DISTINCT 請求番号)                                                            AS 請求の行,
           COUNT(*)                                                                          AS 結合後の行,
           COUNT(DISTINCT CASE WHEN 取引先ID IS NULL THEN 請求番号 END)                          AS つながらない行,
           COUNT(DISTINCT CASE WHEN 取引先ID IS NOT NULL AND 取引先ID <> 正しい取引先ID THEN 請求番号 END) AS 別の取引先につながった行,
           SUM(CASE WHEN 取引先ID IS NULL THEN 金額 ELSE 0 END)                                 AS つながらない金額,
           SUM(金額)                                                                         AS 結合後の金額の合計
    FROM j;
