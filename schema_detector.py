"""
Budget Intelligence Agent - Structural Schema Detection & Data Engineering Core
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Kamus Sinonim & Metadata Kolom Resmi Berdasarkan Aturan Bisnis DIPA
COLUMN_METADATA = {
    "KDDEPT": ["kode departemen", "kode kementerian", "kode k/l", "ministry code", "agency code", "kddept"],
    "NMDEPT": ["nama departemen", "nama kementerian", "nama k/l", "kementerian", "lembaga", "ministry name", "nmdept"],
    "KDUNIT": ["kode unit", "kode eselon 1", "kode ditjen", "echelon 1 code", "kdunit"],
    "NMUNIT": ["nama unit", "nama eselon 1", "nama ditjen", "direktorat jenderal", "unit kerja eselon i", "nmunit"],
    "KDKANWIL": ["kode kanwil", "kode kantor wilayah", "regional office code", "kdkanwil"],
    "NMKANWIL": ["nama kanwil", "kantor wilayah djpb", "kanwil mana", "regional office name", "nmkanwil"],
    "KDKPPN": ["kode kppn", "kppn code", "treasury office code", "kdkppn"],
    "NMKPPN": ["nama kppn", "kantor bayar", "kppn mana", "treasury office name", "nmppn", "nmkppn"],
    "KDSATKER": ["kode satker", "nomor satker", "working unit code", "kdsatker"],
    "NMSATKER": ["nama satker", "satuan kerja", "satker apa", "working unit name", "nmsatker"],
    "KDPROGRAM": ["kode program", "kd prog", "program code", "kdprogram"],
    "NMPROGRAM": ["nama program", "program", "program kerja", "nmprogram"],
    "KDGIAT": ["kode kegiatan", "kd giat", "activity code", "kdgiat"],
    "NMGIAT": ["nama kegiatan", "kegiatan", "activity name", "nmgiat"],
    "KDOUTPUT": ["kode output", "kd output", "output code", "kdoutput"],
    "NMOUTPUT": ["nama output", "output", "keluaran", "output name", "nmoutput"],
    "KDAKUN": ["kode akun", "mata anggaran", "mak", "account code", "coa", "kdakun"],
    "NMAKUN": ["nama akun", "uraian akun", "jenis belanja", "account name", "nmakun"],
    "KDSDANA": ["kode sumber dana", "kd sdana", "source of funds code", "kdsdana"],
    "NMSDANA2": ["nama sumber dana", "sumber dana", "jenis dana", "source of funds description", "nmsdana2"],
    "PAGU_DIPA": ["pagu", "pagu anggaran", "plafon anggaran", "anggaran dipa", "total budget", "allocation", "pagu_dipa"],
    "BLOKIR": ["blokir", "anggaran diblokir", "pagu blokir", "automatic adjustment", "blocked budget", "blokir"],
    "JAN": ["januari", "jan", "realisasi januari", "january spending"],
    "FEB": ["februari", "feb", "realisasi februari", "february spending"],
    "MAR": ["maret", "mar", "realisasi maret", "march spending"],
    "APR": ["april", "apr", "realisasi april", "april spending"],
    "MEI": ["mei", "may", "realisasi mei", "may spending"],
    "JUN": ["juni", "jun", "realisasi juni", "june spending"],
    "JUL": ["juli", "jul", "realisasi juli", "july spending"],
    "AGS": ["agustus", "ags", "agt", "realisasi agustus", "august spending"],
    "SEP": ["september", "sep", "realisasi september", "september spending"],
    "OKT": ["oktober", "okt", "realisasi oktober", "october spending"],
    "NOV": ["november", "nov", "realisasi november", "november spending"],
    "DES": ["desember", "des", "realisasi desember", "december spending"]
}

def detect_budget_schema(df: pd.DataFrame) -> Dict[str, Any]:
    columns = [str(c).strip() for c in df.columns]
    columns_lower = [c.lower() for c in columns]
    
    schema = {
        'budget': None, 'blocked': None, 'account_code': None,
        'org': [], 'account': [], 'months': {}, 'months_short': []
    }
    
    # Helper untuk mencocokkan kolom berdasarkan sinonim
    def find_match(target_key: str) -> str:
        syns = COLUMN_METADATA[target_key]
        for s in syns:
            if s in columns_lower:
                return columns[columns_lower.index(s)]
        # Fallback substring matching
        for c in columns:
            if any(s in c.lower() for s in syns if len(s) > 3):
                return c
        return None

    # Pemetaan Pagu, Blokir, Akun
    schema['budget'] = find_match('PAGU_DIPA')
    schema['blocked'] = find_match('BLOKIR')
    schema['account_code'] = find_match('KDAKUN')
    
    # Jika Pagu gagal dideteksi, cari kolom angka terbesar sebagai fallback
    if not schema['budget']:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            schema['budget'] = numeric_cols[df[numeric_cols].sum().argmax()]
            
    # Pemetaan Bulanan
    month_keys = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]
    for m in month_keys:
        matched_col = find_match(m)
        if matched_col:
            schema['months'][m] = matched_col
            schema['months_short'].append(m)

    # Pemetaan Hirarki Organisasi & Akun untuk Analisis Dinamis
    org_keys = ["NMDEPT", "NMUNIT", "NMKANWIL", "NMKPPN", "NMSATKER", "KDDEPT", "KDUNIT", "KDSATKER"]
    acc_keys = ["NMPROGRAM", "NMGIAT", "NMOUTPUT", "NMAKUN", "NMSDANA2", "KDAKUN"]
    
    for k in org_keys:
        m = find_match(k)
        if m and m not in schema['org']: schema['org'].append(m)
        
    for k in acc_keys:
        m = find_match(k)
        if m and m not in schema['account']: schema['account'].append(m)
        
    return schema

def clean_and_prepare_data(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
    df_clean = df.copy()
    
    # Standardisasi data numerik primer
    if schema['budget']:
        df_clean[schema['budget']] = pd.to_numeric(df_clean[schema['budget']], errors='coerce').fillna(0.0)
    else:
        raise ValueError("Kolom Pagu Anggaran tidak berhasil diidentifikasi.")
        
    if schema['blocked']:
        df_clean[schema['blocked']] = pd.to_numeric(df_clean[schema['blocked']], errors='coerce').fillna(0.0)
    else:
        # Buat kolom fallback jika data masukan tidak memiliki kolom blokir
        schema['blocked'] = 'BLOKIR_FALLBACK'
        df_clean['BLOKIR_FALLBACK'] = 0.0

    # Bersihkan kolom-kolom bulanan
    for m, col in schema['months'].items():
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0.0)
        
    # --- REKAYASA DATA (FEATURE ENGINEERING AUTOMATION) ---
    # 1. Kolom Pagu Efektif
    df_clean['PAGU_EFEKTIF'] = df_clean[schema['budget']] - df_clean[schema['blocked']]
    
    # 2. Pembagian Jenis Belanja Berdasarkan 2 Digit Pertama KDAKUN
    jenis_belanja_map = {
        '51': 'Belanja Pegawai', '52': 'Belanja Barang', '53': 'Belanja Modal',
        '57': 'Belanja Bantuan Sosial', '66': 'Belanja Dana Desa',
        '63': 'Belanja Dana Alokasi Khusus Fisik', '65': 'Belanja Dana Alokasi Khusus Non Fisik',
        '61': 'Belanja Dana Bagi Hasil', '62': 'Belanja Dana Alokasi Umum'
    }
    
    if schema['account_code']:
        def extract_jenis(val):
            val_str = str(val).strip().split('.')[0] # Tangani format desimal excel jika ada
            prefix = val_str[:2]
            return jenis_belanja_map.get(prefix, 'Belanja Lainnya')
        df_clean['JENIS_BELANJA'] = df_clean[schema['account_code']].apply(extract_jenis)
    else:
        df_clean['JENIS_BELANJA'] = 'Belanja Lainnya'
        
    # 3. Hitung Total Realisasi & Persentase Realisasi Terhadap Pagu Efektif
    month_cols = list(schema['months'].values())
    if month_cols:
        df_clean['TOTAL_REALISASI_YTD'] = df_clean[month_cols].sum(axis=1)
    else:
        df_clean['TOTAL_REALISASI_YTD'] = 0.0
        
    # Kalkulasi persentase dengan penanganan pembagian dengan nol
    df_clean['PERSEN_REALISASI_EFEKTIF'] = np.where(
        df_clean['PAGU_EFEKTIF'] > 0,
        (df_clean['TOTAL_REALISASI_YTD'] / df_clean['PAGU_EFEKTIF']) * 100,
        0.0
    )
    
    return df_clean
