"""
Budget Intelligence Agent - Conversational SQL Engine & AI Chart Agent
"""

import duckdb
import pandas as pd
import json
from groq import Groq
from typing import Dict, Any, Tuple, Optional, List

class BudgetQueryEngine:
    def __init__(self, df: pd.DataFrame, schema: Dict[str, Any], api_key: str):
        self.conn = duckdb.connect(database=':memory:')
        self.schema = schema
        self.df = df
        self.conn.register('budget_data', self.df)
        
        self.client = Groq(api_key=api_key) if api_key else None
        self.model_name = "llama3-70b-8192"

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
        if not self.client: return "SELECT * FROM budget_data LIMIT 5;"
            
        history_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in (history[-3:] if history else [])])

        system_prompt = "You are a strict DuckDB SQL expert. You only output raw SQL queries wrapped in ```sql ... ```. No explanations."
        user_prompt = f"""
Convert this question into a valid DuckDB SQL statement.

CRITICAL LOGIC RULES:
1. PAGU DEFAULT RULE: If user asks for "pagu", "anggaran", or "budget", use the ORIGINAL column: '{self.schema['budget']}'. ONLY use the column 'PAGU_EFEKTIF' if the user explicitly types the words "pagu efektif".
2. ENTITY RESOLUTION RULES:
   - "Kementerian" or "Lembaga" or "K/L" -> You MUST group by '{self.schema['kddept']}' and '{self.schema['nmdept']}'. Do NOT include satker columns.
   - "Satker" or "Satuan Kerja" -> You MUST group by '{self.schema['kdsatker']}' and '{self.schema['nmsatker']}'.
3. ANTI-DUPLICATION (AGGREGATION RULE): The dataset contains multiple transaction rows for the same entity. To avoid duplicating entities in the result, you MUST use SUM() for financial columns and GROUP BY the entity code and name. Do not simply SELECT without grouping if asking for entities!
4. Engineered columns available: 'PAGU_EFEKTIF', 'JENIS_BELANJA', 'TOTAL_REALISASI_YTD', 'PERSEN_REALISASI_EFEKTIF'.

Context History:
{history_context}

Current Question: "{user_question}"
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name, temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"SELECT 'Error Generating SQL: {str(e)}' as Error;"

    def generate_narrative_insight(self, user_question: str, result_df: pd.DataFrame, history: List[Dict[str, str]] = None) -> str:
        if not self.client or result_df.empty: return "Berikut data hasil pencarian Anda:"
        result_md = result_df.head(10).to_markdown(index=False)
        
        system_prompt = "Anda adalah Data Reader. Anda hanya menjelaskan ulang tabel dalam teks narasi singkat. DILARANG KERAS memberikan opini, saran, rekomendasi, evaluasi operasional, arahan, atau peringatan apapun."
        user_prompt = f"""
Sajikan narasi ringkas (maksimal 2 kalimat) untuk mendeskripsikan tabel hasil berikut secara lugas.

Aturan Mutlak:
1. Jelaskan isi datanya (Misal: "Berikut adalah daftar 5 satker dengan pagu terbesar...").
2. Jika ada uang nominal besar, sebutkan dalam Rp (Miliar/Triliun).
3. JANGAN berikan "Rekomendasi Operasional" atau saran langkah apapun! HANYA DESKRIPSI DATA.
4. Jika terdapat duplikasi nama dengan kode berbeda, sebutkan bahwa entitas tersebut memiliki sub-unit berbeda.

Tabel Data:
{result_md}

Pertanyaan Pengguna: "{user_question}"
Narasi Ringkas:
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name, temperature=0.1
            )
            return response.choices[0].message.content
        except:
            return "Berikut hasil penarikan data transaksi yang Anda minta:"

    def generate_ai_chart(self, user_question: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if not self.client or df.empty or len(df) < 2: return None
        cols = list(df.columns)
        sample = df.head(2).to_dict(orient='records')
        
        user_prompt = f"Analyze columns {cols} and sample {json.dumps(sample)} for question '{user_question}'. Return a clean JSON with keys: 'chart_type' ('bar','line','pie' or 'none'), 'x' (column), 'y' (column), 'color' (column or null), 'title' (string), 'orientation' ('h' or 'v'). JSON ONLY:"
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": user_prompt}],
                model=self.model_name, temperature=0.0, response_format={"type": "json_object"}
            )
            cfg = json.loads(response.choices[0].message.content)
            return None if cfg.get("chart_type") == "none" else cfg
        except:
            return None

    def generate_recommendation_plan(self, bottleneck_summary: str, anomaly_summary: str) -> str:
        if not self.client: return "Kunci API Groq tidak dikonfigurasi."
        system_prompt = "Anda adalah Direktur Pelaksana Anggaran Negara. Merespons menggunakan Bahasa Indonesia profesional."
        user_prompt = f"""
Tinjau kendala (bottleneck) dan anomali anggaran berikut:
Top Bottleneck Matrix:\n{bottleneck_summary}
Anomali Ringkasan:\n{anomaly_summary}

Susun Rencana Aksi Strategis dalam format Markdown yang mencakup:
1. Ringkasan Eksekutif Kendala Struktural.
2. Matriks Intervensi Prioritas Pembebasan Bottleneck Belanja.
3. Kebijakan Mitigasi Risiko Penyerapan.
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name, temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Gagal memformulasikan rencana. Error: {str(e)}"
