-- R2 店舗別の月次売上
select ym, store_id, sales
from {{ ref('fct_store_month_sales') }}
