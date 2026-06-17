"""
Budget Intelligence Agent - Streamlit Production App Main Entrypoint
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from schema_detector import detect_budget_schema, clean_and_prepare_data
from analytics import (
    compute_core_metrics, run_forecasting_engine, run_simulation_engine,
    run_reverse_math_engine, run_anomaly_detection, run_debottlenecking_engine
)
from query_engine import BudgetQueryEngine
from report_generator import compile_executive_report

st.set_page_config(page_title="Budget Intelligence Agent", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #1f77b4; }
    div[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: bold; color: #1e3a8a; }
    .sidebar .sidebar-content { background-color: #1e293b; color: white; }
    h1, h2, h3 { color: #1e3a8a; }
    .report-block { background-color: #ffffff; padding: 25px; border-radius: 8px; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'cleaned_data' not in st.session_state: st.session_state.cleaned_data = None
if 'detected_schema' not in st.session_state: st.session_state.detected_schema = None
if 'core_metrics' not in st.session_state: st.session_state.core_metrics = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

with st.sidebar:
    st.markdown("### 🏛️ Governance Panel")
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.warning("⚠️ GROQ_API_KEY missing. Running in Offline Math Mode.")
        
    uploaded_file = st.file_uploader("📥 Upload Official DIPA Ledger (.xlsx)", type=["xlsx", "csv"])
    
    if uploaded_file and st.session_state.raw_data is None:
        with st.spinner("Analyzing schema..."):
            try:
                raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
                schema = detect_budget_schema(raw_df)
                cleaned_df = clean_and_prepare_data(raw_df, schema)
                
                st.session_state.raw_data = raw_df
                st.session_state.detected_schema = schema
                st.session_state.cleaned_data = cleaned_df
                st.session_state.core_metrics = compute_core_metrics(cleaned_df, schema)
                st.success("Ledger normalized.")
            except Exception as e:
                st.error(f"Ingest crash: {str(e)}")

    if st.session_state.cleaned_data is not None:
        st.info(f"🧬 **Schema Detected**\nCeiling: `{st.session_state.detected_schema['budget']}`\nBlocked: `{st.session_state.detected_schema['blocked']}`")
        if st.button("🔄 Reset Data"):
            for key in ['raw_data', 'cleaned_data', 'detected_schema', 'core_metrics']:
                st.session_state[key] = None
            st.session_state.chat_history = []
            st.rerun()

st.title("🏛️ Budget Intelligence Agent")

if st.session_state.cleaned_data is None:
    st.info("👋 **Welcome.** Please upload an excel format budget file via the sidebar to initiate.")
else:
    df = st.session_state.cleaned_data
    schema = st.session_state.detected_schema
    metrics = st.session_state.core_metrics
    
    forecast = run_forecasting_engine(metrics)
    bottlenecks = run_debottlenecking_engine(df, schema, metrics)
    anomalies = run_anomaly_detection(df, schema, metrics)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Budget (Pagu)", f"IDR {metrics['total_budget']:,.0f}")
    c2.metric("Total Realization", f"IDR {metrics['total_realization']:,.0f}", f"{metrics['absorption_rate']:.2f}%")
    c3.metric("Blocked (Blokir)", f"IDR {metrics['total_blocked']:,.0f}", f"{metrics['blocked_rate']:.2f}%", delta_color="inverse")
    c4.metric("Projected EOY Absorption", f"{forecast['forecast_absorption_rate']:.1f}%", f"Risk: {forecast['under_absorption']:,.0f}", delta_color="inverse")
        
    t_dash, t_chat, t_forecast, t_sim, t_rev, t_anomaly, t_bottleneck, t_report = st.tabs([
        "📊 Dashboard", "💬 Query Agent", "📈 Forecast", "🎛️ Simulation", "🧮 Reverse Math", "🚨 Anomalies", "⛓️ Bottlenecks", "📄 Report Generator"
    ])
    
    with t_dash:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**Monthly Spending Profiles**")
            m_values = [metrics['monthly_totals'][m] for m in metrics['months_short']]
            fig_trend = go.Figure(go.Bar(x=metrics['months_short'], y=m_values, marker_color="#1e3a8a"))
            fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with col_right:
            st.markdown("**Top 10 Allocations**")
            entity_col = schema['org'][1] if len(schema['org']) > 1 else (schema['org'][0] if schema['org'] else 'INDEX')
            top_alloc = df.groupby(entity_col)[schema['budget']].sum().reset_index().sort_values(by=schema['budget']).tail(10)
            fig_alloc = px.bar(top_alloc, x=schema['budget'], y=entity_col, orientation='h', color_discrete_sequence=["#0284c7"])
            fig_alloc.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig_alloc, use_container_width=True)

    with t_chat:
        engine = BudgetQueryEngine(df, schema, api_key)
        user_query = st.text_input("💬 Ask a strategic question:")
        if user_query:
            with st.spinner("Compiling SQL via Groq (Llama 3)..."):
                sql = engine.ask_llm_sql(user_query)
                st.code(sql, language="sql")
                res_df, error_msg = engine.execute_sql(sql)
                if error_msg:
                    st.error(f"Execution failed: {error_msg}")
                else:
                    st.dataframe(res_df, use_container_width=True)
                    st.info(engine.generate_narrative_insight(user_query, sql, res_df))

    with t_forecast:
        f_df = pd.DataFrame(forecast['forecast_trend'])
        fig_f = go.Figure()
        actuals = f_df[f_df['type'] == 'Actual']
        forecasts = f_df[f_df['type'] == 'Forecast']
        fig_f.add_trace(go.Scatter(x=actuals['month'], y=actuals['cumulative'], name='Actual', line=dict(color='#1e3a8a', width=4)))
        if not forecasts.empty:
            full_track = pd.concat([actuals.tail(1), forecasts])
            fig_f.add_trace(go.Scatter(x=full_track['month'], y=full_track['cumulative'], name='Forecast', line=dict(color='#f59e0b', dash='dash')))
        fig_f.add_trace(go.Scatter(x=f_df['month'], y=[metrics['total_budget']]*12, name='Ceiling', line=dict(color='#ef4444', dash='dot')))
        fig_f.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_f, use_container_width=True)

    with t_sim:
        sc_col1, sc_col2 = st.columns([1, 2])
        with sc_col1:
            spending_mult = st.slider("Spending Level (%)", 50, 200, 100) / 100.0
            target_abs = st.slider("Target Absorption (%)", 70, 100, 95)
            rel_block = st.checkbox("Release Blocked Funds")
        with sc_col2:
            sim_res = run_simulation_engine(metrics, spending_mult, target_abs, rel_block)
            st.metric("Simulated Realization", f"IDR {sim_res['sim_realization']:,.0f}", f"Absorbed: {sim_res['sim_absorption_rate']:.1f}%")
            st.metric("Required to Hit Target", f"IDR {sim_res['required_realization_for_target']:,.0f}")

    with t_rev:
        tgt_pct = st.number_input("Target Year-End Absorption (%)", 1.0, 100.0, 95.0)
        rev_res = run_reverse_math_engine(metrics, tgt_pct)
        st.metric("Required Monthly Spending", f"IDR {rev_res['required_monthly_spending']:,.0f}", f"For remaining {rev_res['remaining_months']} months")

    with t_anomaly:
        st.dataframe(anomalies[anomalies['IS_ANOMALOUS'] == True].sort_values(by=schema['budget'], ascending=False), use_container_width=True)

    with t_bottleneck:
        st.dataframe(bottlenecks.style.background_gradient(subset=['IMPACT_SCORE'], cmap='Reds'), use_container_width=True)

    with t_report:
        if st.button("🚀 Generate Executive Brief"):
            with st.spinner("Generating Report via Groq..."):
                b_str = bottlenecks.head(3)[[entity_col, schema['budget'], 'UNSPENT', 'ABSORPTION_RATE']].to_string()
                a_str = f"Deficits: {anomalies['ANOMALY_DEFICIT'].sum()}\nSpikes: {anomalies['ANOMALY_SPIKE'].sum()}"
                advise = BudgetQueryEngine(df, schema, api_key).generate_recommendation_plan(b_str, a_str)
                st.session_state.chat_history = compile_executive_report(metrics, forecast, bottlenecks, anomalies, advise)
                
        if st.session_state.chat_history:
            st.download_button("💾 Download Report", st.session_state.chat_history, "REPORT.md", "text/markdown")
            st.markdown(f'<div class="report-block">{st.session_state.chat_history}</div>', unsafe_allow_html=True)
