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
            self.model_name = "llama3-70b-8192" # Fast, high reasoning capability model
        else:
            self.client = None

    def execute_sql(self, sql_query: str) -> Tuple[pd.DataFrame, Optional[str]]:
        try:
            clean_sql = sql_query.strip()
            # Clean out markdown formatting if the LLM provided it
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
2. Always select readable text columns (like NMDEPT, NMSATKER, NMAKUN) instead of just IDs.
3. Use 'ORDER BY ... DESC LIMIT 10' for top/highest requests.
4. Return ONLY the raw SQL wrapped in a markdown code block. Do not add any conversational text.

User Question: "{user_question}"
"""
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                temperature=0.0 # Deterministic SQL output
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"SELECT 'Error generating SQL via Groq' as Error;"

    def generate_narrative_insight(self, user_question: str, sql_query: str, result_df: pd.DataFrame) -> str:
        if not self.client:
            return "Groq API key not configured. Displaying raw data only."
            
        result_markdown = result_df.head(50).to_markdown(index=False)
        
        system_prompt = "You are the Budget Intelligence Agent, advising government executives."
        user_prompt = f"""
User Question: "{user_question}"
Data Result:
{result_markdown}

Write a professional narrative analyzing this data. Address the question directly, highlight key trends or anomalies, and provide 2 actionable recommendations. Never mention SQL or database table names in your response.
"""
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return "Narrative generation failed."

    def generate_recommendation_plan(self, bottleneck_summary: str, anomaly_summary: str) -> str:
        if not self.client:
            return "Groq API key missing. Cannot generate AI action plans."
            
        system_prompt = "You are the Budget Intelligence Agent."
        user_prompt = f"""
Review the following bottlenecks and anomalies:

Top Bottlenecks:
{bottleneck_summary}

Detected Anomalies:
{anomaly_summary}

Generate a comprehensive Strategic Acceleration Plan in Markdown format. Include:
1. An Executive Summary.
2. A Prioritized Intervention Matrix for the bottlenecks.
3. Risk Mitigation steps for the anomalies.
"""
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            return "Recommendation generation failed."
