-- 基準日時点の未入金の請求を、2つの起算日で区分に分ける（DuckDB 版）
-- invoices(invoice_id, customer_id, invoice_date, due_date, amount, paid_date)  paid_date が基準日より後、または空なら未入金
WITH open_inv AS (
  SELECT *, date_diff('day', invoice_date, $asof) AS days_from_invoice,
            date_diff('day', due_date, $asof)     AS days_past_due
  FROM invoices
  WHERE invoice_date <= $asof AND (paid_date IS NULL OR paid_date > $asof))
SELECT
  CASE WHEN days_from_invoice <= 30 THEN '1_30日以内' WHEN days_from_invoice <= 60 THEN '2_31〜60日'
       WHEN days_from_invoice <= 90 THEN '3_61〜90日' ELSE '4_90日超' END AS bucket_invoice,
  CASE WHEN days_past_due <= 0 THEN '0_期日前' WHEN days_past_due <= 30 THEN '1_30日以内' WHEN days_past_due <= 60 THEN '2_31〜60日'
       WHEN days_past_due <= 90 THEN '3_61〜90日' ELSE '4_90日超' END AS bucket_due,
  COUNT(*) AS n, SUM(amount) AS amount
FROM open_inv
GROUP BY 1, 2
ORDER BY 1, 2;
