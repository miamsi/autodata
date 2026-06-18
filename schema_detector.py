"""
Budget Intelligence Agent - Schema Detector & Normalization Engine
"""

import pandas as pd
import re
from typing import Dict, Any

def detect_budget_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes dataframe columns to identify organizational hierarchies,
    accounts, budget limits (Pagu), blocks (Blokir), and monthly buckets.
    """
    columns = list(df.columns)
    months_short = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']
    months_long = ['JANUARI', 'FEBRUARI', 'MARET', 'APRIL', 'MEI', 'JUNI', 'JULI', 'AGUSTUS', 'SEPTEMBER', 'OKTOBER', 'NOVEMBER', 'DESEMBER']
    
    schema = {
        'budget': '',
        'blocked': '',
        'months': {},
        'org': [],
        'account': []
    }
    
    # 1. Detect Financial Limits
    for col in columns:
        cl = col.upper()
        if any(x in cl for x in ['PAGU', 'ALOKASI', 'BUDGET', 'CEILING']):
            if not any(b in cl for b in ['BLOKIR', 'BLOCKED', 'SISA']):
                schema['budget'] = col
        if any(x in cl for x in ['BLOKIR', 'BLOCKED', 'HOLD']):
            schema['blocked'] = col

    # Fallbacks
    if not schema['budget']:
        for col in columns:
            if 'PAGU' in col.upper():
                schema['budget'] = col
                break
    if not schema['blocked']:
        for col in columns:
            if 'BLOK' in col.upper():
                schema['blocked'] = col
                break

    # 2. Map Time-Series Buckets
    for i, m_short in enumerate(months_short):
        m_long = months_long[i]
        for col in columns:
            cl = col.upper()
            if cl == m_short or cl == m_long or cl.startswith(m_short) or cl.startswith(m_long):
                schema['months'][m_short] = col
                break

    # 3. Categorize Hierarchies
    for col in columns:
        cl = col.upper()
        if col == schema['budget'] or col == schema['blocked'] or col in schema['months'].values():
            continue
        if any(x in cl for x in ['DEPT', 'UNIT', 'KANWIL', 'KPPN', 'SATKER', 'KEMENTERIAN', 'LEMBAGA', 'REGION', 'WILAYAH']):
            schema['org'].append(col)
        elif any(x in cl for x in ['AKUN', 'PROGRAM', 'GIAT', 'OUTPUT', 'SUBOUTPUT', 'KOMPONEN', 'MATA_ANGGARAN']):
            schema['account'].append(col)
            
    return schema

def clean_and_prepare_data(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
    """
    Normalizes dirty currency string inputs into DuckDB-safe floats.
    """
    cleaned_df = df.copy()
    
    # Enforce standard formatting for KDDEPT to prevent downstream string parsing errors
    if 'KDDEPT' in cleaned_df.columns:
        cleaned_df['KDDEPT'] = cleaned_df['KDDEPT'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(3)
    
    def parse_numeric(v: Any) -> float:
        if pd.isna(v):
            return 0.0
        v_str = str(v).strip()
        if not v_str or v_str.lower() in ['censored', '-', 'null', 'none']:
            return 0.0
        v_str = v_str.replace(' ', '')
        
        # Handle decimal/thousands variations
        if ',' in v_str and '.' in v_str:
            if v_str.find(',') > v_str.find('.'):
                v_str = v_str.replace('.', '').replace(',', '.')
            else:
                v_str = v_str.replace(',', '')
        elif ',' in v_str:
            if len(v_str.split(',')[-1]) <= 2:
                v_str = v_str.replace(',', '.')
            else:
                v_str = v_str.replace(',', '')
                
        try:
            return float(re.sub(r'[^\d\.\-]', '', v_str))
        except ValueError:
            return 0.0

    # Clean primary boundaries
    if schema['budget'] and schema['budget'] in cleaned_df.columns:
        cleaned_df[schema['budget']] = cleaned_df[schema['budget']].apply(parse_numeric)
    else:
        schema['budget'] = 'TOTAL_PAGU_FALLBACK'
        cleaned_df['TOTAL_PAGU_FALLBACK'] = 0.0
        
    if schema['blocked'] and schema['blocked'] in cleaned_df.columns:
        cleaned_df[schema['blocked']] = cleaned_df[schema['blocked']].apply(parse_numeric)
    else:
        schema['blocked'] = 'BLOKIR_FALLBACK'
        cleaned_df['BLOKIR_FALLBACK'] = 0.0

    # Clean calendar buckets
    months_list = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']
    for m in months_list:
        if m in schema['months'] and schema['months'][m] in cleaned_df.columns:
            col_name = schema['months'][m]
            cleaned_df[col_name] = cleaned_df[col_name].apply(parse_numeric)
        else:
            col_name = f'{m}_FALLBACK'
            cleaned_df[col_name] = 0.0
            schema['months'][m] = col_name

    return cleaned_df
