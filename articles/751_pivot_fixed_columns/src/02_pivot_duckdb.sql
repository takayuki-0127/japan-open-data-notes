-- PIVOT の列を固定で書くと、あとから増えた区分はどうなるか（DuckDB 版）
-- sales(ym DATE（月初）, category VARCHAR, amount BIGINT)
-- A 列を固定した PIVOT（作った時点の6区分だけを書いた）
SELECT * FROM (
  PIVOT sales ON category IN ('食品', '飲料', '日用品', '衣料', '家電', '雑貨') USING SUM(amount) GROUP BY ym
) ORDER BY ym;
-- B CASE WHEN で6区分を横に並べ、「その他」と「合計」の列も足す
SELECT ym,
       SUM(CASE WHEN category = '食品'   THEN amount ELSE 0 END) AS 食品,
       SUM(CASE WHEN category = '飲料'   THEN amount ELSE 0 END) AS 飲料,
       SUM(CASE WHEN category = '日用品' THEN amount ELSE 0 END) AS 日用品,
       SUM(CASE WHEN category = '衣料'   THEN amount ELSE 0 END) AS 衣料,
       SUM(CASE WHEN category = '家電'   THEN amount ELSE 0 END) AS 家電,
       SUM(CASE WHEN category = '雑貨'   THEN amount ELSE 0 END) AS 雑貨,
       SUM(CASE WHEN category NOT IN ('食品', '飲料', '日用品', '衣料', '家電', '雑貨') THEN amount ELSE 0 END) AS その他,
       SUM(amount) AS 合計
FROM sales GROUP BY ym ORDER BY ym;
-- C 縦持ちのまま月の合計（答え合わせ用）
SELECT ym, SUM(amount) AS total FROM sales GROUP BY ym ORDER BY ym;
-- D 表にない区分を探す（固定の列に入っていない区分）
SELECT category, MIN(ym) AS first_month, SUM(amount) AS amount
FROM sales
WHERE category NOT IN ('食品', '飲料', '日用品', '衣料', '家電', '雑貨')
GROUP BY category ORDER BY first_month;
