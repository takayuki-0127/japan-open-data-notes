-- 会員カードを出したレシートだけの客単価と、金額帯で補正した客単価（DuckDB 版）
-- receipts(receipt_id, amount, card, b3, b5, b10)：card＝1 なら会員カードを出した。b3/b5/b10 は金額帯
SELECT AVG(CASE WHEN card = 1 THEN amount END) AS member_avg,
       AVG(amount)                              AS all_avg,
       AVG(card)                                AS card_rate
FROM receipts;
-- 金額帯（5つ）ごとの会員の平均を、全レシートの帯ごとの枚数で重みづけ
WITH m AS (SELECT b5 AS band, AVG(amount) AS avg_member FROM receipts WHERE card = 1 GROUP BY b5),
     c AS (SELECT b5 AS band, COUNT(*) AS n_all FROM receipts GROUP BY b5)
SELECT SUM(m.avg_member * c.n_all) / SUM(c.n_all) AS corrected_avg
FROM m JOIN c ON c.band = m.band;
