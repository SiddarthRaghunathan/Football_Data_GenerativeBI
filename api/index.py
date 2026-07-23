# api/index.py
import os
from functools import lru_cache

import duckdb
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckdb import DuckDbTools
from agno.tools import Toolkit

app = FastAPI()

SHEET_ID = os.getenv("SHEET_ID")
GID = os.getenv("GID", "0")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SHEET_ID:
    raise RuntimeError("Missing SHEET_ID env var")
if not GOOGLE_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY env var")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

semantic_context = """
Replace this with your real semantic_context string.
"""

class AskRequest(BaseModel):
    question: str

class ChartToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="chart_toolkit")
        self.register(self.plot_chart)

    def plot_chart(
        self,
        chart_type: str,
        title: str,
        x_label: str,
        y_label: str,
        x_data: str,
        y_data: str
    ) -> dict:
        xs = [s.strip() for s in x_data.split(",") if s.strip()]
        ys = [float(s.strip()) for s in y_data.split(",") if s.strip()]

        return {
            "chart_type": chart_type,
            "title": title,
            "x_label": x_label,
            "y_label": y_label,
            "x_data": xs,
            "y_data": ys,
        }

@lru_cache(maxsize=1)
def setup_db():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    df = pd.read_csv(url)

    con = duckdb.connect(":memory:")
    con.execute("CREATE OR REPLACE TABLE matches AS SELECT * FROM df")
    return con

@lru_cache(maxsize=1)
def build_agent():
    con = setup_db()

    agent = Agent(
        name="FootballMatchAnalyst",
        model=Gemini(id="gemma-4-31b-it"),
        tools=[
            DuckDbTools(connection=con),
            ChartToolkit(),
        ],
        instructions=[
            "You are a football match data analyst.",
            "The DuckDB database already contains a table called 'matches'. Never create or load new tables.",
            "Use this semantic model as ground truth for column meanings:",
            semantic_context,
            "Always write and run SQL against 'matches' to answer questions - never guess numbers.",
            "Only use the plot_chart tool when the user explicitly asks for a chart, graph, or visualization.",
            "When the user asks for a chart, first run a SQL query to get the aggregated data, then call the plot_chart tool with the results.",
            "Pass x_data and y_data as comma-separated strings.",
            "For weekly grouping use: date_trunc('week', CAST(DateID AS DATE))",
            "Give a concise plain-English answer and show the SQL you used.",
        ],
        markdown=True,
    )
    return agent

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/ask")
def ask(req: AskRequest):
    try:
        agent = build_agent()
        response = agent.run(req.question)
        return {
            "question": req.question,
            "answer": str(response.content) if hasattr(response, "content") else str(response),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
