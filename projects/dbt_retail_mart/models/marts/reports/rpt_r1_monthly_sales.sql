-- R1 全社の月次売上
select d.ym, sum(f.amt) as sales
from {{ ref('fct_sales_net') }} f
join {{ ref('dim_date') }} d on d.date_key = f.date_key
group by d.ym
