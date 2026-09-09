"""
Model loading and feature preparation for the prediction service.

Everything the request path needs to turn a JSON body into something the
estimator will accept lives here. `app/main.py` handles HTTP and this file
handles the model, which keeps the endpoint readable and keeps the model
testable without spinning up a server.

The artifact is written by `train.py` and is not committed. Run training
once before you start the service, or `/health` will tell you the model is
missing.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import joblib

# Order matters. The estimator was fit on a matrix with these columns in
# this order and has no idea what any of them are called, so a request that
# arrives as a dict has to be flattened back into this sequence.
FEATURE_ORDER = [
    "ticket_age_hours",
    "customer_tenure_days",
    "prior_tickets_90d",
    "message_count",
    "account_seats",
    "plan_tier_rank",
]

ARTIFACT_PATH = Path(os.getenv("MODEL_PATH", "models/model.joblib"))


# The service standardizes each feature before the model sees it, the same
# way training did. Values are the per-feature (mean, std) pairs from the
# training run.
FEATURE_SCALING: dict[str, tuple[float, float]] = {
    "ticket_age_hours": (24.0, 18.0),
    "customer_tenure_days": (1100.0, 640.0),
    "prior_tickets_90d": (2.0, 1.4),
    "message_count": (5.5, 2.2),
    "account_seats": (260.0, 900.0),
    "plan_tier_rank": (1.9, 0.9),
}


@lru_cache(maxsize=1)
def load_artifact() -> dict | None:
    """Load and cache the serialized artifact, or None if it is not there.

    Returning None rather than raising is deliberate. A service that
    refuses to start because a file is missing tells you nothing over HTTP.
    A service that starts and reports `model_loaded: false` on `/health`
    tells you exactly what is wrong from a browser.
    """
    if not ARTIFACT_PATH.exists():
        return None
    return joblib.load(ARTIFACT_PATH)


def model_info() -> dict:
    """Model status for `/health`. Never raises."""
    artifact = load_artifact()
    if artifact is None:
        return {
            "loaded": False,
            "version": None,
            "trained_at": None,
            "features": None,
            "path": str(ARTIFACT_PATH),
        }
    return {
        "loaded": True,
        "version": artifact.get("version"),
        "trained_at": artifact.get("trained_at"),
        "features": artifact.get("features"),
        "path": str(ARTIFACT_PATH),
    }


def build_feature_vector(features: Mapping[str, float]) -> list[float]:
    """Turn a validated request body into the row the estimator expects.

    Standardizes each value and returns them in `FEATURE_ORDER`.
    """
    row: list[float] = []
    for name in FEATURE_ORDER:
        if name not in features:
            raise KeyError(f"Missing feature: {name}")
        mean, std = FEATURE_SCALING[name]
        row.append((float(features[name]) - mean) / std)
    return row
