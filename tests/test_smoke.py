"""Smoke tests. These pass on a fresh clone and they must stay passing.

Nothing here tests your model. These check that the service starts, that
`/health` tells the truth, and that the artifact on disk matches the data it
was trained from. They are the tests that catch "I refactored something and
now the whole thing is broken" before a reviewer does.

This file is also the worked example. `tests/test_contract.py` is stubs,
and the quality bar you are aiming for there is this: one behavior per
test, a name that states the claim, and an assertion message that tells the
next person what to do about a failure.

Run:  pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import API_VERSION, SERVICE_NAME, app
from app.model import ARTIFACT_PATH, FEATURE_ORDER, load_artifact

DATA_PATH = Path("data/support_tickets.csv")

TRAIN_FIRST = (
    f"No artifact at {ARTIFACT_PATH}. Run `python train.py` before pytest. "
    "The artifact is gitignored on purpose, so a fresh clone has to train "
    "once."
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# --- the service starts ----------------------------------------------------

def test_health_returns_200(client):
    assert client.get("/health").status_code == 200


def test_health_reports_the_documented_fields(client):
    """`/health` is a contract too. Something monitors it."""
    body = client.get("/health").json()
    assert set(body) == {"status", "service", "version", "model"}
    assert body["service"] == SERVICE_NAME
    assert body["version"] == API_VERSION
    assert body["status"] in {"ok", "degraded"}


def test_health_reports_model_status_not_just_liveness(client):
    """A health check that ignores its dependencies is decorative.

    The model block has to say whether the artifact loaded, and if it did,
    which version, so that a prediction can be traced to a model.
    """
    model = client.get("/health").json()["model"]
    assert set(model) >= {"loaded", "version", "path"}, (
        f"/health model block is missing fields: {sorted(model)}"
    )
    assert model["loaded"] is True, TRAIN_FIRST
    assert model["version"], "Artifact loaded but reports no version."


def test_docs_page_is_reachable(client):
    """The `/docs` page is the deliverable a recruiter opens. If this fails
    in CI it is also broken in production."""
    assert client.get("/docs").status_code == 200


def test_openapi_documents_both_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/health" in paths
    assert "/predict" in paths, (
        "/predict vanished from the OpenAPI schema, which means it is also "
        "gone from the /docs page a reviewer will use."
    )


# --- the artifact on disk is usable ---------------------------------------

def test_artifact_loads(client):
    artifact = load_artifact()
    assert artifact is not None, TRAIN_FIRST
    assert "model" in artifact, (
        f"Artifact has no 'model' key. Keys present: {sorted(artifact)}"
    )


def test_artifact_records_its_own_provenance():
    """An artifact you cannot date or version is not auditable. Six months
    from now this is the difference between "which model made that call"
    and a shrug."""
    artifact = load_artifact()
    assert artifact is not None, TRAIN_FIRST
    for key in ("version", "trained_at", "features"):
        assert artifact.get(key), f"Artifact is missing {key!r}."


def test_serving_feature_order_matches_the_artifact():
    """The estimator was fit on a matrix, and a matrix has no column names.

    If `FEATURE_ORDER` in the serving code drifts from the order training
    used, every prediction is computed from features assigned to the wrong
    coefficients, and nothing raises. This test is cheap insurance against
    a class of bug that is invisible from the outside.
    """
    artifact = load_artifact()
    assert artifact is not None, TRAIN_FIRST
    assert artifact["features"] == FEATURE_ORDER, (
        "Serving feature order does not match training feature order.\n"
        f"  training: {artifact['features']}\n"
        f"  serving : {FEATURE_ORDER}"
    )


def test_estimator_accepts_a_row_of_the_expected_width():
    artifact = load_artifact()
    assert artifact is not None, TRAIN_FIRST
    row = [[0.0] * len(FEATURE_ORDER)]
    assert artifact["model"].predict_proba(row).shape == (1, 2)


# --- the committed data is intact -----------------------------------------

def test_dataset_is_committed_and_has_the_expected_columns():
    """A reviewer should not have to find a dataset."""
    assert DATA_PATH.exists(), f"{DATA_PATH} is missing."
    with DATA_PATH.open() as f:
        header = next(csv.reader(f))
    for column in [*FEATURE_ORDER, "escalated"]:
        assert column in header, f"{DATA_PATH} has no {column!r} column."
