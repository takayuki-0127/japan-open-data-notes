-- 3つの「週」で週次の売上を出す（T-SQL。SQL Server 本体では動かしていません：未検証）

-- ① ISO 週（月曜始まり、1月4日を含む週が第1週）。年は「ISO の年」でまとめる
SELECT YEAR(DATEADD(day, 26 - DATEPART(iso_week, d), d)) AS iso_year,   -- ISO の年（YEAR(d) ではない）
       DATEPART(iso_week, d) AS iso_week,
       COUNT(*) AS days, SUM(amount) AS sales
FROM sales
GROUP BY YEAR(DATEADD(day, 26 - DATEPART(iso_week, d), d)), DATEPART(iso_week, d);

-- ② 日曜始まり・1月1日の週が第1週（DATEFIRST 7 のときの DATEPART(week)）
SET DATEFIRST 7;
SELECT YEAR(d) AS y, DATEPART(week, d) AS wk, COUNT(*) AS days, SUM(amount) AS sales
FROM sales
GROUP BY YEAR(d), DATEPART(week, d);

-- ③ やりがちな取り違え：YEAR(d) と ISO 週を組み合わせる（年末の数日が「その年の第1週」に混ざる）
SELECT YEAR(d) AS y, DATEPART(iso_week, d) AS iso_week, COUNT(*) AS days, SUM(amount) AS sales
FROM sales
GROUP BY YEAR(d), DATEPART(iso_week, d);
