"""
Budget Intelligence Agent - Structural Schema Detection & Data Engineering Core
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

# Kamus Sinonim Metadata Berdasarkan Konteks Pemerintahan
COLUMN_METADATA = {
    "KDDEPT": ["kode departemen", "kode kementerian", "kode k/l", "ministry code", "agency code", "kddept"],
    "NMDEPT": ["nama departemen", "nama kementerian", "nama k/l", "kementerian", "lembaga", "ministry name", "nmdept"],
    "KDUNIT": ["kode unit", "kode eselon 1", "kode ditjen", "echelon 1 code", "kdunit"],
    "NMUNIT": ["nama unit", "nama eselon 1", "nama ditjen", "direktorat jenderal", "unit kerja eselon i", "nmunit"],
    "KDSATKER": ["kode satker", "nomor satker", "working unit code", "kdsatker"],
    "NMSATKER": ["nama satker", "satuan kerja", "satker apa", "working unit name", "nmsatker"],
    "KDAKUN": ["kode akun", "mata anggaran", "mak", "account code", "coa", "kdakun"],
    "NMAKUN": ["nama akun", "uraian akun", "jenis belanja", "account name", "nmakun"],
    "PAGU_DIPA": ["pagu", "pagu anggaran", "plafon anggaran", "anggaran dipa", "total budget", "allocation", "pagu_dipa"],
    "BLOKIR": ["blokir", "anggaran diblokir", "pagu blokir", "automatic adjustment", "blocked budget", "blokir"],
    "JAN": ["januari", "jan", "realisasi januari"], "FEB": ["februari", "feb", "realisasi februari"],
    "MAR": ["maret", "mar", "realisasi maret"], "APR": ["april", "apr", "realisasi april"],
    "MEI": ["mei", "may", "realisasi mei"], "JUN": ["juni", "jun", "realisasi juni"],
    "JUL": ["juli", "jul", "realisasi juli"], "AGS": ["agustus", "ags", "agt", "realisasi agustus"],
    "SEP": ["september", "sep", "realisasi september"], "OKT": ["oktober", "okt", "realisasi oktober"],
    "NOV": ["november", "nov", "realisasi november"], "DES": ["desember", "des", "realisasi desember"]
}

def detect_budget_schema(df: pd.DataFrame) -> Dict[str, Any]:
    columns = [str(c).strip() for c in df.columns]
    columns_lower = [c.lower() for c in columns]
    
    schema = {
        'budget': None, 'blocked': None, 'account_code': None,
        'kddept': None, 'nmdept': None, 'kdsatker': None, 'nmsatker': None,
        'org': [], 'account': [], 'months': {}, 'months_short': []
    }
    
    def find_match(target_key: str) -> str:
        syns = COLUMN_METADATA[target_key]
        # Pencarian presisi (Exact Match)
        for s in syns:
            if s in columns_lower:
                return columns[columns_lower.index(s)]
        # Pencarian substring (Fuzzy Match)
        for c in columns:
            if any(s in c.lower() for s in syns if len(s) > 3):
                return c
        return None

    # Petakan kolom utama secara terarah untuk keperluan LLM context
    schema['budget'] = find_match('PAGU_DIPA')
    schema['blocked'] = find_match('BLOKIR')
    schema['account_code'] = find_match('KDAKUN')
    schema['kddept'] = find_match('KDDEPT')
    schema['nmdept'] = find_match('NMDEPT')
    schema['kdsatker'] = find_match('KDSATKER')
    schema['nmsatker'] = find_match('NMSATKER')
    
    # Kelompokkan bulan
    for m in ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]:
        matched_col = find_match(m)
        if matched_col:
            schema['months'][m] = matched_col
            schema['months_short'].append(m)

    # Isi fallback organisasional jika pengguna butuh filter lain
    for k in ["NMDEPT", "NMUNIT", "NMSATKER", "NMKANWIL", "NMKPPN"]:
        m = find_match(k)
        if m and m not in schema['org']: schema['org'].append(m)
    for k in ["NMAKUN", "NMPROGRAM", "NMGIAT", "NMOUTPUT"]:
        m = find_match(k)
        if m and m not in schema['account']: schema['account'].append(m)
        
    return schema

def clean_and_prepare_data(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
    df_clean = df.copy()
    
    if schema['budget']:
        df_clean[schema['budget']] = pd.to_numeric(df_clean[schema['budget']], errors='coerce').fillna(0.0)
    else:
        raise ValueError("FATAL ERROR: Kolom Pagu Anggaran Utama tidak terdeteksi.")
        
    if schema['blocked']:
        df_clean[schema['blocked']] = pd.to_numeric(df_clean[schema['blocked']], errors='coerce').fillna(0.0)
    else:
        schema['blocked'] = 'BLOKIR_FALLBACK'
        df_clean['BLOKIR_FALLBACK'] = 0.0

    for m, col in schema['months'].items():
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0.0)
        
    # --- DATA ENGINEERING (FITUR BARU) ---
    df_clean['PAGU_EFEKTIF'] = df_clean[schema['budget']] - df_clean[schema['blocked']]
    
    jenis_belanja_map = {
        '51': 'Belanja Pegawai', '52': 'Belanja Barang', '53': 'Belanja Modal',
        '57': 'Belanja Bantuan Sosial', '66': 'Belanja Dana Desa',
        '63': 'Belanja Dana Alokasi Khusus Fisik', '65': 'Belanja Dana Alokasi Khusus Non Fisik',
        '61': 'Belanja Dana Bagi Hasil', '62': 'Belanja Dana Alokasi Umum'
    }
    
    if schema['account_code']:
        df_clean['JENIS_BELANJA'] = df_clean[schema['account_code']].astype(str).str.strip().str[:2].map(jenis_belanja_map).fillna('Belanja Lainnya')
    else:
        df_clean['JENIS_BELANJA'] = 'Belanja Lainnya'
        
    if schema['months'].values():
        df_clean['TOTAL_REALISASI_YTD'] = df_clean[list(schema['months'].values())].sum(axis=1)
    else:
        df_clean['TOTAL_REALISASI_YTD'] = 0.0
        
    df_clean['PERSEN_REALISASI_EFEKTIF'] = np.where(df_clean['PAGU_EFEKTIF'] > 0, (df_clean['TOTAL_REALISASI_YTD'] / df_clean['PAGU_EFEKTIF']) * 100, 0.0)
    
    return df_clean
