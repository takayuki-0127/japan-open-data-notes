select
    cast(receipt_id as bigint)  as receipt_id,
    cast(line_no as integer)    as line_no,
    cast(date_key as integer)   as date_key,
    cast(store_id as integer)   as store_id,
    cast(item_id as integer)    as item_id,
    cast(amount_incl as double) as amount_incl,
    cast(tax_pct as integer)    as tax_pct,
    cast(status as varchar)     as status
from {{ source('raw', 'sales_line') }}
where cast(date_key as integer) <= {{ var('load_until') }}
