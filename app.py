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
from report_generator import compile_executive_report, format_rp, generate_docx

# --- FORMATTERS ---
def format_short_rp(value):
    try:
        is_neg = value < 0
        val = abs(value)
        if val >= 1e12:
            fmt = f"{val/1e12:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            res = f"Rp {fmt} Triliun"
        elif val >= 1e9:
            fmt = f"{val/1e9:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            res = f"Rp {fmt} Miliar"
        elif val >= 1e6:
            fmt = f"{val/1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            res = f"Rp {fmt} Juta"
        else:
            return format_rp(value)
        return f"-{res}" if is_neg else res
    except:
        return "Rp 0"

# --- CONFIG & STYLING ---
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
if 'docx_file' not in st.session_state: st.session_state.docx_file = None

with st.sidebar:
    st.markdown("### 🏛️ Panel Navigasi Data")
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.warning("⚠️ GROQ_API_KEY tidak ditemukan. AI dimatikan.")
        
    uploaded_file = st.file_uploader("📥 Upload File DIPA/Realisasi (.xlsx, .csv)", type=["xlsx", "csv"])
    
    if uploaded_file and st.session_state.raw_data is None:
        with st.spinner("Menganalisis skema struktur data..."):
            try:
                raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
                schema = detect_budget_schema(raw_df)
                cleaned_df = clean_and_prepare_data(raw_df, schema)
                
                st.session_state.raw_data = raw_df
                st.session_state.detected_schema = schema
                st.session_state.cleaned_data = cleaned_df
                st.session_state.core_metrics = compute_core_metrics(cleaned_df, schema)
                st.success("File berhasil diproses!")
            except Exception as e:
                st.error(f"Gagal memproses file: {str(e)}")

    if st.session_state.cleaned_data is not None:
        st.info(f"🧬 **Skema Terdeteksi**\nPagu: `{st.session_state.detected_schema['budget']}`\nBlokir: `{st.session_state.detected_schema['blocked']}`")
        if st.button("🔄 Reset Data Aplikasi"):
            for key in ['raw_data', 'cleaned_data', 'detected_schema', 'core_metrics', 'chat_history', 'docx_file']:
                st.session_state[key] = None
            st.rerun()

st.title("🏛️ Agen Intelijen Anggaran")

if st.session_state.cleaned_data is None:
    st.info("👋 **Selamat Datang.** Silakan unggah file Excel/CSV di panel kiri untuk memulai analisis otomatis.")
