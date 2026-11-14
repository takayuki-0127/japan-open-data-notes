select
    cast(receipt_id as bigint)      as receipt_id,
    cast(line_no as integer)        as line_no,
    cast(return_date_key as integer) as return_date_key,
    cast(amount_incl as double)     as amount_incl
from {{ source('raw', 'returns_line') }}
where cast(return_date_key as integer) <= {{ var('load_until') }}
