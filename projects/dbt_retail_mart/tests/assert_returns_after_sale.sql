-- 返品は、元の売上の日より前に来ない。金額は元の売上の金額を超えない
select r.receipt_id, r.line_no, r.return_date_key, l.date_key, r.amount_incl, l.amount_incl as sale_amount
from {{ ref('stg_returns_line') }} r
left join {{ ref('stg_sales_line') }} l on l.receipt_id = r.receipt_id and l.line_no = r.line_no
where l.receipt_id is null or r.return_date_key < l.date_key or r.amount_incl > l.amount_incl
