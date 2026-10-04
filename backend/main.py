from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Follow-up answers use the analysis payload returned by /validate.
from agents.advisor_agent import answer_follow_up
from agents.gemini_retry import take_failure
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
    # /validate returns null for any agent that failed. These stay optional so
    # the advisor can still answer from whatever analysis does exist, instead
    # of FastAPI rejecting the whole request with a 422.
    market: Optional[dict] = None
    competitors: Optional[dict] = None
    swot: Optional[dict] = None
    mvp: Optional[dict] = None
    gtm: Optional[dict] = None


@app.get("/")
def home():
    return {"message": "Litmus - AI Startup Idea Validator API", "milestone": 4}


@app.post("/validate")
def validate(request: IdeaRequest):
    return run_pipeline(request.idea)


@app.post("/advisor")
def advise(request: AdvisorRequest):
    answer = answer_follow_up(
        request.question,
        request.idea,
        request.market,
        request.competitors,
        request.swot,
        request.mvp,
        request.gtm,
    )
    if answer is None:
        # Return a real error status, not a 200 with a null body. The client
        # can then tell a failed answer apart from a missing server.
        failure = take_failure()
        if failure:
            raise HTTPException(status_code=503, detail="Advisor unavailable: " + failure)
        raise HTTPException(
            status_code=502,
            detail="Advisor returned an empty or invalid answer. Please try again.",
        )
    return answer


@app.post("/report")
def generate_report(validation_result: dict):
    from fastapi.responses import HTMLResponse

    content = build_validation_report(validation_result)
    filename = report_filename(validation_result.get("idea", ""))
    return HTMLResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )