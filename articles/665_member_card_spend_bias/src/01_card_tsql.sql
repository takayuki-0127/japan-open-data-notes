-- T-SQL：未検証（SQL Server では動かしていない）
SELECT AVG(CASE WHEN card = 1 THEN CAST(amount AS float) END) AS member_avg,
       AVG(CAST(amount AS float))                              AS all_avg,
       AVG(CAST(card AS float))                                AS card_rate
FROM dbo.receipts;
WITH m AS (SELECT b5 AS band, AVG(CAST(amount AS float)) AS avg_member FROM dbo.receipts WHERE card = 1 GROUP BY b5),
     c AS (SELECT b5 AS band, COUNT(*) AS n_all FROM dbo.receipts GROUP BY b5)
SELECT SUM(m.avg_member * c.n_all) / SUM(c.n_all) AS corrected_avg
FROM m JOIN c ON c.band = m.band;
