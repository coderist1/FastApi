from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.demand_model import DEFAULT_ARTIFACT_PATH, train_demand_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the demand forecasting model.")
    parser.add_argument("--data", required=True, help="Path to historical_bookings.csv")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Path to save the trained demand model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = train_demand_model(Path(args.data), Path(args.artifact))
    print(json.dumps(metrics, indent=2))
    print(f"Saved demand model to {args.artifact}")


if __name__ == "__main__":
    main()