"""
Budget Intelligence Agent - Financial Analytics Pipeline
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

def compute_core_metrics(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, Any]:
    budget_col = schema['budget']
    blocked_col = schema['blocked']
    month_cols = list(schema['months'].values())
    
    total_budget = float(df[budget_col].sum())
    total_blocked = float(df[blocked_col].sum())
    total_realization = float(df[month_cols].sum().sum())
    
    months_short = ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AGS', 'SEP', 'OKT', 'NOV', 'DES']
    current_month_idx = 0
    monthly_totals = {}
    
    for i, m in enumerate(months_short):
        col = schema['months'].get(m)
        m_sum = float(df[col].sum()) if col and col in df.columns else 0.0
        monthly_totals[m] = m_sum
        if m_sum > 0: current_month_idx = i + 1
            
    if current_month_idx == 0: current_month_idx = 1
        
    ytd_cols = [schema['months'][m] for m in months_short[:current_month_idx] if m in schema['months']]
    total_ytd_realization = float(df[ytd_cols].sum().sum())
    
    absorption_rate = (total_realization / total_budget * 100) if total_budget > 0 else 0.0
    blocked_rate = (total_blocked / total_budget * 100) if total_budget > 0 else 0.0
    
    return {
        'total_budget': total_budget,
        'total_blocked': total_blocked,
        'total_realization': total_realization,
        'total_ytd_realization': total_ytd_realization,
        'absorption_rate': absorption_rate,
        'blocked_rate': blocked_rate,
        'current_month_idx': current_month_idx,
        'monthly_totals': monthly_totals,
        'months_short': months_short
    }

def run_forecasting_engine(metrics: Dict[str, Any]) -> Dict[str, Any]:
    total_budget = metrics['total_budget']
    current_month_idx = metrics['current_month_idx']
    total_ytd_realization = metrics['total_ytd_realization']
    monthly_totals = metrics['monthly_totals']
    months_short = metrics['months_short']
    
    avg_monthly_burn = total_ytd_realization / current_month_idx if current_month_idx > 0 else 0.0
    
    if current_month_idx >= 12:
        forecast_eoy_realization = metrics['total_realization']
    else:
        forecast_eoy_realization = total_ytd_realization + (avg_monthly_burn * (12 - current_month_idx))
        
    forecast_absorption_rate = (forecast_eoy_realization / total_budget * 100) if total_budget > 0 else 0.0
    under_absorption = max(0.0, total_budget - forecast_eoy_realization)
    budget_deficit_risk = max(0.0, forecast_eoy_realization - total_budget)
    
    dec_spending = monthly_totals.get('DES', 0.0)
    dec_concentration_pct = (dec_spending / metrics['total_realization'] * 100) if current_month_idx == 12 and metrics['total_realization'] > 0 else (avg_monthly_burn / forecast_eoy_realization * 100 if forecast_eoy_realization > 0 else 0.0)

    forecast_trend = []
    running_total = 0.0
    for i, m in enumerate(months_short):
        if i + 1 <= current_month_idx:
            running_total += monthly_totals[m]
            forecast_trend.append({'month': m, 'type': 'Actual', 'value': monthly_totals[m], 'cumulative': running_total})
        else:
            running_total += avg_monthly_burn
            forecast_trend.append({'month': m, 'type': 'Forecast', 'value': avg_monthly_burn, 'cumulative': running_total})
            
    return {
        'forecast_eoy_realization': forecast_eoy_realization,
        'forecast_absorption_rate': forecast_absorption_rate,
        'under_absorption': under_absorption,
        'budget_deficit_risk': budget_deficit_risk,
        'dec_concentration_pct': dec_concentration_pct,
        'forecast_trend': forecast_trend
    }

def run_simulation_engine(metrics: Dict[str, Any], spending_multiplier: float, target_absorption: float, release_blocked: bool) -> Dict[str, Any]:
    total_budget = metrics['total_budget']
    total_blocked = metrics['total_blocked']
    total_realization = metrics['total_realization']
    
    sim_blocked = 0.0 if release_blocked else total_blocked
    sim_budget = total_budget
    sim_realization = total_realization * spending_multiplier
    sim_absorption_rate = (sim_realization / sim_budget * 100) if sim_budget > 0 else 0.0
    required_realization_for_target = (target_absorption / 100.0) * sim_budget
    
    return {
        'sim_realization': sim_realization,
        'sim_absorption_rate': sim_absorption_rate,
        'sim_blocked': sim_blocked,
        'required_realization_for_target': required_realization_for_target
    }

def run_reverse_math_engine(metrics: Dict[str, Any], target_absorption_pct: float) -> Dict[str, Any]:
    total_budget = metrics['total_budget']
    total_ytd_realization = metrics['total_ytd_realization']
    current_month_idx = metrics['current_month_idx']
    
    target_realization = (target_absorption_pct / 100.0) * total_budget
    remaining_to_spend = max(0.0, target_realization - total_ytd_realization)
    remaining_months = max(1, 12 - current_month_idx)
    
    required_monthly_spending = remaining_to_spend / remaining_months
    
    return {
        'target_realization': target_realization,
        'remaining_to_spend': remaining_to_spend,
        'remaining_months': remaining_months,
        'required_monthly_spending': required_monthly_spending,
        'target_achieved': total_ytd_realization >= target_realization
    }

def run_anomaly_detection(df: pd.DataFrame, schema: Dict[str, Any], metrics: Dict[str, Any]) -> pd.DataFrame:
    budget_col = schema['budget']
    blocked_col = schema['blocked']
    month_cols = list(schema['months'].values())
    current_month_idx = metrics['current_month_idx']
    
    anom_df = df.copy()
    anom_df['ROW_REALIZATION'] = anom_df[month_cols].sum(axis=1)
    anom_df['ROW_ABSORPTION_RATE'] = np.where(anom_df[budget_col] > 0, (anom_df['ROW_REALIZATION'] / anom_df[budget_col] * 100), 0.0)
    anom_df['ROW_BLOKIR_RATE'] = np.where(anom_df[budget_col] > 0, (anom_df[blocked_col] / anom_df[budget_col] * 100), 0.0)
    
    anom_df['ANOMALY_DEFICIT'] = anom_df['ROW_REALIZATION'] > anom_df[budget_col]
    anom_df['ANOMALY_LOW_ABSORPTION'] = (anom_df[budget_col] >= anom_df[budget_col].quantile(0.75)) & (anom_df['ROW_ABSORPTION_RATE'] < (current_month_idx * 5.0)) & (anom_df[budget_col] > 0)
    
    row_month_max = anom_df[month_cols].max(axis=1)
    row_month_sum = anom_df[month_cols].sum(axis=1)
    row_month_avg_others = (row_month_sum - row_month_max) / 11.0
    anom_df['ANOMALY_SPIKE'] = (row_month_max > (3.0 * row_month_avg_others)) & (row_month_max > 0)
    anom_df['ANOMALY_HIGH_BLOKIR'] = anom_df['ROW_BLOKIR_RATE'] > 20.0
    
    anom_df['IS_ANOMALOUS'] = anom_df['ANOMALY_DEFICIT'] | anom_df['ANOMALY_LOW_ABSORPTION'] | anom_df['ANOMALY_SPIKE'] | anom_df['ANOMALY_HIGH_BLOKIR']
    return anom_df

def run_debottlenecking_engine(df: pd.DataFrame, schema: Dict[str, Any], metrics: Dict[str, Any]) -> pd.DataFrame:
    budget_col = schema['budget']
    blocked_col = schema['blocked']
    month_cols = list(schema['months'].values())
    
    entity_col = schema['kdsatker'] if schema['kdsatker'] else (schema['org'][0] if schema['org'] else 'ENTITY')
    if entity_col not in df.columns:
        df['ENTITY_GROUP'] = 'All Operations'
        entity_col = 'ENTITY_GROUP'
        
    grouped = df.groupby(entity_col).agg({budget_col: 'sum', blocked_col: 'sum'}).reset_index()
    
    realized_series = []
    for entity in grouped[entity_col]:
        sub_df = df[df[entity_col] == entity]
        realized_series.append(sub_df[month_cols].sum().sum())
        
    grouped['REALIZED'] = realized_series
    grouped['UNSPENT'] = grouped[budget_col] - grouped['REALIZED']
    grouped['ABSORPTION_RATE'] = np.where(grouped[budget_col] > 0, (grouped['REALIZED'] / grouped[budget_col] * 100), 0.0)
    grouped['IMPACT_SCORE'] = grouped[blocked_col] + (grouped['UNSPENT'] * (1.0 - grouped['ABSORPTION_RATE']/100.0))
    
    return grouped.sort_values(by='IMPACT_SCORE', ascending=False)
