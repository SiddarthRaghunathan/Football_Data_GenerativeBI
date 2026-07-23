
## GenBI — Football Match Analytics with Agno AI
A Generative BI (text-to-SQL) project that lets you ask natural-language questions over 38,000+ football matches and get instant answers, SQL queries, and visualizations — powered by Google Gemini and the Agno agent framework.

## What It Does
Loads live football match data from a Google Sheet (38,564 rows, 852 leagues)

Stores it in DuckDB for fast in-memory SQL queries

Uses an Agno AI agent with Google Gemini to translate plain-English questions into SQL

Automatically runs the SQL, summarizes results, and renders charts when requested
## Architecture
Google Sheet (CSV export) -> DuckDB (`genbi.duckdb`) -> Semantic model (`semantic_model.yaml`)
-> LLM text-to-SQL (`app.py`) -> Answer

## Files
- `matches_raw.csv` — raw exported data
- `genbi.duckdb` — DuckDB database with `matches` table loaded
- `semantic_model.yaml` — schema + business metric definitions fed to the LLM as grounding context
- `app.py` — CLI: takes a natural-language question, generates SQL via LLM, runs it on DuckDB, returns a plain-English answer
- `requirements.txt` — pip dependencies
