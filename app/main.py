"""
D2 — Ship the Model.

A trained classifier standing behind an HTTP API. Two endpoints: `/health`
so a platform and a human can both tell whether the thing is alive, and
`/predict` so a stranger can score a ticket from the interactive docs page
without installing anything.

`/health` is finished. `/predict` is not, and finishing it is the
assignment. Read the TODOs in it, then read the section of the README
titled "This repository ships with a bug in it" before you trust any
number that comes out of it.

Run:  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.model import model_info

API_VERSION = "0.1.0"
SERVICE_NAME = "ticket-escalation-api"

app = FastAPI(
    title="Ticket Escalation API",
    description=(
        "Portfolio Factory D2 starter. Predicts whether a support ticket "
        "will be escalated.\n\n"
        "`/health` reports service and model status. `/predict` is a stub "
        "until you wire it up. This page is the deliverable a reviewer "
        "opens, so the field descriptions below are worth writing well."
    ),
    version=API_VERSION,
)


# ---------------------------------------------------------------------------
# Schemas
#
# These are the contract. Whatever you change here changes the `/docs` page
# a reviewer reads, so treat the descriptions as documentation rather than
# as filler.
# ---------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    """One support ticket, as it looks at the moment of prediction."""

    ticket_age_hours: float = Field(
        ge=0, le=2_000,
        description="Hours since the ticket was opened.",
        examples=[36.0],
    )
    customer_tenure_days: int = Field(
        ge=0, le=20_000,
        description="Days the customer account has existed.",
        examples=[820],
    )
    prior_tickets_90d: int = Field(
        ge=0, le=500,
        description="Tickets this customer opened in the previous 90 days.",
        examples=[3],
    )
    message_count: int = Field(
        ge=1, le=1_000,
        description="Messages exchanged on this ticket so far.",
        examples=[7],
    )
    account_seats: int = Field(
        ge=1, le=100_000,
        description="Licensed seats on the account.",
        examples=[240],
    )
    plan_tier_rank: int = Field(
        ge=1, le=4,
        description="Plan tier, 1 (free) through 4 (enterprise).",
        examples=[2],
    )


class PredictionResponse(BaseModel):
    """What `/predict` returns. Your contract test asserts this shape."""

    # Pydantic reserves the `model_` prefix for its own methods. Opting out
    # of the protected namespace is the standard way to keep a field named
    # `model_version`, which is the name a client actually wants to read.
    model_config = ConfigDict(protected_namespaces=())

    escalated: bool = Field(
        description="The predicted class at the decision threshold.",
    )
    probability: float = Field(
        ge=0, le=1,
        description="Predicted probability of escalation.",
    )
    model_version: str = Field(
        description="Version of the artifact that produced this prediction. "
                    "A prediction you cannot trace back to a model is not "
                    "auditable.",
    )


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    service: str
    version: str
    model: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Service and model status.

    Reports whether the artifact actually loaded and which version it is. A
    health endpoint that returns 200 without touching its dependencies is
    decorative: this one answers the question you actually have at 2am,
    which is whether the process is up but serving nothing.

    Returns 200 even when the model is missing, with `status: "degraded"`.
    A 503 would be defensible, and it would also make most free-tier
    platforms mark the deployment as failed and stop showing you logs.
    """
    info = model_info()
    return HealthResponse(
        status="ok" if info["loaded"] else "degraded",
        service=SERVICE_NAME,
        version=API_VERSION,
        model=info,
    )


@app.post("/predict", response_model=PredictionResponse, tags=["predict"])
def predict(payload: PredictionRequest) -> PredictionResponse:
    """Score one ticket.

    TODO(you): wire this up. The request and response contracts above are
    already defined, and the helpers you need are in `app/model.py`.

      1. Load the artifact. `app.model.load_artifact()` returns the dict
         `train.py` wrote, or None if training has not been run. Decide
         what this endpoint should do when the model is missing, and make
         `/docs` say so.

      2. Turn the payload into a feature row. `app.model.FEATURE_ORDER`
         gives the column order the estimator was fit on and
         `app.model.build_feature_vector()` will assemble the row for you.

      3. Get a probability out of the estimator, convert it to a class at
         whatever threshold you can defend, and return a
         `PredictionResponse`. Put the artifact's version on it.

      4. Decide what happens on a request that validates but is nonsense,
         such as a two-year-old ticket with one message. Whatever you
         decide, one of your contract tests should assert it.

    Then, before you deploy: score the same rows two ways, once through the
    training code and once through this endpoint, and check that the two
    agree. See the README. They do not agree right now.
    """
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "Not implemented. See the TODOs in app/main.py:predict.",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
