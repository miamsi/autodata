# Budget Intelligence Agent 🏛️

A zero-infrastructure, completely in-memory AI application designed to provide sub-second financial aggregations and executive LLM guidance via the Gemini API and DuckDB.

## 🚀 Deployment Instructions (Streamlit Community Cloud)

1. Create a fresh GitHub repository.
2. Upload the following files directly to the root of the repository:
   - `app.py`
   - `analytics.py`
   - `query_engine.py`
   - `report_generator.py`
   - `schema_detector.py`
   - `requirements.txt`
3. Log into [Streamlit Community Cloud](https://share.streamlit.io/).
4. Click **New app**, point it to your repository, and set the entry point to `app.py`.
5. Before clicking deploy, click on **Advanced settings**.
6. In the **Secrets** text box, paste your API key exactly like this:
   ```toml
   GEMINI_API_KEY = "YOUR_ACTUAL_KEY_HERE"
