from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Follow-up answers use the analysis payload returned by /validate.
from agents.advisor_agent import answer_follow_up
from report_generator import build_validation_report, report_filename

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


class AdvisorRequest(BaseModel):
    question: str
    idea: str
    market: dict
    competitors: dict
    swot: dict
    mvp: dict
    gtm: dict


@app.get("/")
def home():
    return {"message": "Litmus - AI Startup Idea Validator API", "milestone": 2}


@app.post("/validate")
def validate(request: IdeaRequest):
    return run_pipeline(request.idea)


@app.post("/advisor")
def advise(request: AdvisorRequest):
    return answer_follow_up(
        request.question,
        request.idea,
        request.market,
        request.competitors,
        request.swot,
        request.mvp,
        request.gtm,
    )


@app.post("/report")
def generate_report(validation_result: dict):
    from fastapi.responses import HTMLResponse

    content = build_validation_report(validation_result)
    filename = report_filename(validation_result.get("idea", ""))
    return HTMLResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )