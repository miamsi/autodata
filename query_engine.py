"""
Budget Intelligence Agent - DuckDB & Groq (Llama 3) Natural Language Core
"""

import duckdb
import pandas as pd
from groq import Groq
from typing import Dict, Any, Tuple, Optional

class BudgetQueryEngine:
    def __init__(self, df: pd.DataFrame, schema: Dict[str, Any], api_key: str):
        self.conn = duckdb.connect(database=':memory:')
        self.schema = schema
        self.df = df
        self.conn.register('budget_data', self.df)
        
        if api_key:
            self.client = Groq(api_key=api_key)
            self.model_name = "llama3-70b-8192"
        else:
            self.client = None

    def execute_sql(self, sql_query: str) -> Tuple[pd.DataFrame, Optional[str]]:
        try:
            clean_sql = sql_query.strip()
            if clean_sql.startswith("```sql"):
                clean_sql = clean_sql.split("```sql")[1].split("```")[0].strip()
            elif clean_sql.startswith("```"):
                clean_sql = clean_sql.split("```")[1].split("```")[0].strip()
            
            res_df = self.conn.execute(clean_sql).df()
            return res_df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def ask_llm_sql(self, user_question: str) -> str:
        if not self.client:
            return "SELECT * FROM budget_data LIMIT 5;"
            
        months_str = ", ".join([f"{k}: '{v}'" for k, v in self.schema['months'].items()])
        org_str = ", ".join(self.schema['org'])
        acc_str = ", ".join(self.schema['account'])
        
        system_prompt = "You are an expert DuckDB SQL engineer. You only output raw SQL queries wrapped in ```sql tags. Do not write explanations."
        user_prompt = f"""
Translate the user's question into a valid DuckDB SQL query.
Table Name: 'budget_data'
Schema:
- Budget Column: '{self.schema['budget']}'
- Blocked Column: '{self.schema['blocked']}'
- Monthly Columns: {{ {months_str} }}
- Organizational Columns: [ {org_str} ]
- Account Columns: [ {acc_str} ]

Rules:
1. Total Realization for any row is computed as the sum of its monthly columns: ({' + '.join(list(self.schema['months'].values()))}).
2. Always select readable text columns (like NMDEPT, NMSATKER, NMAKUN).
3. Use 'ORDER BY ... DESC LIMIT 10' for top/highest requests.
4. Return ONLY the raw SQL wrapped in a markdown code block.

User Question: "{user_question}"
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name,
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"SELECT 'Error Groq API: {str(e)}' as Error;"

    def generate_narrative_insight(self, user_question: str, sql_query: str, result_df: pd.DataFrame) -> str:
        if not self.client:
            return "Groq API key not configured. Displaying raw data only."
            
        # Limit to 20 rows to prevent Token Limit Exceeded on wide tables
        result_markdown = result_df.head(20).to_markdown(index=False)
        
        system_prompt = "Anda adalah Agen Intelijen Anggaran Eksekutif. Anda wajib menjawab selalu menggunakan Bahasa Indonesia yang profesional dan formal."
        user_prompt = f"""
Pertanyaan User: "{user_question}"
Hasil Data:
{result_markdown}

Tuliskan narasi profesional untuk menganalisis data ini dalam Bahasa Indonesia. Jawab pertanyaan secara langsung, soroti tren, dan berikan 2 saran operasional. Dilarang menyebut kata SQL atau nama tabel database dalam jawaban Anda. Format angka dengan mata uang Rupiah jika ada nominal uang.
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"**Gagal menghasilkan narasi AI.**\nError dari Server Groq: `{str(e)}`"

    def generate_recommendation_plan(self, bottleneck_summary: str, anomaly_summary: str) -> str:
        if not self.client:
            return "Groq API key missing. Cannot generate AI action plans."
            
        system_prompt = "Anda adalah Penasihat Strategis Anggaran. Wajib merespons menggunakan Bahasa Indonesia profesional."
        user_prompt = f"""
Tinjau anomali dan bottleneck anggaran berikut:

Top Bottleneck:
{bottleneck_summary}

Anomali:
{anomaly_summary}

Hasilkan Rencana Akselerasi Strategis dalam format Markdown berbahasa Indonesia yang mencakup:
1. Ringkasan Eksekutif (1 Paragraf).
2. Matriks Intervensi Prioritas untuk menangani unit/satker bottleneck tersebut.
3. Strategi Mitigasi Risiko untuk mencegah anomali.
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                model=self.model_name,
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"**Pembuatan Rekomendasi Gagal.** Kemungkinan limit API tercapai atau format data terlalu besar. Pesan Sistem Groq: `{str(e)}`"
