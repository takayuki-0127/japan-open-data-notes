-- 照合：R8（直近月の日別）の合計は、R1 の直近月の売上と一致する
select r1.ym, r1.sales, sum(r8.sales) as daily_total
from {{ ref('rpt_r8_latest_month_daily') }} r8
cross join (select ym, sales from {{ ref('rpt_r1_monthly_sales') }} order by ym desc limit 1) r1
group by r1.ym, r1.sales
having abs(sum(r8.sales) - r1.sales) > 1e-9 * greatest(1, abs(r1.sales))
