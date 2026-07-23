
# GenBI Sample Project — Football Match Analytics

## What this is
A minimal Generative BI (text-to-SQL) sample project built on your Google Sheet data
(38564 rows, 852 leagues, dates 20260301–20260707).

## Architecture
Google Sheet (CSV export) -> DuckDB (`genbi.duckdb`) -> Semantic model (`semantic_model.yaml`)
-> LLM text-to-SQL (`app.py`) -> Answer

## Files
- `matches_raw.csv` — raw exported data
- `genbi.duckdb` — DuckDB database with `matches` table loaded
- `semantic_model.yaml` — schema + business metric definitions fed to the LLM as grounding context
- `app.py` — CLI: takes a natural-language question, generates SQL via LLM, runs it on DuckDB, returns a plain-English answer
- `requirements.txt` — pip dependencies

## How to run
1. `pip install -r requirements.txt`
2. `export OPENAI_API_KEY=...`
3. `python app.py "Which league had the most matches in June 2026?"`

## Extending this into a real GenBI product
- Swap OpenAI for Claude/LangChain agent with tool-calling for multi-step queries.
- Add a Streamlit or Next.js chat UI on top of `app.py` logic.
- Add query validation/guardrails (read-only DuckDB connection already enforced).
- Add caching layer (e.g. cache SQL for repeated questions).
- Add a feedback loop: log (question, generated_sql, was_correct) for fine-tuning few-shot examples.
