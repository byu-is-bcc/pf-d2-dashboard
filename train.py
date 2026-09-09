"""
Trains the ticket escalation model and writes the serialized artifact.

The dataset is a small committed synthetic file so this repository runs on
a fresh clone with no downloads and no credentials. The model is a plain
logistic regression, because the modeling is not what this project is
about: standing the result up behind an API that a stranger can call is.

Six features, all knowable at the moment you are predicting, and a binary
target. Features are standardized before fitting, which matters here
because `account_seats` runs into the thousands while `plan_tier_rank`
runs one through four, and a model fit on the raw columns would read that
difference as importance.

Run:  python train.py
Out:  models/model.joblib

Swap in your own dataset once this works end to end. Keep the shape:
features, a target, a split, a fit, a held-out number, an artifact.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

SEED = 27  # Fixed everywhere, so your run matches everyone else's.
TEST_SIZE = 0.25

DATA_PATH = Path("data/support_tickets.csv")
MODEL_DIR = Path("models")
ARTIFACT_PATH = MODEL_DIR / "model.joblib"
MODEL_VERSION = "0.1.0"

FEATURE_COLUMNS = [
    "ticket_age_hours",
    "customer_tenure_days",
    "prior_tickets_90d",
    "message_count",
    "account_seats",
    "plan_tier_rank",
]
TARGET_COLUMN = "escalated"


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    # Split before fitting anything, including the scaler. Fitting a scaler
    # on the full dataset leaks the test set's distribution into training
    # and is the reason a lot of reported numbers do not survive contact
    # with new data.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED, stratify=y
    )

    scaler = StandardScaler()
    scaler.fit(X_train)

    model = LogisticRegression(max_iter=1_000, random_state=SEED)
    model.fit(scaler.transform(X_train), y_train)

    probability = model.predict_proba(scaler.transform(X_test))[:, 1]
    prediction = (probability >= 0.5).astype(int)

    accuracy = accuracy_score(y_test, prediction)
    auc = roc_auc_score(y_test, probability)
    positive_rate = float(y.mean())
    baseline = max(positive_rate, 1 - positive_rate)

    MODEL_DIR.mkdir(exist_ok=True)
    artifact = {
        "model": model,
        "features": FEATURE_COLUMNS,
        "version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "holdout_accuracy": round(float(accuracy), 4),
        "holdout_auc": round(float(auc), 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    joblib.dump(artifact, ARTIFACT_PATH)

    print(f"Rows: {len(df):,}  train: {len(X_train)}  held out: {len(X_test)}")
    print(f"Escalation rate: {positive_rate:.1%}")
    print(f"Majority-class baseline accuracy: {baseline:.1%}")
    print(f"Held-out accuracy: {accuracy:.1%}")
    print(f"Held-out ROC AUC: {auc:.3f}")
    print()
    print(f"Wrote {ARTIFACT_PATH}")
    print(f"Artifact keys: {sorted(k for k in artifact)}")
    print()
    print(
        "Those are training-path numbers. Whether the service reproduces "
        "them is a separate question, and it is the one this project is "
        "about. See the README."
    )


if __name__ == "__main__":
    main()
