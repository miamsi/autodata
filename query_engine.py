"""
Budget Intelligence Agent - Conversational SQL Engine
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
        self.client = Groq(api_key=api_key) if api_key else None
        self.model_name = "gpt-oss-20b"

    def _extract_sql_from_text(self, text: str) -> str:
        match = re.search(r'
http://googleusercontent.com/immersive_entry_chip/0

### Langkah Penting untuk Mengatasi Error:

1. **Pastikan `app.py` benar:** Di `app.py`, baris `from query_engine import BudgetQueryEngine` **harus berada di baris paling atas** setelah *import* bawaan Streamlit/Pandas. Pastikan tidak ada *whitespace* aneh sebelum `from`.
2. **Cek Filename:** Pastikan nama file di disk persis `query_engine.py` (huruf kecil semua, underscore benar).
3. **Streamlit Cache:** Jika error tetap berlanjut di Streamlit Cloud, klik tombol **"Reboot app"** atau **"Clear cache"** di menu *Manage app* (pojok kanan bawah). Terkadang Streamlit menyimpan *bytecode* lama yang rusak.

Saya telah menyederhanakan `query_engine.py` di atas agar tidak ada risiko *syntax error* sama sekali. Silakan dicoba kembali.
