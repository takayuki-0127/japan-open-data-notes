-- 自分で作り直した実質賃金指数が、公表の実質賃金指数と 0.15 ポイント以内で一致するか
-- （2020年=100 の同じ基準になった 2020年1月以降で確かめる。外れた月があれば失敗）
select month, real_wage_total_idx, real_wage_total_idx_rebuilt
from {{ ref('mart_indicators_monthly') }}
where month >= date '2020-01-01'
  and real_wage_total_idx is not null
  and abs(real_wage_total_idx - real_wage_total_idx_rebuilt) > 0.15
