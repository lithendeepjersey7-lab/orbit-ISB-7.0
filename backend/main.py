from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# The pipeline runs the search agent, then the market and competitor
# agents at the same time. Aliased because this file already has a
# route function called validate().
from agents.pipeline import validate as run_pipeline

app = FastAPI(title="Litmus - AI Startup Idea Validator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IdeaRequest(BaseModel):
    idea: str


@app.get("/")
def home():
    return {"message": "Litmus - AI Startup Idea Validator API", "milestone": 2}


@app.post("/validate")
def validate(request: IdeaRequest):
    return run_pipeline(request.idea)