-- 中の整合：既存店の売上は全店の売上を超えない（返品が多い月もあるので、正味の売上で比べる）
select r4.ym, r4.comp_sales, r1.sales
from {{ ref('rpt_r4_comp_store_yoy') }} r4
join {{ ref('rpt_r1_monthly_sales') }} r1 on r1.ym = r4.ym
where r4.comp_sales > r1.sales + 1e-6
