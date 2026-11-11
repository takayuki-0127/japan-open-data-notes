-- 00 政令市の「区」への編入を、市のコードにそろえる（T-SQL）。この記事の単位は政令市を市全体で数えるため
-- 区のコード（例：22103 清水区）→ 同じ県で、区のコード以下でいちばん大きい政令市のコード（22100 静岡市）
UPDATE x
SET new_code = (SELECT MAX(c.code) FROM dbo.seirei_cities c
                WHERE LEFT(c.code, 2) = LEFT(x.new_code, 2) AND c.code <= x.new_code)
FROM dbo.events_x x
WHERE SUBSTRING(x.new_code, 3, 1) = '1'                    -- 市区町村コードの3桁目が1＝政令市・区
  AND x.new_code NOT IN (SELECT code FROM dbo.seirei_cities)
  AND x.new_code NOT BETWEEN '13101' AND '13123';         -- 東京23区は区のまま
