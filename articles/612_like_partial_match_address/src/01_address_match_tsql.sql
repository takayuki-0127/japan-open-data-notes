-- T-SQL：未検証（SQL Server では動かしていない）。SQL Server には正規表現がないので、正規化した列と町名の列を作ってから一致させる
-- 正規化（全角→半角、ケ→ヶ、空白の除去）は取り込みのときにアプリ側で行い、address_norm に入れておく想定
SELECT cust_id
FROM dbo.customers
WHERE address_norm LIKE N'桜ヶ丘[0-9]%'
   OR address_norm LIKE N'桜ヶ丘[一二三四五六七八九]%'
   OR address_norm LIKE N'架空市桜ヶ丘[0-9]%'
   OR address_norm LIKE N'架空市桜ヶ丘[一二三四五六七八九]%'
   OR address_norm IN (N'桜ヶ丘', N'架空市桜ヶ丘');
