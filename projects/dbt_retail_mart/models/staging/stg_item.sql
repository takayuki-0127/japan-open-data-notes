select cast(item_id as integer) as item_id, cast(dept_id as integer) as dept_id
from {{ source('raw', 'item') }}
