from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.web_search_agent import search_idea

app = FastAPI(title="AI Startup Idea Validator")

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
    return {"message": "AI Startup Idea Validator API"}


@app.post("/validate")
def validate(request: IdeaRequest):
    return search_idea(request.idea)