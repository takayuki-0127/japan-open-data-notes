-- R7 KPI のまとめ
select r5.ym, r5.sales, r5.customers, r5.ticket, r4.yoy as comp_yoy
from {{ ref('rpt_r5_customers_ticket') }} r5
left join {{ ref('rpt_r4_comp_store_yoy') }} r4 on r4.ym = r5.ym
