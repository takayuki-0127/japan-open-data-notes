-- R6 店舗×部門グループの月次売上
select d.ym, f.store_id, i.dept_grp as grp, sum(f.amt) as sales
from {{ ref('fct_sales_net') }} f
join {{ ref('dim_date') }} d on d.date_key = f.date_key
join {{ ref('dim_item') }} i on i.item_id = f.item_id
group by d.ym, f.store_id, i.dept_grp
