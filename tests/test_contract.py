"""Contract tests. These fail until you write them. That is intentional.

A contract test asserts what a caller is allowed to depend on: the shape of
a success response, and what happens when the request is wrong. The
difference between this and "testing the model" is that these do not care
whether the prediction is any good, only that the interface behaves as
documented.

`tests/test_smoke.py` is the worked example. Match its bar: one behavior
per test, a name that states the claim, an assertion message that tells the
next person what to do.

Run:  pytest tests/test_contract.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

VALID_TICKET = {
    "ticket_age_hours": 36.0,
    "customer_tenure_days": 820,
    "prior_tickets_90d": 3,
    "message_count": 7,
    "account_seats": 240,
    "plan_tier_rank": 2,
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_predict_returns_the_documented_shape(client):
    """A valid request returns 200 and exactly the documented fields.

    TODO(you): write this.

    POST `VALID_TICKET` to `/predict` and assert on the response, not on
    the prediction. Worth covering:

      - status code 200
      - the response has exactly the keys `PredictionResponse` declares,
        no more. Extra keys are how a debugging field ends up in a public
        contract permanently.
      - `probability` is a float between 0 and 1
      - `escalated` is a bool, and it agrees with `probability` at whatever
        threshold you documented
      - `model_version` is a non-empty string

    Do not assert a specific probability. That couples your test suite to a
    particular trained artifact and it will break the next time you retrain
    for a reason that has nothing to do with the contract.
    """
    pytest.fail(
        "Not written yet. Assert the /predict success contract. See the "
        "TODO in this test."
    )


def test_predict_rejects_malformed_input(client):
    """A request that violates the schema is refused, not guessed at.

    TODO(you): write this.

    At least these, each as its own assertion or its own test:

      - a missing required field
      - a field of the wrong type, such as `"seven"` for `message_count`
      - a value outside the declared bounds, such as a negative
        `ticket_age_hours` or a `plan_tier_rank` of 9
      - an entirely empty body

    FastAPI returns 422 for schema violations without you writing anything,
    which is exactly why this test matters: you are asserting that the
    bounds you declared in `PredictionRequest` are the bounds you meant.
    Loosen a `Field(ge=...)` by accident and this test is what notices.

    The failure mode to rule out is a service that accepts nonsense and
    returns a confident number for it.
    """
    pytest.fail(
        "Not written yet. Assert that malformed input is refused. See the "
        "TODO in this test."
    )


def test_training_and_serving_agree_on_the_same_rows(client):
    """The same input scores the same through both paths.

    TODO(you): write this, and write it before you deploy.

    This is the test the README's bug section is about, and it is the one
    that would have caught the bug this repository ships with.

    The shape of it:

      1. Read a handful of rows out of `data/support_tickets.csv`.
      2. Score them the way `train.py` scores its held-out set.
      3. Score the same rows by POSTing them to `/predict`.
      4. Assert the probabilities match to a tight tolerance. Not "close
         enough to look right", tight, because there is no legitimate
         reason for two paths running the same model on the same row to
         disagree at all.

    Whether step 2 is easy is itself the finding. If reproducing the
    training path means re-running training, then the artifact does not
    contain everything the prediction depends on, and this test is telling
    you something about your design rather than about your arithmetic.

    Once you have fixed the underlying problem, this test is the thing that
    keeps it fixed. Every retrain runs it.
    """
    pytest.fail(
        "Not written yet. Assert that the training path and the serving "
        "path produce the same predictions for the same rows. See the "
        "README section titled 'This repository ships with a bug in it'."
    )
