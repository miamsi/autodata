"""
Budget Intelligence Agent - DuckDB & Groq (Llama 3) Natural Language Core
"""

import duckdb
import pandas as pd
from groq import Groq
from typing import Dict, Any, Tuple, Optional

class BudgetQueryEngine:
    # Embedded DJPb Context Mapping for AI Prompting
    DJPB_CONTEXT_MAPPING = """
    # SYSTEM CONTEXT: BUDGET REALIZATION DATA DICTIONARY (DJPb STANDARD)
    # Use this mapping to translate user queries into data filters.
    
    data_source: "DJPb Budget Realization Report"
    column_mappings:
      - column: "KDDEPT"
        synonyms: ["kode departemen", "kode kementerian", "kode k/l", "ministry code"]
      - column: "NMDEPT"
        synonyms: ["nama departemen", "nama kementerian", "nama k/l", "kementerian"]
      - column: "KDUNIT"
        synonyms: ["kode unit", "kode eselon 1", "kode ditjen"]
      - column: "NMUNIT"
        synonyms: ["nama unit", "nama eselon 1", "nama ditjen", "direktorat jenderal"]
      - column: "KDKANWIL"
        synonyms: ["kode kanwil", "kode kantor wilayah"]
      - column: "NMKANWIL"
        synonyms: ["nama kanwil", "kantor wilayah djpb", "kanwil mana"]
      - column: "KDKPPN"
        synonyms: ["kode kppn", "kppn code"]
      - column: "NMKPPN"
        synonyms: ["nama kppn", "kantor bayar", "kppn mana"]
      - column: "KDSATKER"
        synonyms: ["kode satker", "nomor satker"]
      - column: "NMSATKER"
        synonyms: ["nama satker", "satuan kerja", "satker apa"]
      - column: "KDPROGRAM"
        synonyms: ["kode program", "kd prog"]
      - column: "NMPROGRAM"
        synonyms: ["nama program", "program", "program kerja"]
      - column: "KDGIAT"
        synonyms: ["kode kegiatan", "kd giat"]
      - column: "NMGIAT"
        synonyms: ["nama kegiatan", "kegiatan"]
      - column: "KDOUTPUT"
        synonyms: ["kode output", "kd output"]
      - column: "NMOUTPUT"
        synonyms: ["nama output", "output", "keluaran"]
      - column: "KDAKUN"
        synonyms: ["kode akun", "mata anggaran", "mak", "coa"]
      - column: "NMAKUN"
        synonyms: ["nama akun", "uraian akun", "jenis belanja"]
      - column: "KDSDANA"
        synonyms: ["kode sumber dana", "kd sdana"]
      - column: "NMSDANA2"
        synonyms: ["nama sumber dana", "sumber dana", "jenis dana"]
      - column: "PAGU_DIPA"
        synonyms: ["pagu", "pagu anggaran", "plafon anggaran", "anggaran dipa", "total budget"]
      - column: "JAN"
        synonyms: ["januari", "jan", "realisasi januari"]
      - column: "FEB"
        synonyms: ["februari", "feb", "realisasi februari"]
      - column: "MAR"
        synonyms: ["maret", "mar", "realisasi maret"]
      - column: "APR"
        synonyms: ["april", "apr", "realisasi april"]
      - column: "MEI"
        synonyms: ["mei", "may", "realisasi mei"]
      - column: "JUN"
        synonyms: ["juni", "jun", "realisasi juni"]
      - column: "JUL"
        synonyms: ["juli", "jul", "realisasi juli"]
      - column: "AGS"
        synonyms: ["agustus", "ags", "agt", "realisasi agustus"]
      - column: "SEP"
        synonyms: ["september", "sep", "realisasi september"]
      - column: "OKT"
        synonyms: ["oktober", "okt", "realisasi oktober"]
      - column: "NOV"
        synonyms: ["november", "nov", "realisasi november"]
      - column: "DES"
        synonyms: ["desember", "des", "realisasi desember"]
      - column: "BLOKIR"
        synonyms: ["blokir", "anggaran diblokir", "pagu blokir", "automatic adjustment"]
    """

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
        
        system_prompt = f"You are an expert DuckDB SQL engineer. You only output raw SQL queries wrapped in ```sql tags. Do not write explanations.\n\n{self.DJPB_CONTEXT_MAPPING}"
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
4. IMPORTANT: Always use GROUP BY and SUM() when analyzing or ranking categorical entities (like NMDEPT, NMSATKER, or NMAKUN) to prevent duplicate text rows.
5. Return ONLY the raw SQL wrapped in a markdown code block.

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
        
        system_prompt = f"Anda adalah Agen Intelijen Anggaran Eksekutif. Anda wajib menjawab selalu menggunakan Bahasa Indonesia yang profesional dan formal.\n\n{self.DJPB_CONTEXT_MAPPING}"
        user_prompt = f"""
Pertanyaan User: "{user_question}"
Hasil Data:
{result_markdown}

Tuliskan HANYA 1 paragraf singkat yang mendeskripsikan data ini secara faktual dalam Bahasa Indonesia. DILARANG menggunakan poin-poin (bullet points), dilarang memberikan saran operasional, dan dilarang menyebut kata SQL. Format angka dengan mata uang Rupiah jika ada nominal uang.
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
            
        system_prompt = f"Anda adalah Penasihat Strategis Anggaran. Wajib merespons menggunakan Bahasa Indonesia profesional.\n\n{self.DJPB_CONTEXT_MAPPING}"
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
