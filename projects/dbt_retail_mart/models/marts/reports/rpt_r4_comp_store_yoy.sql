-- R4 既存店の前年比（その月に既存店で、前年同月の売上がある店だけ）
select ym,
       sum(sales) as comp_sales,
       sum(sales_ly) as comp_sales_ly,
       sum(sales) / sum(sales_ly) - 1 as yoy
from {{ ref('fct_store_month_sales') }}
where is_comp and sales_ly is not null
group by ym
