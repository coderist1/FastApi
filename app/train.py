from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.features import prepare_feature_frame


DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "model" / "lightgbm_model.pkl"



def train_model(data_path: Path, artifact_path: Path, model_name: str = "random_forest") -> dict[str, float | str]:
	dataset = pd.read_csv(data_path)
	if "Car_Cancellation" not in dataset.columns:
		raise ValueError("The dataset must contain a Car_Cancellation column.")

	dataset = dataset.dropna(subset=["Car_Cancellation"]).copy()
	target = pd.to_numeric(dataset["Car_Cancellation"], errors="coerce").fillna(0).astype(int)
	features = prepare_feature_frame(dataset)

	X_train, X_test, y_train, y_test = train_test_split(
		features,
		target,
		test_size=0.2,
		random_state=42,
		stratify=target,
	)

	# choose model by name so we can support LightGBM or RandomForest
	if model_name == "lightgbm":
		model = LGBMClassifier(
			n_estimators=200,
			random_state=42,
			class_weight="balanced",
			n_jobs=-1,
		)
	else:
		model = RandomForestClassifier(
			n_estimators=200,
			random_state=42,
			class_weight="balanced_subsample",
			n_jobs=-1,
		)

	pipeline = Pipeline(steps=[("imputer", SimpleImputer(strategy="median")), ("model", model)])

	pipeline.fit(X_train, y_train)
	predictions = pipeline.predict(X_test)
	probabilities = pipeline.predict_proba(X_test)
	positive_index = list(pipeline.named_steps["model"].classes_).index(1)

	metrics = {
		"accuracy": accuracy_score(y_test, predictions),
		"f1": f1_score(y_test, predictions, zero_division=0),
		"roc_auc": roc_auc_score(y_test, probabilities[:, positive_index]),
		"rows": int(len(dataset)),
	}

	artifact_path.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump(
		{
			"pipeline": pipeline,
			"feature_columns": list(features.columns),
			"metrics": metrics,
			"model_name": model_name,
		},
		artifact_path,
	)
	return metrics


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Train the car cancellation model.")
	parser.add_argument("--data", required=True, help="Path to SAR Rental.csv")
	parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT_PATH), help="Path to save the trained model")
	parser.add_argument(
		"--model",
		choices=["random_forest", "lightgbm"],
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