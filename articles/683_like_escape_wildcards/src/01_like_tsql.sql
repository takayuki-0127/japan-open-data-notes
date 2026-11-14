-- T-SQL：未検証
-- 品名に「_M」を含む行を数える。3つの書き方
SELECT COUNT(*) FROM dbo.items WHERE item_name LIKE N'%_M%';                -- エスケープなし：_ は任意の1文字（余分に拾う）
SELECT COUNT(*) FROM dbo.items WHERE item_name LIKE N'%\_M%' ESCAPE N'\';   -- ESCAPE 句
SELECT COUNT(*) FROM dbo.items WHERE item_name LIKE N'%[_]M%';              -- 角かっこ（SQL Server の書き方）

-- 「100%」を含む行
SELECT COUNT(*) FROM dbo.items WHERE item_name LIKE N'%100[%]%';
SELECT COUNT(*) FROM dbo.items WHERE item_name LIKE N'%100\%%' ESCAPE N'\';

-- 文字として探すだけなら、LIKE を使わない書き方もある
SELECT COUNT(*) FROM dbo.items WHERE CHARINDEX(N'_M', item_name) > 0;
