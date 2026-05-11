import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="DataMind Demo", layout="wide", page_icon="🧠")

st.title("🧠 DataMind 弹性大数据平台 Demo")
st.caption("采集 → 加工 → 分发 | 同一套代码，从笔记本到集群")

tab_ingest, tab_etl, tab_export, tab_query, tab_govern = st.tabs([
    "📥 数据采集", "⚙️ ETL加工", "📤 数据分发", "🔍 智能查询", "🛡️ 数据治理"
])

with tab_ingest:
    st.header("批量数据采集")
    st.markdown("从外部数据源大批量采集数据入库")

    if st.button("🚀 执行数据采集", type="primary"):
        with st.spinner("采集中..."):
            from datamind.core.factory import get_ingestion, get_storage
            import yaml
            from pathlib import Path

            config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
            with open(config_path) as f:
                sources_config = yaml.safe_load(f)

            ingestion = get_ingestion()
            storage = get_storage()

            results = []
            for source in sources_config["sources"]:
                try:
                    ing_id = ingestion.ingest_batch(source)
                    status = ingestion.get_status(ing_id)
                    results.append({
                        "数据源": source["name"],
                        "状态": "✅ 成功",
                        "行数": status.get("rows", 0),
                        "大小(KB)": round(status.get("size_bytes", 0) / 1024, 1),
                    })
                except Exception as e:
                    results.append({
                        "数据源": source["name"],
                        "状态": f"❌ 失败: {e}",
                        "行数": 0,
                        "大小(KB)": 0,
                    })

            st.dataframe(pd.DataFrame(results), use_container_width=True)

    st.divider()
    st.subheader("Raw Zone 数据概览")
    try:
        from datamind.core.factory import get_storage
        storage = get_storage()
        tables = storage.list_tables("raw")
        if tables:
            for t in tables:
                size = storage.get_size(f"raw/{t}")
                st.markdown(f"- **{t}** ({round(size/1024, 1)} KB)")
        else:
            st.info("Raw Zone 为空，请先执行数据采集")
    except Exception:
        st.info("Raw Zone 为空，请先执行数据采集")

with tab_etl:
    st.header("5层ETL加工")
    st.markdown("Raw → Cleaned → Detail → Summary → App")

    layers = [
        ("Raw", "原始数据，原样保存", "raw"),
        ("Cleaned", "格式统一、类型正确、空值处理", "cleaned"),
        ("Detail", "维度关联、业务解码、去重", "detail"),
        ("Summary", "聚合指标、口径统一", "summary"),
        ("App", "面向业务主题，直接可用", "app"),
    ]

    for name, desc, zone in layers:
        with st.expander(f"📦 {name}层 — {desc}"):
            try:
                from datamind.core.factory import get_storage
                storage = get_storage()
                tables = storage.list_tables(zone)
                if tables:
                    for t in tables:
                        st.markdown(f"- `{t}`")
                else:
                    st.caption("（空）")
            except Exception:
                st.caption("（空）")

    if st.button("⚙️ 运行dbt ETL", type="primary"):
        with st.spinner("ETL运行中..."):
            import subprocess
            from pathlib import Path
            dbt_dir = str(Path(__file__).parent.parent / "dbt_project")
            result = subprocess.run(
                ["dbt", "run", "--project-dir", dbt_dir],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                st.success("ETL运行成功！")
                st.code(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            else:
                st.error("ETL运行失败")
                st.code(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)

with tab_export:
    st.header("批量数据分发")
    st.markdown("将加工后的数据导出给消费者")

    col1, col2 = st.columns(2)
    with col1:
        export_format = st.selectbox("导出格式", ["parquet", "csv"])
        export_source = st.selectbox("数据源", [
            "app/app_daily_revenue",
            "app/app_customer_segments",
        ])
    with col2:
        export_target = st.text_input("目标路径", f"exports/{export_source.split('/')[-1]}")

    if st.button("📤 执行导出", type="primary"):
        with st.spinner("导出中..."):
            from datamind.core.factory import get_export
            export = get_export()
            export_id = export.export_file(export_source, {
                "format": export_format,
                "target": "file",
                "target_path": export_target,
            })
            st.success(f"导出完成！export_id={export_id}")

    st.divider()
    st.subheader("导出历史")
    try:
        from datamind.core.factory import get_export
        export = get_export()
        exports = export.list_exports()
        if exports:
            st.dataframe(pd.DataFrame(exports), use_container_width=True)
        else:
            st.info("暂无导出记录")
    except Exception:
        st.info("暂无导出记录")

with tab_query:
    st.header("智能查询")
    question = st.text_input("输入问题（支持中文）：", placeholder="例：最近30天的销售趋势")

    if question:
        from datamind.core.natural_query import TemplateMatcher
        matcher = TemplateMatcher()
        result = matcher.match(question)
        if result:
            st.code(f"SQL: {result['sql']}", language="sql")
            try:
                from datamind.core.factory import get_compute, get_storage
                compute = get_compute()
                storage = get_storage()
                for zone in ("summary", "app", "detail"):
                    for t in storage.list_tables(zone):
                        compute.register_table(t, storage.data_path(f"{zone}/{t}"))
                df = compute.execute(result["sql"])
                st.dataframe(df, use_container_width=True)
                chart_type = result["chart"]
                if chart_type == "line" and len(df) > 1:
                    st.line_chart(df)
                elif chart_type == "bar" and len(df) > 1:
                    st.bar_chart(df)
            except Exception as e:
                st.error(f"查询失败: {e}")
        else:
            st.warning("未找到匹配的查询模板，请尝试：销售/营收/月度/客户/增长/地区")

with tab_govern:
    st.header("数据治理")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("质量评分")
        try:
            from datamind.core.factory import get_metadata
            metadata = get_metadata()
            tables = metadata.list_tables()
            scores = []
            for t in tables:
                score = metadata.get_quality_score(t["name"])
                scores.append(score)
            if scores:
                st.dataframe(pd.DataFrame(scores), use_container_width=True)
            else:
                st.info("暂无质量评分数据")
        except Exception:
            st.info("暂无质量评分数据")

    with col2:
        st.subheader("血缘追踪")
        table_name = st.text_input("输入表名查看血缘：", placeholder="app_daily_revenue")
        if table_name:
            try:
                from datamind.core.factory import get_metadata
                metadata = get_metadata()
                upstream = metadata.get_lineage(table_name, "upstream")
                downstream = metadata.get_lineage(table_name, "downstream")
                if upstream:
                    st.markdown("**上游依赖：**")
                    for l in upstream:
                        st.markdown(f"- `{l['source']}` → `{l['target']}`")
                if downstream:
                    st.markdown("**下游影响：**")
                    for l in downstream:
                        st.markdown(f"- `{l['source']}` → `{l['target']}`")
                if not upstream and not downstream:
                    st.info("暂无血缘数据")
            except Exception:
                st.info("暂无血缘数据")
