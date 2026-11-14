-- R8 直近月の日別売上
with f as (
    select f.date_key, d.ym, f.amt
    from {{ ref('fct_sales_net') }} f
    join {{ ref('dim_date') }} d on d.date_key = f.date_key
)
select date_key, sum(amt) as sales
from f
where ym = (select max(ym) from f)
group by date_key
