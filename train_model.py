from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.train import DEFAULT_ARTIFACT_PATH, train_model


DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "historical_bookings.csv"


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Train the LightGBM model.")
	parser.add_argument("--data", default=str(DEFAULT_DATA_PATH), help="Path to historical_bookings.csv")
	parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Path to save the trained model")
	parser.add_argument(
		"--model",
		choices=["lightgbm", "random_forest"],
		default="lightgbm",
		help="Which model backend to use (default: lightgbm)",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	metrics = train_model(Path(args.data), Path(args.artifact), args.model)
	print(json.dumps(metrics, indent=2))
	print(f"Saved model to {args.artifact}")


if __name__ == "__main__":
	main()
