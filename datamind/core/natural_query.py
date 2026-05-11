from datetime import datetime, timedelta

QUERY_TEMPLATES = [
    {
        "patterns": ["销售", "营收", "收入", "revenue", "卖了"],
        "sql": (
            "SELECT order_date, total_revenue, order_count "
            "FROM app_daily_revenue ORDER BY order_date DESC LIMIT 30"
        ),
        "chart": "line",
    },
    {
        "patterns": ["月度", "每月", "月报", "monthly"],
        "sql": (
            "SELECT order_month, total_revenue, order_count, unique_customers "
            "FROM fct_monthly_kpi ORDER BY order_month DESC LIMIT 12"
        ),
        "chart": "bar",
    },
    {
        "patterns": ["客户", "用户", "customer", "segment"],
        "sql": (
            "SELECT customer_segment, COUNT(*) AS count, SUM(total_spent) AS total_spent "
            "FROM app_customer_segments GROUP BY customer_segment ORDER BY total_spent DESC"
        ),
        "chart": "pie",
    },
    {
        "patterns": ["增长", "趋势", "growth", "trend"],
        "sql": (
            "SELECT order_date, total_revenue, dod_growth_pct "
            "FROM app_daily_revenue WHERE dod_growth_pct IS NOT NULL "
            "ORDER BY order_date DESC LIMIT 30"
        ),
        "chart": "line",
    },
    {
        "patterns": ["地区", "城市", "region", "state", "city"],
        "sql": (
            "SELECT customer_state, COUNT(*) AS order_count, SUM(total_spent) AS total_spent "
            "FROM app_customer_segments GROUP BY customer_state "
            "ORDER BY total_spent DESC LIMIT 10"
        ),
        "chart": "bar",
    },
]


class TemplateMatcher:
    def match(self, question: str) -> dict | None:
        question_lower = question.lower()
        for template in QUERY_TEMPLATES:
            for pattern in template["patterns"]:
                if pattern in question_lower:
                    sql = template["sql"]
                    sql = self._apply_time_filters(sql, question_lower)
                    return {"sql": sql, "chart": template["chart"]}
        return None

    def _apply_time_filters(self, sql: str, question: str) -> str:
        today = datetime.now()

        if any(w in question for w in ["今天", "today"]):
            date_filter = f"order_date = '{today.strftime('%Y-%m-%d')}'"
        elif any(w in question for w in ["昨天", "yesterday"]):
            yesterday = today - timedelta(days=1)
            date_filter = f"order_date = '{yesterday.strftime('%Y-%m-%d')}'"
        elif any(w in question for w in ["本周", "this week"]):
            start = today - timedelta(days=today.weekday())
            date_filter = f"order_date >= '{start.strftime('%Y-%m-%d')}'"
        elif any(w in question for w in ["本月", "this month"]):
            start = today.replace(day=1)
            date_filter = f"order_date >= '{start.strftime('%Y-%m-%d')}'"
        elif any(w in question for w in ["上月", "last month"]):
            start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            end = today.replace(day=1) - timedelta(days=1)
            date_filter = (
                f"order_date >= '{start.strftime('%Y-%m-%d')}' "
                f"AND order_date <= '{end.strftime('%Y-%m-%d')}'"
            )
        else:
            return sql

        if "WHERE" in sql.upper():
            sql = sql.replace("WHERE", f"WHERE {date_filter} AND", 1)
        elif "ORDER BY" in sql.upper():
            sql = sql.replace("ORDER BY", f"WHERE {date_filter} ORDER BY", 1)
        elif "LIMIT" in sql.upper():
            sql = sql.replace("LIMIT", f"WHERE {date_filter} LIMIT", 1)

        return sql
