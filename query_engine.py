"""
Budget Intelligence Agent - DuckDB & Gemini API Natural Language Core
"""

import duckdb
import pandas as pd
import google.generativeai as genai
from typing import Dict, Any, Tuple, Optional

class BudgetQueryEngine:
    def __init__(self, df: pd.DataFrame, schema: Dict[str, Any], api_key: str):
        self.conn = duckdb.connect(database=':memory:')
        self.schema = schema
        self.df = df
        self.conn.register('budget_data', self.df)
        
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

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

    def ask_gemini_sql(self, user_question: str) -> str:
        if not self.model:
            return "SELECT * FROM budget_data LIMIT 5;"
            
        months_str = ", ".join([f"{k}: '{v}'" for k, v in self.schema['months'].items()])
        org_str = ", ".join(self.schema['org'])
        acc_str = ", ".join(self.schema['account'])
        
        prompt = f"""
You are an expert DuckDB SQL engineer. Translate the user's question into a valid DuckDB SQL query.
Table Name: 'budget_data'
Schema:
- Budget Column: '{self.schema['budget']}'
- Blocked Column: '{self.schema['blocked']}'
- Monthly Columns: {{ {months_str} }}
- Organizational Columns: [ {org_str} ]
- Account Columns: [ {acc_str} ]

Rules:
1. Total Realization for any item is computed as the sum of its monthly columns: ({' + '.join(list(self.schema['months'].values()))}).
2. Include readable text columns (like NMDEPT, NMSATKER, NMAKUN) in SELECT statements.
3. Use 'ORDER BY ... DESC LIMIT 10' for top/highest requests.
4. Return ONLY the raw SQL wrapped in a markdown code block. Do not add explanations.

User Question: "{user_question}"
"""
        response = self.model.generate_content(prompt)
        return response.text

    def generate_narrative_insight(self, user_question: str, sql_query: str, result_df: pd.DataFrame) -> str:
        if not self.model:
            return "Gemini API key not configured. Displaying raw data only."
            
        result_markdown = result_df.head(50).to_markdown(index=False)
        
        prompt = f"""
You are the Budget Intelligence Agent, advising executives.
User Question: "{user_question}"
Data Result:
{result_markdown}

Write a professional narrative analyzing this data. Address the question directly, highlight key trends, and provide 2 actionable recommendations. Never mention SQL or database table names in your response.
"""
        response = self.model.generate_content(prompt)
        return response.text

    def generate_recommendation_plan(self, bottleneck_summary: str, anomaly_summary: str) -> str:
        if not self.model:
            return "Gemini API key missing. Cannot generate AI action plans."
            
        prompt = f"""
You are the Budget Intelligence Agent. Review the following bottlenecks and anomalies:
Top Bottlenecks:
{bottleneck_summary}
Detected Anomalies:
{anomaly_summary}

Generate a comprehensive Strategic Acceleration Plan in Markdown format. Include an Executive Summary, a Prioritized Intervention Matrix for the bottlenecks, and Risk Mitigation for the anomalies.
"""
        response = self.model.generate_content(prompt)
        return response.text
