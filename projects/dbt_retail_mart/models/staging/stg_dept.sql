select cast(dept_id as integer) as dept_id, cast(dept_name as varchar) as dept_name
from {{ source('raw', 'dept') }}
