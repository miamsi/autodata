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

# --- FORMATTERS AKUNTANSI INDONESIA ---
def format_short_rp(value):
    try:
        if pd.isna(value): return "Rp 0"
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
    .report-block { background-color: #ffffff; padding: 25px; border-radius: 8px; border: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# Inisialisasi State Aplikasi
if 'raw_data' not in st.session_state: st.session_state.raw_data = None
if 'cleaned_data' not in st.session_state: st.session_state.cleaned_data = None
if 'detected_schema' not in st.session_state: st.session_state.detected_schema = None
if 'core_metrics' not in st.session_state: st.session_state.core_metrics = None
if 'executive_report' not in st.session_state: st.session_state.executive_report = None
if 'docx_file' not in st.session_state: st.session_state.docx_file = None
if 'agent_chat_history' not in st.session_state: st.session_state.agent_chat_history = []

with st.sidebar:
    st.markdown("### 🏛️ Navigasi Logistik Data")
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.warning("⚠️ GROQ_API_KEY tidak terdeteksi. Fitur pintar LLM dinonaktifkan.")
        
    uploaded_file = st.file_uploader("📥 Unggah Berkas Transaksi DIPA (.xlsx, .csv)", type=["xlsx", "csv"])
    
    if uploaded_file and st.session_state.raw_data is None:
        with st.spinner("Menjalankan Otomatisasi Penyelarasan Skema Data..."):
            try:
                raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
                schema = detect_budget_schema(raw_df)
                cleaned_df = clean_and_prepare_data(raw_df, schema)
                
                st.session_state.raw_data = raw_df
                st.session_state.detected_schema = schema
                st.session_state.cleaned_data = cleaned_df
                st.session_state.core_metrics = compute_core_metrics(cleaned_df, schema)
                st.success("Data engineered successfully!")
            except Exception as e:
                st.error(f"Kesalahan Ingest Data: {str(e)}")

    if st.session_state.cleaned_data is not None:
        st.info(f"🧬 **Skema Hasil Sinkronisasi**\nPagu: `{st.session_state.detected_schema['budget']}`\nAkun Akun: `{st.session_state.detected_schema['account_code']}`")
        if st.button("🔄 Bersihkan Sesi & Reset"):
            for key in ['raw_data', 'cleaned_data', 'detected_schema', 'core_metrics', 'executive_report', 'docx_file', 'agent_chat_history']:
                st.session_state[key] = None
            st.rerun()

st.title("🏛️ Budget Intelligence Agent")

if st.session_state.cleaned_data is None:
    st.info("👋 **Sistem Siap.** Silakan unggah berkas excel/csv laporan keuangan anggaran kerja Anda pada panel kiri.")
else:
    df = st.session_state.cleaned_data
    schema = st.session_state.detected_schema
    metrics = st.session_state.core_metrics
    
    forecast = run_forecasting_engine(metrics)
    bottlenecks = run_debottlenecking_engine(df, schema, metrics)
    anomalies = run_anomaly_detection(df, schema, metrics)
    
    # KARTU INDIKATOR UTAMA (Menggunakan format Rupiah Singkat agar tidak terpotong layout)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Pagu Alokasi", format_short_rp(metrics['total_budget']))
    c2.metric("Total Realisasi YTD", format_short_rp(metrics['total_realization']), f"{metrics['absorption_rate']:.2f}% Penyerapan")
    c3.metric("Pagu Blokir Berjalan", format_short_rp(metrics['total_blocked']), f"{metrics['blocked_rate']:.2f}% Terkunci", delta_color="inverse")
    c4.metric("Proyeksi Sisa Belanja", format_short_rp(forecast['under_absorption']), f"Target Akhir EOY: {forecast['forecast_absorption_rate']:.1f}%", delta_color="inverse")
        
    t_dash, t_chat, t_forecast, t_sim, t_rev, t_anomaly, t_bottleneck, t_report = st.tabs([
        "📊 Dashboard", "💬 Conversational Agent", "📈 Peramalan", "🎛️ Simulasi Skenario", "🧮 Kalkulator Target", "🚨 Analisis Anomali", "⛓️ Manajemen Bottleneck", "📄 Naskah Ringkasan"
    ])
    
    with t_dash:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**Grafik Tren Realisasi Bulanan Korporasi**")
            m_values = [metrics['monthly_totals'][m] for m in metrics['months_short']]
            fig_trend = go.Figure(go.Bar(x=metrics['months_short'], y=m_values, marker_color="#1e3a8a"))
            fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with col_right:
            st.markdown("**Komposisi Pagu Alokasi per Jenis Belanja**")
            top_jenis = df.groupby('JENIS_BELANJA')['PAGU_EFEKTIF'].sum().reset_index()
            fig_alloc = px.pie(top_jenis, values='PAGU_EFEKTIF', names='JENIS_BELANJA', color_discrete_sequence=px.colors.sequential.RdBu)
            fig_alloc.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig_alloc, use_container_width=True)

    with t_chat:
        st.subheader("💬 Asisten Cerdas Intelijen Anggaran (Chat Style)")
        engine = BudgetQueryEngine(df, schema, api_key)
        
        # Render riwayat percakapan yang tersimpan dalam session state
        for message in st.session_state.agent_chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "df_result" in message:
                    st.dataframe(message["df_result"], use_container_width=True)
                if "chart_config" in message and message["chart_config"]:
                    cfg = message["chart_config"]
                    try:
                        if cfg["chart_type"] == "bar":
                            fig = px.bar(message["df_result"], x=cfg["x"], y=cfg["y"], color=cfg.get("color"), title=cfg["title"], orientation=cfg.get("orientation", "v"))
                        elif cfg["chart_type"] == "line":
                            fig = px.line(message["df_result"], x=cfg["x"], y=cfg["y"], color=cfg.get("color"), title=cfg["title"])
                        elif cfg["chart_type"] == "pie":
                            fig = px.pie(message["df_result"], values=cfg["y"], names=cfg["x"], title=cfg["title"])
                        st.plotly_chart(fig, use_container_width=True)
                    except:
                        pass

        # Input interaksi chat baru
        if user_prompt := st.chat_input("Tanyakan sesuatu (Contoh: 'Tampilkan total realisasi efektif per jenis belanja')"):
            with st.chat_message("user"):
                st.markdown(user_prompt)
            st.session_state.agent_chat_history.append({"role": "user", "content": user_prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("AI sedang memproses basis data..."):
                    # 1. Bangun SQL otomatis dengan memori riwayat chat
                    sql_query = engine.ask_llm_sql(user_prompt, st.session_state.agent_chat_history[:-1])
                    res_df, error_msg = engine.execute_sql(sql_query)
                    
                    if error_msg:
                        st.error(f"Kegagalan Translasi SQL: {error_msg}")
                        st.code(sql_query, language="sql")
                    else:
                        # 2. Hasilkan narasi wawasan eksekutif
                        insight = engine.generate_narrative_insight(user_prompt, res_df, st.session_state.agent_chat_history[:-1])
                        st.markdown(insight)
                        
                        # Format angka tabel agar rapi saat ditampilkan ke pengguna
                        disp_df = res_df.copy()
                        for col in disp_df.select_dtypes(include=['float', 'int']).columns:
                            if 'RATE' not in col and 'PERCENT' not in col:
                                disp_df[col] = disp_df[col].apply(lambda x: f"{x:,.0f}".replace(",", "."))
                        st.dataframe(disp_df, use_container_width=True)
                        
                        # 3. Grafik Otomatis Melalui Chart Agent Engine
                        chart_cfg = engine.generate_ai_chart(user_prompt, res_df)
                        if chart_cfg:
                            try:
                                if chart_cfg["chart_type"] == "bar":
                                    fig = px.bar(res_df, x=chart_cfg["x"], y=chart_cfg["y"], color=chart_cfg.get("color"), title=chart_cfg["title"], orientation=chart_cfg.get("orientation", "v"))
                                elif chart_cfg["chart_type"] == "line":
                                    fig = px.line(res_df, x=chart_cfg["x"], y=chart_cfg["y"], color=chart_cfg.get("color"), title=chart_cfg["title"])
                                elif chart_cfg["chart_type"] == "pie":
                                    fig = px.pie(res_df, values=chart_cfg["y"], names=chart_cfg["x"], title=chart_cfg["title"])
                                st.plotly_chart(fig, use_container_width=True)
                            except:
                                chart_cfg = None
                                
                        # Simpan komplit data ke dalam state riwayat agar persisten saat re-run
                        st.session_state.agent_chat_history.append({
                            "role": "assistant", "content": insight,
                            "df_result": res_df, "chart_config": chart_cfg
                        })

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
            spending_mult = st.slider("Simulasi Akselerasi Kecepatan Belanja (%)", 50, 200, 100) / 100.0
            target_abs = st.slider("Target Batas Batas Penyerapan (%)", 70, 100, 95)
            rel_block = st.checkbox("Buka Kunci Anggaran Terblokir Otomatis")
        with sc_col2:
            sim_res = run_simulation_engine(metrics, spending_mult, target_abs, rel_block)
            st.metric("Simulasi Anggaran Terserap Akhir", format_rp(sim_res['sim_realization']), f"Total Serap: {sim_res['sim_absorption_rate']:.1f}%")
            st.metric("Dana Tambahan Guna Mencapai Target", format_rp(sim_res['required_realization_for_target']))

    with t_rev:
        tgt_pct = st.number_input("Input Target Persentase Penyerapan Akhir Tahun (%)", 1.0, 100.0, 95.0)
        rev_res = run_reverse_math_engine(metrics, tgt_pct)
        st.metric("Batas Belanja Bulanan Minimal Wajib", format_rp(rev_res['required_monthly_spending']), f"Dihitung untuk sisa {rev_res['remaining_months']} bulan berjalan")

    with t_anomaly:
        st.info("Deteksi Anomali Penyimpangan Transaksi Pagu Belanja:")
        anom_disp = anomalies[anomalies['IS_ANOMALOUS'] == True].sort_values(by=schema['budget'], ascending=False).copy()
        for col in anom_disp.select_dtypes(include=['float', 'int']).columns:
            if 'RATE' not in col:
                anom_disp[col] = anom_disp[col].apply(format_rp)
        st.dataframe(anom_disp, use_container_width=True)

    with t_bottleneck:
        b_styled = bottlenecks.copy()
        styled = b_styled.style.format(formatter={col: format_rp for col in b_styled.columns if 'RATE' not in col and 'SCORE' not in col and b_styled[col].dtype in ['float', 'int']})
        styled = styled.background_gradient(subset=['IMPACT_SCORE'], cmap='Reds')
        st.dataframe(styled, use_container_width=True)

    with t_report:
        if st.button("🚀 Formulasikan Naskah Ringkasan Eksekutif"):
            with st.spinner("AI sedang menyusun draf naskah laporan dokumen..."):
                entity_col = schema['org'][0] if schema['org'] else 'INDEX'
                b_str = bottlenecks.head(3)[[entity_col, schema['budget'], 'UNSPENT', 'ABSORPTION_RATE']].to_string()
                a_str = f"Defisit: {anomalies['ANOMALY_DEFICIT'].sum()}\nSpike: {anomalies['ANOMALY_SPIKE'].sum()}"
                
                advise = BudgetQueryEngine(df, schema, api_key).generate_recommendation_plan(b_str, a_str)
                st.session_state.executive_report = compile_executive_report(metrics, forecast, bottlenecks, anomalies, advise)
                st.session_state.docx_file = generate_docx(st.session_state.executive_report)
                
        if st.session_state.executive_report:
            st.download_button(
                "💾 Unduh Berkas Laporan Eksekutif (.docx)", 
                data=st.session_state.docx_file, 
                file_name="Laporan_Eksekutif_Intelijen_Anggaran.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.markdown(f'<div class="report-block">{st.session_state.executive_report}</div>', unsafe_allow_html=True)
