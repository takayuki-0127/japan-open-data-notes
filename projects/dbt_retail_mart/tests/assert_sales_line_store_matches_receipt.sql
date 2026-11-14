-- 明細の店と日付は、レシートの店と日付と同じ
select l.receipt_id, l.line_no
from {{ ref('stg_sales_line') }} l
join {{ ref('stg_receipt') }} r on r.receipt_id = l.receipt_id
where l.store_id <> r.store_id or l.date_key <> r.date_key
