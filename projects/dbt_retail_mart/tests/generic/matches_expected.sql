{#- 答え合わせ：モデルの結果が、pandas で別に計算した期待値（seed）と一致するか。
    どちらかにしかない行、または値の差が許容を超える行を返す -#}
{% test matches_expected(model, expected, keys, value_columns, rel_tol=1e-9) %}
{{ config(enabled=is_base_config()) }}
select
    {% for k in keys %}coalesce(m.{{ k }}, e.{{ k }}) as {{ k }}, {% endfor %}
    {% for c in value_columns %}m.{{ c }} as model_{{ c }}, e.{{ c }} as expected_{{ c }}{% if not loop.last %}, {% endif %}{% endfor %}
from {{ model }} m
full outer join {{ ref(expected) }} e
  on {% for k in keys %}m.{{ k }} = e.{{ k }}{% if not loop.last %} and {% endif %}{% endfor %}
where {% for k in keys %}m.{{ k }} is null or e.{{ k }} is null or {% endfor %}
      {% for c in value_columns %}
      (m.{{ c }} is distinct from e.{{ c }} and (m.{{ c }} is null or e.{{ c }} is null
        or abs(m.{{ c }} - e.{{ c }}) > {{ rel_tol }} * greatest(1.0, abs(e.{{ c }}))))
      {% if not loop.last %} or {% endif %}{% endfor %}
{% endtest %}
