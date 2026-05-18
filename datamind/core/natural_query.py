import re
from datetime import datetime, timedelta

_SAFE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

QUERY_TEMPLATES = [
    {
        "patterns": ["销售", "营收", "收入", "revenue", "卖了"],
        "sql": (
            "SELECT order_date, total_revenue, order_count "
            "FROM app_daily_revenue ORDER BY order_date DESC LIMIT 30"
        ),
        "chart": "line",
        "table": "app_daily_revenue",
    },
    {
        "patterns": ["月度", "每月", "月报", "monthly"],
        "sql": (
            "SELECT order_month, total_revenue, order_count, unique_customers "
            "FROM fct_monthly_kpi ORDER BY order_month DESC LIMIT 12"
        ),
        "chart": "bar",
        "table": "fct_monthly_kpi",
    },
    {
        "patterns": ["客户", "用户", "customer", "segment"],
        "sql": (
            "SELECT customer_segment, COUNT(*) AS count, SUM(total_spent) AS total_spent "
            "FROM app_customer_segments GROUP BY customer_segment ORDER BY total_spent DESC"
        ),
        "chart": "pie",
        "table": "app_customer_segments",
    },
    {
        "patterns": ["增长", "趋势", "growth", "trend"],
        "sql": (
            "SELECT order_date, total_revenue, dod_growth_pct "
            "FROM app_daily_revenue WHERE dod_growth_pct IS NOT NULL "
            "ORDER BY order_date DESC LIMIT 30"
        ),
        "chart": "line",
        "table": "app_daily_revenue",
    },
    {
        "patterns": ["地区", "城市", "region", "state", "city"],
        "sql": (
            "SELECT customer_state, COUNT(*) AS order_count, SUM(total_spent) AS total_spent "
            "FROM app_customer_segments GROUP BY customer_state "
            "ORDER BY total_spent DESC LIMIT 10"
        ),
        "chart": "bar",
        "table": "app_customer_segments",
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
                    return {"sql": sql, "chart": template["chart"], "table": template["table"]}
        return None

    @staticmethod
    def _format_date(dt: datetime) -> str:
        formatted = dt.strftime("%Y-%m-%d")
        if not _SAFE_DATE.match(formatted):
            raise ValueError(f"Invalid date generated: {formatted}")
        return formatted

    def _apply_time_filters(self, sql: str, question: str) -> str:
        today = datetime.now()

        if any(w in question for w in ["今天", "today"]):
            date_filter = f"order_date = '{self._format_date(today)}'"
        elif any(w in question for w in ["昨天", "yesterday"]):
            yesterday = today - timedelta(days=1)
            date_filter = f"order_date = '{self._format_date(yesterday)}'"
        elif any(w in question for w in ["本周", "this week"]):
            start = today - timedelta(days=today.weekday())
            date_filter = f"order_date >= '{self._format_date(start)}'"
        elif any(w in question for w in ["本月", "this month"]):
            start = today.replace(day=1)
            date_filter = f"order_date >= '{self._format_date(start)}'"
        elif any(w in question for w in ["上月", "last month"]):
            start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            end = today.replace(day=1) - timedelta(days=1)
            date_filter = (
                f"order_date >= '{self._format_date(start)}' "
                f"AND order_date <= '{self._format_date(end)}'"
            )
        else:
            return sql

        sql_upper = sql.upper()
        if "WHERE" in sql_upper:
            where_pos = sql_upper.index("WHERE")
            insert_pos = where_pos + len("WHERE")
            sql = sql[:insert_pos] + f" {date_filter} AND" + sql[insert_pos:]
        elif "ORDER BY" in sql_upper:
            order_pos = sql_upper.index("ORDER BY")
            sql = sql[:order_pos] + f"WHERE {date_filter} " + sql[order_pos:]
        elif "LIMIT" in sql_upper:
            limit_pos = sql_upper.index("LIMIT")
            sql = sql[:limit_pos] + f"WHERE {date_filter} " + sql[limit_pos:]

        return sql
