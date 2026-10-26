-- くらしの指標（1か月1行）。物価の前年同月比と、実質賃金の作り直しを入れる
with cpi as (
    select *,
        round(100 * (cpi_all / lag(cpi_all, 12) over (order by month) - 1), 1)             as cpi_all_yoy,
        round(100 * (cpi_core / lag(cpi_core, 12) over (order by month) - 1), 1)           as cpi_core_yoy,
        round(100 * (cpi_core_core / lag(cpi_core_core, 12) over (order by month) - 1), 1) as cpi_core_core_yoy,
        round(100 * (cpi_ex_rent / lag(cpi_ex_rent, 12) over (order by month) - 1), 1)     as cpi_ex_rent_yoy,
        round(100 * (cpi_energy / lag(cpi_energy, 12) over (order by month) - 1), 1)       as cpi_energy_yoy,
        round(100 * (cpi_food / lag(cpi_food, 12) over (order by month) - 1), 1)           as cpi_food_yoy
    from {{ ref('stg_cpi') }}
)
select
    c.month,
    c.cpi_all, c.cpi_core, c.cpi_ex_rent,
    c.cpi_all_yoy, c.cpi_core_yoy, c.cpi_core_core_yoy, c.cpi_ex_rent_yoy, c.cpi_energy_yoy, c.cpi_food_yoy,
    l.unemp_rate_sa, l.employed_sa_10k,
    j.jobs_ratio_sa,
    w.wage_total_idx, w.wage_total_yoy, w.wage_scheduled_yoy,
    w.real_wage_total_idx, w.real_wage_total_yoy,
    -- 実質賃金を自分で作り直す：名目賃金指数 ÷ 持家の帰属家賃を除く総合 × 100
    round(100 * w.wage_total_idx / c.cpi_ex_rent, 1) as real_wage_total_idx_rebuilt,
    -- 名目の伸び − 物価の伸び（近似）
    round(w.wage_total_yoy - c.cpi_ex_rent_yoy, 1) as real_wage_gap_approx
from cpi c
left join {{ ref('stg_lfs') }}  l using (month)
left join {{ ref('stg_jobs') }} j using (month)
left join {{ ref('stg_wage') }} w using (month)
