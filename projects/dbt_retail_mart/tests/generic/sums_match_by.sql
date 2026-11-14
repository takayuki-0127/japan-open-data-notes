{#- 照合：このモデルの列の合計（group_by ごと）が、もう1つのモデルの合計と一致するか -#}
{% test sums_match_by(model, column_name, compare_model, compare_column, group_by, rel_tol=1e-9) %}
with a as (select {{ group_by }} as g, sum({{ column_name }}) as v from {{ model }} group by 1),
     b as (select {{ group_by }} as g, sum({{ compare_column }}) as v from {{ compare_model }} group by 1)
select coalesce(a.g, b.g) as g, a.v as this_total, b.v as compare_total
from a full outer join b on a.g = b.g
where a.v is null or b.v is null or abs(a.v - b.v) > {{ rel_tol }} * greatest(1.0, abs(b.v))
{% endtest %}
