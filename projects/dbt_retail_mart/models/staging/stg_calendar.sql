select
    cast(date_key as integer) as date_key,
    cast(cal_ym as integer)   as cal_ym,
    cast(cal_mi as integer)   as cal_mi,
    cast(fis_ym as integer)   as fis_ym,
    cast(fis_mi as integer)   as fis_mi
from {{ source('raw', 'calendar') }}
