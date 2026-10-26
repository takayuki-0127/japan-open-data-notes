select
    month,
    max(case when series = 'unemp_rate_sa'   then value end) as unemp_rate_sa,
    max(case when series = 'employed_sa'     then value end) as employed_sa_10k,
    max(case when series = 'labour_force_sa' then value end) as labour_force_sa_10k,
    max(case when series = 'unemployed_sa'   then value end) as unemployed_sa_10k
from {{ source('raw', 'raw_lfs') }}
group by month
