-- 「桜ヶ丘」の住所を探す（DuckDB 版）。customers(cust_id, address, address_norm)。地名はすべて架空
-- A1 部分一致：別の町名（東桜ヶ丘・桜ヶ丘台）や建物名まで拾い、「桜ケ丘」と書いた行は取りこぼす
SELECT cust_id FROM customers WHERE address LIKE '%桜ヶ丘%';
-- A2 市の名前から前方一致：市を省いた行・「ケ」の行を取りこぼし、桜ヶ丘台は拾う
SELECT cust_id FROM customers WHERE address LIKE '架空市桜ヶ丘%';
-- A3 正規化した住所で、町名のすぐあとが数字か丁目か終わりであることを確かめる
SELECT cust_id FROM customers WHERE regexp_matches(address_norm, '^(架空市)?桜ヶ丘([0-9一二三四五六七八九]|$)');
