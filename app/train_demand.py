from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.demand_model import DEFAULT_ARTIFACT_PATH, DEFAULT_PROPHET_ARTIFACT_PATH, train_demand_model, train_prophet_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the demand forecasting model.")
    parser.add_argument("--data", required=True, help="Path to historical_bookings.csv")
    parser.add_argument("--artifact", default=None, help="Path to save the trained demand model")
    parser.add_argument("--method", choices=["lightgbm", "prophet"], default="prophet", help="Training method to use")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifact = args.artifact
    if artifact is None:
        artifact = str(DEFAULT_PROPHET_ARTIFACT_PATH if args.method == "prophet" else DEFAULT_ARTIFACT_PATH)

    if args.method == "prophet":
        metrics = train_prophet_model(Path(args.data), Path(artifact))
    else:
        metrics = train_demand_model(Path(args.data), Path(artifact))

    print(json.dumps(metrics, indent=2))
    print(f"Saved demand model to {artifact}")


if __name__ == "__main__":
    main()