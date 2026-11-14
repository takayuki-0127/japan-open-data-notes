-- R5 客数と客単価
with c as (
    select d.ym, count(distinct v.cust_key) as customers
    from {{ ref('fct_customer_visit') }} v
    join {{ ref('dim_date') }} d on d.date_key = v.date_key
    group by d.ym
)
select s.ym, s.sales, c.customers, s.sales / c.customers as ticket
from {{ ref('rpt_r1_monthly_sales') }} s
join c on c.ym = s.ym
