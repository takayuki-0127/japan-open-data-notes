-- 443 分類の付け替えがあるときの3つの集計（T-SQL 版。SQL Server 本体では未検証。同じ考え方の SQL を DuckDB で実行して確かめた）
-- sales(product_id INT, ym CHAR(7), amount BIGINT)
-- class_hist(product_id INT, category NVARCHAR(20), valid_from CHAR(7), valid_to CHAR(7))  … 期間つきの分類（valid_to は最後の月。いまも有効なら '9999-12'）
-- class_now(product_id INT, category NVARCHAR(20))                                        … いまの分類だけ（扱いをやめた商品は載っていない）

-- ① いまのマスタだけで集計（載っていない商品の売上は落ちる）
SELECT c.category, LEFT(s.ym, 4) AS y, SUM(s.amount) AS amount
FROM sales s JOIN class_now c ON c.product_id = s.product_id
GROUP BY c.category, LEFT(s.ym, 4);

-- ② 当時の区分で集計（その月に有効だった分類）
SELECT h.category, LEFT(s.ym, 4) AS y, SUM(s.amount) AS amount
FROM sales s JOIN class_hist h ON h.product_id = s.product_id AND s.ym BETWEEN h.valid_from AND h.valid_to
GROUP BY h.category, LEFT(s.ym, 4);

-- ③ いまの区分に引き直して集計（商品ごとに、いちばん新しい分類を過去の全部の月に当てる）
WITH latest AS (
  SELECT product_id, category,
         ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY valid_from DESC) AS rn
  FROM class_hist
)
SELECT l.category, LEFT(s.ym, 4) AS y, SUM(s.amount) AS amount
FROM sales s JOIN latest l ON l.product_id = s.product_id AND l.rn = 1
GROUP BY l.category, LEFT(s.ym, 4);
