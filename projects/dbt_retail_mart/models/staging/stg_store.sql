select
    cast(store_id as integer)      as store_id,
    cast(open_date_key as integer) as open_date_key,
    cast(is_test as integer) = 1   as is_test
from {{ source('raw', 'store') }}
