-- 赤黒で訂正した伝票を、最後に有効な伝票だけで数える（T-SQL 版。SQL Server では動かしていない：未検証）
-- dbo.slips(row_id, slip_no, kind, ref_slip_no, entry_date, orig_date, amount)
SELECT COUNT(*) AS slips, SUM(s.amount) AS amount
FROM dbo.slips AS s
WHERE s.kind IN (N'通常', N'黒')
  AND NOT EXISTS (SELECT 1 FROM dbo.slips AS r WHERE r.kind = N'赤' AND r.ref_slip_no = s.slip_no);

-- 月の売上を「もとの取引日」で数える（赤・黒も、もとの伝票の日付に戻す）
SELECT FORMAT(s.orig_date, 'yyyy-MM') AS ym, SUM(s.amount) AS amount
FROM dbo.slips AS s
GROUP BY FORMAT(s.orig_date, 'yyyy-MM');
