import os
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckdb import DuckDbTools
from agno.tools import Toolkit

app = FastAPI()
handler = app

DB_PATH = "/tmp/genbi.duckdb"
CHART_DIR = Path("/tmp/charts")
CHART_DIR.mkdir(parents=True, exist_ok=True)

SHEET_ID = "1Op6IKbc0IICuQCiRYjf94MGxXfDiE-IxGcL_lGfDw4c"
GID = "0"

semantic_context = """
model: football_matches
table: matches
grain: one row per match (MatchId)
columns:
  DateID: match date as YYYYMMDD integer
  League: league/competition name, includes country prefix
  MatchId: unique match identifier
  Home: home team name
  Away: away team name
  HomeLeaguePosition: home team league position at match time (often null)
  AwayLeaguePosition: away team league position at match time (often null)
  Handicap: Asian handicap line for home team (negative = home favored)
  Score: format 'FT (HT)', e.g. '2 - 1 (1 - 0)'
  Corners: format 'home-away (HThome-HTaway)'
  DangerousAttack: format 'home-away (HThome-HTaway)'
  HomeRedCard / HomeYellowCard / AwayRedCard / AwayYellowCard: card counts
notes:
  - Score, Corners, DangerousAttack are strings; use split_part() in SQL to parse.
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

        fig, ax = plt.subplots(figsize=(10, 5))

        if chart_type == "line":
            ax.plot(xs, ys, marker="o", linewidth=2)
        elif chart_type == "bar":
            ax.bar(xs, ys)
        elif chart_type == "scatter":
            ax.scatter(xs, ys)
        else:
            return {"error": f"Unsupported chart type: {chart_type}"}

        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        filename = f"chart_{len(list(CHART_DIR.glob('*.png')))}.png"
        filepath = CHART_DIR / filename
        fig.savefig(filepath, dpi=150)
        plt.close(fig)

        return {
            "chart_type": chart_type,
            "title": title,
            "path": str(filepath),
            "x_data": xs,
            "y_data": ys,
        }

def get_google_api_key():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY env var")
    os.environ["GOOGLE_API_KEY"] = api_key
    return api_key

@lru_cache(maxsize=1)
def setup_db():
    get_google_api_key()

    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    df = pd.read_csv(url)

    try:
        duckdb.close(DB_PATH)
    except:
        pass

    con = duckdb.connect(DB_PATH)
    con.execute("CREATE OR REPLACE TABLE matches AS SELECT * FROM df")
    count = con.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    con.close()

    return {"db_path": DB_PATH, "row_count": count}

@lru_cache(maxsize=1)
def build_agent():
    db_info = setup_db()

    agent = Agent(
        name="FootballMatchAnalyst",
        model=Gemini(id="gemma-4-31b-it"),
        tools=[
            DuckDbTools(db_path=db_info["db_path"], read_only=True),
            ChartToolkit(),
        ],
        instructions=[
            "You are a football match data analyst.",
            "The DuckDB database already contains a table called 'matches'. Never create or load new tables.",
            "Use this semantic model as ground truth for column meanings:",
            semantic_context,
            "Always write and run SQL against 'matches' to answer questions — never guess numbers.",
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
    try:
        db_info = setup_db()
        return {
            "ok": True,
            "rows": db_info["row_count"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ask")
def ask(req: AskRequest):
    try:
        agent = build_agent()
        response = agent.run(req.question)
        answer = getattr(response, "content", str(response))

        return {
            "question": req.question,
            "answer": str(answer),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
