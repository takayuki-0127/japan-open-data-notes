-- 赤黒で訂正した伝票を、最後に有効な伝票だけで数える（DuckDB 版）
-- slips(row_id, slip_no, kind, ref_slip_no, entry_date, orig_date, amount)
--   kind：'通常'（はじめの登録）、'赤'（取消。ref_slip_no は取り消す伝票、amount はマイナス）、'黒'（再登録。ref_slip_no は取り消した伝票）
WITH cancelled AS (SELECT DISTINCT ref_slip_no AS slip_no FROM slips WHERE kind = '赤')
SELECT COUNT(*) AS slips, SUM(amount) AS amount
FROM slips AS s
WHERE s.kind IN ('通常', '黒')
  AND s.slip_no NOT IN (SELECT slip_no FROM cancelled);
