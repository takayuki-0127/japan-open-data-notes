select
    cast(receipt_id as bigint) as receipt_id,
    cast(date_key as integer)  as date_key,
    cast(store_id as integer)  as store_id,
    cast(member_id as bigint)  as member_id   -- 約4割は NULL（会員カードなし）
from {{ source('raw', 'receipt') }}
where cast(date_key as integer) <= {{ var('load_until') }}