else:
    df = st.session_state.cleaned_data
    schema = st.session_state.detected_schema
    metrics = st.session_state.core_metrics
    
    forecast = run_forecasting_engine(metrics)
    bottlenecks = run_debottlenecking_engine(df, schema, metrics)
    anomalies = run_anomaly_detection(df, schema, metrics)
    
    # KARTU METRIK ATAS (Menggunakan format singkat agar tidak terpotong)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Pagu Alokasi", format_short_rp(metrics['total_budget']))
    c2.metric("Total Realisasi", format_short_rp(metrics['total_realization']), f"{metrics['absorption_rate']:.2f}% Terserap")
    c3.metric("Diblokir (Blokir)", format_short_rp(metrics['total_blocked']), f"{metrics['blocked_rate']:.2f}%", delta_color="inverse")
    c4.metric("Proyeksi Penyerapan", f"{forecast['forecast_absorption_rate']:.1f}%", f"Risiko Sisa: {format_short_rp(forecast['under_absorption'])}", delta_color="inverse")
        
    t_dash, t_chat, t_forecast, t_sim, t_rev, t_anomaly, t_bottleneck, t_report = st.tabs([
        "📊 Dashboard", "💬 Query Agent", "📈 Forecast", "🎛️ Simulation", "🧮 Reverse Math", "🚨 Anomalies", "⛓️ Bottlenecks", "📄 Report Generator"
    ])
    
    with t_dash:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**Profil Belanja Per Bulan (Realisasi)**")
            m_values = [metrics['monthly_totals'][m] for m in metrics['months_short']]
            fig_trend = go.Figure(go.Bar(x=metrics['months_short'], y=m_values, marker_color="#1e3a8a"))
            fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with col_right:
            st.markdown("**10 Entitas Anggaran Terbesar**")
            entity_col = schema['org'][1] if len(schema['org']) > 1 else (schema['org'][0] if schema['org'] else 'INDEX')
            top_alloc = df.groupby(entity_col)[schema['budget']].sum().reset_index().sort_values(by=schema['budget']).tail(10)
            fig_alloc = px.bar(top_alloc, x=schema['budget'], y=entity_col, orientation='h', color_discrete_sequence=["#0284c7"])
            fig_alloc.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig_alloc, use_container_width=True)

    with t_chat:
        engine = BudgetQueryEngine(df, schema, api_key)
        user_query = st.text_input("💬 Tanyakan pertanyaan strategis ke asisten AI:")
        if user_query:
            with st.spinner("Menerjemahkan ke SQL & Menjalankan LLM Llama 3..."):
                sql = engine.ask_llm_sql(user_query)
                st.code(sql, language="sql")
                res_df, error_msg = engine.execute_sql(sql)
                
                if error_msg:
                    st.error(f"Gagal menjalankan pencarian: {error_msg}")
                else:
                    # Tampilkan data dengan format angka rapi
                    styled_res = res_df.copy()
                    for c in styled_res.select_dtypes(include=['float', 'int']).columns:
                        styled_res[c] = styled_res[c].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "0")
                    st.dataframe(styled_res, use_container_width=True)
                    
                    st.info(engine.generate_narrative_insight(user_query, sql, res_df))

    with t_forecast:
        f_df = pd.DataFrame(forecast['forecast_trend'])
        fig_f = go.Figure()
        actuals = f_df[f_df['type'] == 'Actual']
        forecasts = f_df[f_df['type'] == 'Forecast']
        fig_f.add_trace(go.Scatter(x=actuals['month'], y=actuals['cumulative'], name='Aktual', line=dict(color='#1e3a8a', width=4)))
        if not forecasts.empty:
            full_track = pd.concat([actuals.tail(1), forecasts])
            fig_f.add_trace(go.Scatter(x=full_track['month'], y=full_track['cumulative'], name='Proyeksi Linear', line=dict(color='#f59e0b', dash='dash')))
        fig_f.add_trace(go.Scatter(x=f_df['month'], y=[metrics['total_budget']]*12, name='Pagu Maksimal', line=dict(color='#ef4444', dash='dot')))
        fig_f.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_f, use_container_width=True)

    with t_sim:
        sc_col1, sc_col2 = st.columns([1, 2])
        with sc_col1:
            spending_mult = st.slider("Simulasi Kenaikan/Penurunan Belanja (%)", 50, 200, 100) / 100.0
            target_abs = st.slider("Target Penyerapan (%)", 70, 100, 95)
            rel_block = st.checkbox("Simulasi Buka Blokir Anggaran")
        with sc_col2:
            sim_res = run_simulation_engine(metrics, spending_mult, target_abs, rel_block)
            st.metric("Simulasi Realisasi Akhir", format_rp(sim_res['sim_realization']), f"Total Serap: {sim_res['sim_absorption_rate']:.1f}%")
            st.metric("Dana Diperlukan untuk Target", format_rp(sim_res['required_realization_for_target']))

    with t_rev:
        tgt_pct = st.number_input("Target Persentase Penyerapan Akhir Tahun (%)", 1.0, 100.0, 95.0)
        rev_res = run_reverse_math_engine(metrics, tgt_pct)
        st.metric("Target Sisa Bulanan (Per Bulan)", format_rp(rev_res['required_monthly_spending']), f"Dihitung untuk sisa {rev_res['remaining_months']} bulan aktif")

    with t_anomaly:
        st.info("Algoritma mendeteksi anomali/keanehan pada baris di bawah ini:")
        anom_disp = anomalies[anomalies['IS_ANOMALOUS'] == True].sort_values(by=schema['budget'], ascending=False).copy()
        # Formatter agar angka enak dibaca
        for col in anom_disp.select_dtypes(include=['float', 'int']).columns:
            anom_disp[col] = anom_disp[col].apply(lambda x: f"{x:,.0f}")
        st.dataframe(anom_disp, use_container_width=True)

    with t_bottleneck:
        try:
            b_styled = bottlenecks.copy()
            # Terapkan format background gradient HANYA ke IMPACT SCORE, sisanya ubah ke teks format RP
            styled = b_styled.style.format(formatter={col: format_rp for col in b_styled.columns if 'RATE' not in col and 'SCORE' not in col and b_styled[col].dtype in ['float', 'int']})
            styled = styled.background_gradient(subset=['IMPACT_SCORE'], cmap='Reds')
            st.dataframe(styled, use_container_width=True)
        except ImportError:
            st.dataframe(bottlenecks, use_container_width=True)

    with t_report:
        if st.button("🚀 Buat Laporan Eksekutif Dokumen"):
            with st.spinner("AI Llama 3 sedang membaca analisis & membuat naskah laporan..."):
                b_str = bottlenecks.head(3)[[entity_col, schema['budget'], 'UNSPENT', 'ABSORPTION_RATE']].to_string()
                a_str = f"Defisit: {anomalies['ANOMALY_DEFICIT'].sum()}\nSpike: {anomalies['ANOMALY_SPIKE'].sum()}"
                
                advise = BudgetQueryEngine(df, schema, api_key).generate_recommendation_plan(b_str, a_str)
                st.session_state.chat_history = compile_executive_report(metrics, forecast, bottlenecks, anomalies, advise)
                st.session_state.docx_file = generate_docx(st.session_state.chat_history)
                
        if st.session_state.chat_history:
            dl_col1, dl_col2 = st.columns([1, 4])
            with dl_col1:
                st.download_button("💾 Unduh File .DOCX (Word)", data=st.session_state.docx_file, file_name="Laporan_Eksekutif_Anggaran.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            with dl_col2:
                # Tombol Copy (menggunakan trik Text Area jika Streamlit clipboard kurang stabil)
                st.info("👆 Laporan bisa diunduh langsung dalam bentuk Word (DOCX).")
                
            st.markdown(f'<div class="report-block">{st.session_state.chat_history}</div>', unsafe_allow_html=True)
