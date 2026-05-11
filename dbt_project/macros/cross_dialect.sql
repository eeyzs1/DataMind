{% macro date_sub(date_expr, days) %}
    {% if target.type == 'duckdb' %}
        {{ date_expr }} - INTERVAL '{{ days }}' DAY
    {% elif target.type == 'spark' %}
        DATE_SUB({{ date_expr }}, {{ days }})
    {% else %}
        {{ date_expr }} - INTERVAL '{{ days }}' DAY
    {% endif %}
{% endmacro %}

{% macro date_trunc(unit, date_expr) %}
    {% if target.type == 'duckdb' %}
        DATE_TRUNC('{{ unit }}', {{ date_expr }})
    {% elif target.type == 'spark' %}
        TRUNC({{ date_expr }}, '{{ unit }}')
    {% else %}
        DATE_TRUNC('{{ unit }}', {{ date_expr }})
    {% endif %}
{% endmacro %}

{% macro current_timestamp() %}
    {% if target.type == 'duckdb' %}
        CURRENT_TIMESTAMP
    {% elif target.type == 'spark' %}
        CURRENT_TIMESTAMP()
    {% else %}
        CURRENT_TIMESTAMP
    {% endif %}
{% endmacro %}
