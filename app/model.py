from pathlib import Path
from datetime import date, datetime, time, timedelta

import joblib
import pandas as pd

from app.features import prepare_feature_frame


DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "model" / "lightgbm_model.pkl"


class LightGBMModel:
    def __init__(self, artifact_path: Path | str = DEFAULT_ARTIFACT_PATH):
        self.artifact_path = Path(artifact_path)
        self.reload()

    def reload(self):
        if not self.artifact_path.exists():
            raise FileNotFoundError(
                f"Trained LightGBM model not found at {self.artifact_path}. Run `python -m app.train --data <csv> --model lightgbm` first."
            )

        payload = joblib.load(self.artifact_path)
        if not isinstance(payload, dict) or "pipeline" not in payload:
            raise ValueError("Unexpected model artifact format. Retrain with `python -m app.train --model lightgbm`.")

        self.pipeline = payload["pipeline"]
        self.feature_columns = payload.get("feature_columns", [])
        self.model_name = payload.get("model_name", "lightgbm")
        if self.model_name != "lightgbm":
            raise ValueError(f"Expected a LightGBM artifact, found {self.model_name!r}.")

    def predict(self, booking: dict):
        frame = pd.DataFrame([booking])
        features = prepare_feature_frame(frame)
        if self.feature_columns:
            features = features.reindex(columns=self.feature_columns)

        prediction = int(self.pipeline.predict(features)[0])
        probabilities = self.pipeline.predict_proba(features)[0]
        class_index = list(self.pipeline.named_steps["model"].classes_).index(1)
        score = float(probabilities[class_index])
        label = "Cancelled" if prediction == 1 else "Not Cancelled"
        return {"label": label, "score": score}

    def predict_demand(
        self,
        start_date: date,
        end_date: date,
        from_area_id: int = 0,
        vehicle_model_id: int = 0,
        travel_type_id: int | None = None,
    ):
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")

        daily_predictions = []
        total_predicted_bookings = 0

        day = start_date
        while day <= end_date:
            start_dt = datetime.combine(day, time(hour=10))
            end_dt = start_dt + timedelta(hours=6)
            booking_created_dt = start_dt - timedelta(hours=24)

            sample_booking = {
                "vehicle_model_id": vehicle_model_id,
                "package_id": 1,
                "travel_type_id": 1 if travel_type_id is None else travel_type_id,
                "from_area_id": from_area_id,
                "to_area_id": 0,
                "from_city_id": 0,
                "to_city_id": 0,
                "online_booking": 1,
                "mobile_site_booking": 0,
                "from_lat": None,
                "from_long": None,
                "to_lat": None,
                "to_long": None,
                "from_date": start_dt.isoformat(),
                "to_date": end_dt.isoformat(),
                "booking_created": booking_created_dt.isoformat(),
            }

            result = self.predict(sample_booking)
            # Convert cancellation risk into a rough demand volume index.
            demand_strength = max(0.0, 1.0 - float(result["score"]))
            predicted_bookings = int(round(5 + (15 * demand_strength)))

            daily_predictions.append(
                {
                    "date": day.isoformat(),
                    "predicted_bookings": predicted_bookings,
                }
            )
            total_predicted_bookings += predicted_bookings
            day += timedelta(days=1)

        return {
            "predictions": daily_predictions,
            "total_predicted_bookings": total_predicted_bookings,
            "number_of_days": len(daily_predictions),
            "message": "Demand forecast generated successfully",
        }


model_instance = LightGBMModel()