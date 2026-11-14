-- 商品の次元。部門グループは vars の dept_group_version に従う
select i.item_id, i.dept_id, d.dept_name, {{ dept_group('i.dept_id') }} as dept_grp
from {{ ref('stg_item') }} i
join {{ ref('stg_dept') }} d on d.dept_id = i.dept_id
