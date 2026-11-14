-- 店×月の売上と、前年同月の売上、既存店かどうか（定義は models/docs.md の def_comp_store）
with sm as (
    select d.ym, d.mi, f.store_id, sum(f.amt) as sales
    from {{ ref('fct_sales_net') }} f
    join {{ ref('dim_date') }} d on d.date_key = f.date_key
    group by d.ym, d.mi, f.store_id
)
select
    a.ym, a.mi, a.store_id, a.sales,
    b.sales as sales_ly,
    s.open_mi <= a.mi - {{ var('comp_store_min_months') }} as is_comp
from sm a
join {{ ref('dim_store') }} s on s.store_id = a.store_id
left join sm b on b.store_id = a.store_id and b.mi = a.mi - 12
