-- 品名に文字列を含む行を数える（DuckDB）。? には Python から作ったパターンを入れる
-- エスケープなし：例 '%_M%'
SELECT COUNT(*) FROM items WHERE item_name LIKE ?;
-- ESCAPE 句：例 '%\_M%'（\ のあとの _ や % は文字として読む）
SELECT COUNT(*) FROM items WHERE item_name LIKE ? ESCAPE '\';
-- 角かっこ：例 '%[_]M%'。DuckDB では [ ] は文字として読まれるので、SQL Server と結果が違う
SELECT COUNT(*) FROM items WHERE item_name LIKE ?;
