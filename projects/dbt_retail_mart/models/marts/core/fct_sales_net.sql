-- 売上と返品の明細（1行＝1明細の売上、または1明細の返品）。金額は返品をマイナスにした正味
select
    receipt_id, line_no, kind,
    date_key, store_id, item_id, amt
from {{ ref('int_net_sales') }}
