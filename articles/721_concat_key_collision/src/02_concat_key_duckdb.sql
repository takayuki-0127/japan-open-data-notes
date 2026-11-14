-- DuckDB で実行（1スレッド）。区切りなし・区切りあり・2列のままの3通りで、目標の表を売上につなぐ
-- sales(store_cd, item_cd, amount)、targets_nosep(key_nosep, target)、targets(store_cd, item_cd, target)
WITH j_nosep AS (
    SELECT s.store_cd, s.item_cd, s.amount, t.target
    FROM sales s JOIN targets_nosep t ON s.store_cd || s.item_cd = t.key_nosep
), j_sep AS (
    SELECT s.store_cd, s.item_cd, s.amount, t.target
    FROM sales s JOIN targets_sep t ON s.store_cd || '-' || s.item_cd = t.key_sep
), j_two AS (
    SELECT s.store_cd, s.item_cd, s.amount, t.target
    FROM sales s JOIN targets t ON s.store_cd = t.store_cd AND s.item_cd = t.item_cd
)
SELECT 'nosep' AS method, COUNT(*) AS rows, SUM(amount) AS amount, SUM(target) AS target FROM j_nosep
UNION ALL SELECT 'sep', COUNT(*), SUM(amount), SUM(target) FROM j_sep
UNION ALL SELECT 'two_columns', COUNT(*), SUM(amount), SUM(target) FROM j_two
ORDER BY method;
