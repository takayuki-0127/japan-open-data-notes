"""同じ8本のレポートを、2つの持ち方で書いた SQL。
star＝事実（fact_sales）とマスタ（product・store）、wide＝マスタの列を写した1枚の表（sales_wide）。
T-SQL でもそのまま通る書き方にしてある（YEAR・MONTH・SUM・COUNT(DISTINCT)）。SQL Server では未検証。"""
REPORTS = {
"R1 部門別の売上": dict(star="""
SELECT p.dept, SUM(f.amount) AS amount
FROM fact_sales f
JOIN product p ON p.product_id=f.product_id
GROUP BY p.dept""", wide="""
SELECT dept, SUM(amount) AS amount
FROM sales_wide
GROUP BY dept"""),
"R2 地域別・月別の売上": dict(star="""
SELECT s.region, YEAR(f.sale_date) AS y, MONTH(f.sale_date) AS m, SUM(f.amount) AS amount
FROM fact_sales f
JOIN store s ON s.store_id=f.store_id
GROUP BY s.region, YEAR(f.sale_date), MONTH(f.sale_date)""", wide="""
SELECT region, YEAR(sale_date) AS y, MONTH(sale_date) AS m, SUM(amount) AS amount
FROM sales_wide
GROUP BY region, YEAR(sale_date), MONTH(sale_date)"""),
"R3 部門×地域の売上": dict(star="""
SELECT p.dept, s.region, SUM(f.amount) AS amount
FROM fact_sales f
JOIN product p ON p.product_id=f.product_id
JOIN store s ON s.store_id=f.store_id
GROUP BY p.dept, s.region""", wide="""
SELECT dept, region, SUM(amount) AS amount
FROM sales_wide
GROUP BY dept, region"""),
"R4 商品別の売上と数量": dict(star="""
SELECT p.product_name, SUM(f.amount) AS amount, SUM(f.qty) AS qty
FROM fact_sales f
JOIN product p ON p.product_id=f.product_id
GROUP BY p.product_name""", wide="""
SELECT product_name, SUM(amount) AS amount, SUM(qty) AS qty
FROM sales_wide
GROUP BY product_name"""),
"R5 店別の売上": dict(star="""
SELECT s.store_name, SUM(f.amount) AS amount
FROM fact_sales f
JOIN store s ON s.store_id=f.store_id
GROUP BY s.store_name""", wide="""
SELECT store_name, SUM(amount) AS amount
FROM sales_wide
GROUP BY store_name"""),
"R6 部門別の前年比": dict(star="""
SELECT p.dept,
       SUM(CASE WHEN YEAR(f.sale_date)=2025 THEN f.amount ELSE 0 END) AS a2025,
       SUM(CASE WHEN YEAR(f.sale_date)=2024 THEN f.amount ELSE 0 END) AS a2024
FROM fact_sales f
JOIN product p ON p.product_id=f.product_id
GROUP BY p.dept""", wide="""
SELECT dept,
       SUM(CASE WHEN YEAR(sale_date)=2025 THEN amount ELSE 0 END) AS a2025,
       SUM(CASE WHEN YEAR(sale_date)=2024 THEN amount ELSE 0 END) AS a2024
FROM sales_wide
GROUP BY dept"""),
"R7 部門別の売れた商品の数": dict(star="""
SELECT p.dept, COUNT(DISTINCT f.product_id) AS n_products
FROM fact_sales f
JOIN product p ON p.product_id=f.product_id
GROUP BY p.dept""", wide="""
SELECT dept, COUNT(DISTINCT product_id) AS n_products
FROM sales_wide
GROUP BY dept"""),
"R8 月別の売上（全体）": dict(star="""
SELECT YEAR(sale_date) AS y, MONTH(sale_date) AS m, SUM(amount) AS amount
FROM fact_sales
GROUP BY YEAR(sale_date), MONTH(sale_date)""", wide="""
SELECT YEAR(sale_date) AS y, MONTH(sale_date) AS m, SUM(amount) AS amount
FROM sales_wide
GROUP BY YEAR(sale_date), MONTH(sale_date)"""),
}
USES = {"R1 部門別の売上": ["dept"], "R2 地域別・月別の売上": ["region"], "R3 部門×地域の売上": ["dept", "region"],
        "R4 商品別の売上と数量": ["product_name"], "R5 店別の売上": ["store_name"], "R6 部門別の前年比": ["dept"],
        "R7 部門別の売れた商品の数": ["dept"], "R8 月別の売上（全体）": []}
