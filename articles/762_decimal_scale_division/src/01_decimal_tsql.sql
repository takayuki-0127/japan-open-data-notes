-- T-SQL：未検証（SQL Server では動かしていない）
-- SQL Server では、decimal どうしの割り算の結果の桁は、もとの型の桁から決まる（決まりは公式の文書を確かめること）。
-- 整数どうしなら整数の割り算になるので、どちらかを decimal にしてから割る。
SELECT store_id,
       CAST(applications AS decimal(10, 4)) / visitors                 AS rate_raw,
       CAST(CAST(applications AS decimal(10, 4)) / visitors AS decimal(5, 2)) AS rate_dec2,
       CAST(CAST(applications AS decimal(10, 4)) / visitors AS decimal(7, 4)) AS rate_dec4
FROM dbo.stores;
-- 率を入れる列を作るなら、桁を足りるだけ取る（例：比で小数4桁以上、または % で小数2桁以上）
-- ALTER TABLE dbo.store_kpi ALTER COLUMN apply_rate decimal(7, 4);
