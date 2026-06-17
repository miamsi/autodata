"""
Budget Intelligence Agent - Executive Report Compiling Framework
"""

import pandas as pd
from typing import Dict, Any

def compile_executive_report(metrics: Dict[str, Any], forecast: Dict[str, Any], bottlenecks_df: pd.DataFrame, anomalies_df: pd.DataFrame, ai_recommendations: str) -> str:
    top_bottlenecks = bottlenecks_df.head(5).to_markdown(index=False)
    
    anomaly_summary_counts = {
        'Deficits': int(anomalies_df['ANOMALY_DEFICIT'].sum()),
        'Low Absorption': int(anomalies_df['ANOMALY_LOW_ABSORPTION'].sum()),
        'Spending Spikes': int(anomalies_df['ANOMALY_SPIKE'].sum()),
        'High Blocked': int(anomalies_df['ANOMALY_HIGH_BLOKIR'].sum())
    }
    
    report_md = f"""# EXECUTIVE BUDGET INTELLIGENCE BRIEF
Generated automatically by the Budget Intelligence Agent

## 1. Macro Executive Overview
Total Budget Allocation: **IDR {metrics['total_budget']:,.2f}**
Year-to-Date Realization: **IDR {metrics['total_realization']:,.2f}** ({metrics['absorption_rate']:.2f}%)
Administratively Blocked: **IDR {metrics['total_blocked']:,.2f}** ({metrics['blocked_rate']:.2f}%)

## 2. Year-End Run-Rate Projections
- **Projected Year-End Realization**: IDR {forecast['forecast_eoy_realization']:,.2f}
- **Projected Final Absorption Rate**: {forecast['forecast_absorption_rate']:.2f}%
- **Estimated Under-Absorption Risk**: IDR {forecast['under_absorption']:,.2f}
- **December Backloading Risk Index**: {forecast['dec_concentration_pct']:.2f}% concentrated

## 3. Structural Operational Gridlocks (Top 5 Bottlenecks)
{top_bottlenecks}

## 4. Institutional Vulnerabilities Summary
- **Lines with Deficit Exposure**: {anomaly_summary_counts['Deficits']}
- **High-Allocation / Sluggish Lines**: {anomaly_summary_counts['Low Absorption']}
- **Unusual Spending Spikes**: {anomaly_summary_counts['Spending Spikes']}
- **Excessive Admin Lock-up (>20%)**: {anomaly_summary_counts['High Blocked']}

## 5. Strategic Interventions & Acceleration Action Plan
{ai_recommendations}
---
*Report End. Confidential.*
"""
    return report_md
