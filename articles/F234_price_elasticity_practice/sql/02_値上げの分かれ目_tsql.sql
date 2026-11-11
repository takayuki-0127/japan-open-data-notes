-- F234：値上げで利益が減り始める弾力性（分かれ目）。粗利率 m・値上げ幅 x の組み合わせ（T-SQL）
WITH m AS (SELECT v AS margin FROM (VALUES (0.1),(0.2),(0.3),(0.5)) t(v)),
     x AS (SELECT v AS price_up FROM (VALUES (0.03),(0.05),(0.10)) t(v))
SELECT margin, price_up,
       LOG(margin / (margin + price_up)) / LOG(1 + price_up) AS breakeven_elasticity
FROM m CROSS JOIN x
ORDER BY margin, price_up;
