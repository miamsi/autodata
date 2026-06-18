"""
Budget Intelligence Agent - Conversational SQL Engine & AI Chart Agent
"""

import duckdb
import pandas as pd
import json
import re
from groq import Groq
from typing import Dict, Any, Tuple, Optional, List

class BudgetQueryEngine:
    def __init__(self, df: pd.DataFrame, schema: Dict[str, Any], api_key: str):
        self.conn = duckdb.connect(database=':memory:')
        self.schema = schema
        self.df = df
        self.conn.register('budget_data', self.df)
        
        if api_key:
            self.client = Groq(api_key=api_key)
            self.model_name = "openai/gpt-oss-20b"
        else:
            self.client = None

    def execute_sql(self, sql_query: str) -> Tuple[pd.DataFrame, Optional[str]]:
        try:
            clean_sql = sql_query.strip()
            if "```sql" in clean_sql:
                clean_sql = clean_sql.split("```sql")[1].split("```")[0].strip()
            elif "```" in clean_sql:
                clean_sql = clean_sql.split("```")[1].split("```")[0].strip()
            
            res_df = self.conn.execute(clean_sql).df()
            return res_df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def ask_llm_sql(self, user_question: str, history: List[Dict[str, str]] = None) -> str:
        if not self.client:
            return "SELECT * FROM budget_data LIMIT 5;"
            
        months_str = ", ".join([f"{k}: '{v}'" for k, v in self.schema['months'].items()])
        org_str = ", ".join(self.schema['org'])
        acc_str = ", ".join(self.schema['account'])
        
        # Susun riwayat percakapan untuk konteks tindak lanjut (follow-up requests)
        history_context = ""
        if history:
            for msg in history[-4:]: # Ambil 4 interaksi terakhir saja agar tidak kelebihan token
                role = "User" if msg['role'] == 'user' else "AI"
                history_context += f"{role}: {msg['content']}\n"

        system_prompt = "You are an expert DuckDB SQL engineer. You only output raw SQL queries wrapped in ```sql tags. No conversational filler text."
        user_prompt = f"""
Translate the user's question into a valid DuckDB SQL query based on the historical conversation.
Table Name: 'budget_data'

Available Engineered Columns:
- 'PAGU_EFEKTIF' (Pagu DIPA - BLOKIR)
- 'JENIS_BELANJA' (Kategori Belanja seperti Belanja Pegawai, Belanja Barang, Belanja Modal, dll)
- 'TOTAL_REALISASI_YTD' (Total Realisasi akumulasi bulan-bulan aktif)
- 'PERSEN_REALISASI_EFEKTIF' (Total Realisasi / Pagu Efektif * 100)

Original Schema:
- Original Budget Column: '{self.schema['budget']}'
- Original Blocked Column: '{self.schema['blocked']}'
- Original Account Code: '{self.schema['account_code']}'
- Monthly Columns: {{ {months_str} }}
- Organizational Columns: [ {org_str} ]
- Account Columns: [ {acc_str} ]

Context History:
{history_context}

Rules:
1. Prioritize using engineered columns ('PAGU_EFEKTIF', 'JENIS_BELANJA', 'PERSEN_REALISASI_EFEKTIF') if the user asks about effective budget or categories.
2. Output ONLY the raw SQL inside standard ```sql ... ``` markers.

User Current Question: "{user_question}"
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name,
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"SELECT 'Error Groq SQL Engine: {str(e)}' as Error;"

    def generate_narrative_insight(self, user_question: str, result_df: pd.DataFrame, history: List[Dict[str, str]] = None) -> str:
        if not self.client:
            return "Kunci API Groq tidak dikonfigurasi. Menampilkan tabel mentah."
            
        result_markdown = result_df.head(15).to_markdown(index=False)
        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in (history[-3:] if history else [])])
        
        system_prompt = "Anda adalah Analis Keuangan Eksekutif Kementerian Keuangan. Anda wajib membalas menggunakan Bahasa Indonesia yang formal, taktis, dan ringkas."
        user_prompt = f"""
Berikan penjelasan naratif interaktif dari hasil query data anggaran berikut berdasarkan konteks percakapan sebelumnya.

Riwayat Konteks:
{history_context}

Pertanyaan Terbaru User: "{user_question}"
Hasil Data Query:
{result_markdown}

Aturan Penulisan Jawab:
1. Jawab langsung ke inti pertanyaan dalam Bahasa Indonesia secara komprehensif.
2. Jika ada angka uang besar, sebutkan dalam format Rupiah terstruktur (Contoh: Rp 12,5 Miliar atau Rp 4,2 Triliun).
3. Berikan 2 rekomendasi langkah operasional konkret. Dilarang keras menyebut istilah teknis basis data seperti 'SQL', 'Table', 'Row', atau nama kolom database dalam narasi Anda!
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"**Gagal menghasilkan narasi AI.** Error: `{str(e)}`"

    def generate_ai_chart(self, user_question: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Menganalisis data hasil query dan menghasilkan spesifikasi grafik Plotly Express secara otomatis"""
        if not self.client or df.empty or len(df) < 2:
            return None
            
        cols = list(df.columns)
        sample_data = df.head(3).to_dict(orient='records')
        
        system_prompt = "You are a data visualization expert. You output ONLY valid JSON blocks containing chart configurations for Plotly Express. Do not output python code text."
        user_prompt = f"""
Analyze the dataframe details and user question to produce an optimized interactive chart configuration using Plotly Express.
Dataframe Columns: {cols}
Sample Rows Data: {json.dumps(sample_data)}
User Question Context: "{user_question}"

Output format MUST be a strict JSON block with these keys:
- "chart_type": (string choice: "bar", "line", "pie", "scatter")
- "x": (string, column name for x-axis)
- "y": (string, column name for y-axis)
- "color": (string or null, column name for groupings)
- "title": (string, chart title in Bahasa Indonesia)
- "orientation": (string, "h" or "v" for bar chart only)

If the data is completely non-visualizable, return JSON with "chart_type": "none".
JSON Output:
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            config = json.loads(response.choices[0].message.content)
            if config.get("chart_type") == "none":
                return None
            return config
        except:
            return None

    def generate_recommendation_plan(self, bottleneck_summary: str, anomaly_summary: str) -> str:
        if not self.client: return "Kunci API Groq tidak dikonfigurasi."
        system_prompt = "Anda adalah Direktur Pelaksana Anggaran Negara. Wajib merespons menggunakan Bahasa Indonesia profesional."
        user_prompt = f"""
Tinjau kendala operasional (bottleneck) dan anomali anggaran berikut:
Top Bottleneck Matrix:\n{bottleneck_summary}
Anomali Ringkasan:\n{anomaly_summary}

Susun Rencana Aksi Strategis & Intervensi Anggaran Berbahasa Indonesia dalam format Markdown yang mencakup:
1. Ringkasan Eksekutif Kendala Struktural.
2. Matriks Intervensi Prioritas Pembebasan Bottleneck Belanja.
3. Kebijakan Mitigasi Risiko Penyerapan Akhir Tahun.
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Gagal memformulasikan rencana aksi strategis. Kesalahan: {str(e)}"
