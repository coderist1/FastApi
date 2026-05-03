from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from pandas.tseries.holiday import USFederalHolidayCalendar
from sklearn.metrics import mean_absolute_error, mean_squared_error


DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parents[1] / "model" / "demand_lightgbm.pkl"
DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "historical_bookings.csv"

SEGMENT_COLUMNS = ["from_area_id", "vehicle_model_id", "travel_type_id"]
LAG_FEATURES = [1, 7, 14, 28]
ROLLING_WINDOWS = [7, 14, 28]
STATIC_FEATURES = [
    "segment_mean_demand",
    "area_mean_demand",
    "vehicle_model_mean_demand",
    "travel_type_mean_demand",
]


def _coerce_int_series(series: pd.Series, default: int = 0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default).astype(int)


def _to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def _calendar_features(frame: pd.DataFrame, date_column: str = "booking_date") -> pd.DataFrame:
    dates = pd.to_datetime(frame[date_column], errors="coerce")
    frame["dayofweek"] = dates.dt.dayofweek
    frame["month"] = dates.dt.month
    frame["dayofmonth"] = dates.dt.day
    frame["weekofyear"] = dates.dt.isocalendar().week.astype("Int64")
    frame["dayofyear"] = dates.dt.dayofyear
    frame["is_weekend"] = (frame["dayofweek"] >= 5).astype(int)
    frame["is_month_start"] = dates.dt.is_month_start.astype(int)
    frame["is_month_end"] = dates.dt.is_month_end.astype(int)
    frame["is_quarter_start"] = dates.dt.is_quarter_start.astype(int)
    frame["is_quarter_end"] = dates.dt.is_quarter_end.astype(int)
    frame["is_payday"] = dates.dt.day.isin([1, 15]).astype(int)
    frame["dayofyear_sin"] = np.sin(2 * np.pi * frame["dayofyear"] / 365.25)
    frame["dayofyear_cos"] = np.cos(2 * np.pi * frame["dayofyear"] / 365.25)
    frame["month_sin"] = np.sin(2 * np.pi * frame["month"] / 12.0)
    frame["month_cos"] = np.cos(2 * np.pi * frame["month"] / 12.0)
    return frame


def _holiday_flags(frame: pd.DataFrame, date_column: str = "booking_date") -> pd.DataFrame:
    dates = pd.to_datetime(frame[date_column], errors="coerce")
    start = dates.min()
    end = dates.max()
    calendar = USFederalHolidayCalendar()
    holiday_dates = calendar.holidays(start=start, end=end)
    holiday_set = set(holiday_dates.normalize())
    window_set = {
        holiday + timedelta(days=offset)
        for holiday in holiday_set
        for offset in (-1, 0, 1)
    }
    frame["is_holiday"] = dates.dt.normalize().isin(holiday_set).astype(int)
    frame["is_holiday_window"] = dates.dt.normalize().isin(window_set).astype(int)
    return frame


def _build_daily_grid(history: pd.DataFrame) -> pd.DataFrame:
    daily_counts = (
        history.groupby(["booking_date", *SEGMENT_COLUMNS], dropna=False)
        .size()
        .reset_index(name="demand")
    )
    all_dates = pd.DataFrame({"booking_date": pd.date_range(history["booking_date"].min(), history["booking_date"].max(), freq="D")})
    segments = daily_counts[SEGMENT_COLUMNS].drop_duplicates().reset_index(drop=True)
    all_dates["_key"] = 1
    segments["_key"] = 1
    grid = all_dates.merge(segments, on="_key").drop(columns="_key")
    grid = grid.merge(daily_counts, on=["booking_date", *SEGMENT_COLUMNS], how="left")
    grid["demand"] = grid["demand"].fillna(0).astype(int)
    return grid


def _add_static_features(frame: pd.DataFrame, maps: dict[str, dict]) -> pd.DataFrame:
    frame["segment_mean_demand"] = frame.apply(
        lambda row: maps["segment_mean"].get(
            (int(row["from_area_id"]), int(row["vehicle_model_id"]), int(row["travel_type_id"])),
            maps["global_mean"],
        ),
        axis=1,
    )
    frame["area_mean_demand"] = frame["from_area_id"].map(maps["area_mean"]).fillna(maps["global_mean"])
    frame["vehicle_model_mean_demand"] = frame["vehicle_model_id"].map(maps["vehicle_model_mean"]).fillna(maps["global_mean"])
    frame["travel_type_mean_demand"] = frame["travel_type_id"].map(maps["travel_type_mean"]).fillna(maps["global_mean"])
    return frame


def _add_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values([*SEGMENT_COLUMNS, "booking_date"]).copy()
    grouped = frame.groupby(SEGMENT_COLUMNS, sort=False)
    for lag in LAG_FEATURES:
        frame[f"lag_{lag}"] = grouped["demand"].shift(lag)
    shifted = grouped["demand"].shift(1)
    for window in ROLLING_WINDOWS:
        frame[f"rolling_mean_{window}"] = shifted.groupby(frame[SEGMENT_COLUMNS].apply(tuple, axis=1)).transform(
            lambda values: values.rolling(window=window, min_periods=1).mean()
        )
    frame["rolling_std_7"] = shifted.groupby(frame[SEGMENT_COLUMNS].apply(tuple, axis=1)).transform(
        lambda values: values.rolling(window=7, min_periods=2).std()
    )
    return frame


def _build_feature_frame(history: pd.DataFrame, maps: dict[str, dict]) -> pd.DataFrame:
    frame = _build_daily_grid(history)
    frame = _calendar_features(frame)
    frame = _holiday_flags(frame)
    frame = _add_static_features(frame, maps)
    frame = _add_lag_features(frame)
    return frame


def _build_training_maps(frame: pd.DataFrame, target_column: str = "demand") -> dict[str, dict]:
    global_mean = float(frame[target_column].mean()) if not frame.empty else 0.0
    return {
        "global_mean": global_mean,
        "area_mean": frame.groupby("from_area_id")[target_column].mean().to_dict(),
        "vehicle_model_mean": frame.groupby("vehicle_model_id")[target_column].mean().to_dict(),
        "travel_type_mean": frame.groupby("travel_type_id")[target_column].mean().to_dict(),
        "segment_mean": frame.groupby(SEGMENT_COLUMNS)[target_column].mean().to_dict(),
    }


@lru_cache(maxsize=1)
def _load_history_frame(history_path: str) -> pd.DataFrame:
    raw = pd.read_csv(history_path)
    required_columns = {"booking_created", *SEGMENT_COLUMNS}
    missing = required_columns.difference(raw.columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"Historical data is missing required columns: {missing_columns}")

    history = raw.copy()
    history["booking_date"] = _to_date(history["booking_created"])
    history = history.dropna(subset=["booking_date"])
    for column in SEGMENT_COLUMNS:
        history[column] = _coerce_int_series(history[column], default=0)
    return history


def train_demand_model(data_path: Path, artifact_path: Path) -> dict[str, float | str]:
    history = _load_history_frame(str(data_path))
    if history.empty:
        raise ValueError("Historical booking data is empty.")

    feature_frame = _build_feature_frame(history, {"global_mean": 0.0, "area_mean": {}, "vehicle_model_mean": {}, "travel_type_mean": {}, "segment_mean": {}})
    feature_frame = feature_frame.dropna(subset=["demand"]).copy()

    unique_dates = pd.Index(feature_frame["booking_date"].sort_values().unique())
    if len(unique_dates) < 10:
        raise ValueError("Not enough distinct booking dates to train the demand model.")

    split_index = max(1, int(len(unique_dates) * 0.8))
    split_date = unique_dates[split_index - 1]
    train_frame = feature_frame[feature_frame["booking_date"] <= split_date].copy()
    test_frame = feature_frame[feature_frame["booking_date"] > split_date].copy()

    maps = _build_training_maps(train_frame)
    train_frame = _add_static_features(train_frame, maps)
    test_frame = _add_static_features(test_frame, maps)

    feature_columns = [
        "from_area_id",
        "vehicle_model_id",
        "travel_type_id",
        "dayofweek",
        "month",
        "dayofmonth",
        "weekofyear",
        "dayofyear",
        "is_weekend",
        "is_month_start",
        "is_month_end",
        "is_quarter_start",
        "is_quarter_end",
        "is_payday",
        "is_holiday",
        "is_holiday_window",
        "dayofyear_sin",
        "dayofyear_cos",
        "month_sin",
        "month_cos",
        *STATIC_FEATURES,
        *[f"lag_{lag}" for lag in LAG_FEATURES],
        *[f"rolling_mean_{window}" for window in ROLLING_WINDOWS],
        "rolling_std_7",
    ]

    model = LGBMRegressor(
        objective="poisson",
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=63,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(train_frame[feature_columns], train_frame["demand"])
    test_predictions = np.clip(model.predict(test_frame[feature_columns]), 0, None)

    metrics = {
        "mae": float(mean_absolute_error(test_frame["demand"], test_predictions)),
        "rmse": float(np.sqrt(mean_squared_error(test_frame["demand"], test_predictions))),
        "rows": int(len(feature_frame)),
        "training_days": int(train_frame["booking_date"].nunique()),
        "testing_days": int(test_frame["booking_date"].nunique()),
    }

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "maps": maps,
            "segment_columns": SEGMENT_COLUMNS,
            "history_path": str(data_path),
            "model_name": "lightgbm_demand_regressor",
            "metrics": metrics,
        },
        artifact_path,
    )
    return metrics


class DemandForecaster:
    def __init__(self, artifact_path: Path | str = DEFAULT_ARTIFACT_PATH, history_path: Path | str = DEFAULT_HISTORY_PATH):
        self.artifact_path = Path(artifact_path)
        self.history_path = Path(history_path)
        self.reload()

    def reload(self):
        if not self.artifact_path.exists():
            raise FileNotFoundError(
                f"Demand model not found at {self.artifact_path}. Run `python -m app.train_demand --data <csv>` first."
            )

        payload = joblib.load(self.artifact_path)
        if not isinstance(payload, dict) or "model" not in payload or "feature_columns" not in payload:
            raise ValueError("Unexpected demand model artifact format. Retrain with `python -m app.train_demand`. ")

        self.model = payload["model"]
        self.feature_columns = payload["feature_columns"]
        self.maps = payload.get("maps", {})
        self.model_name = payload.get("model_name", "lightgbm_demand_regressor")
        self.segment_columns = payload.get("segment_columns", SEGMENT_COLUMNS)
        self.history_path = Path(payload.get("history_path", self.history_path))

    def _segment_history_lookup(self, from_area_id: int, vehicle_model_id: int, travel_type_id: int) -> dict[pd.Timestamp, int]:
        history = _load_history_frame(str(self.history_path))
        segment = history[
            (history["from_area_id"] == int(from_area_id))
            & (history["vehicle_model_id"] == int(vehicle_model_id))
            & (history["travel_type_id"] == int(travel_type_id))
        ]

        if segment.empty:
            return {}

        counts = segment.groupby("booking_date").size()
        full_range = pd.date_range(history["booking_date"].min(), history["booking_date"].max(), freq="D")
        counts = counts.reindex(full_range, fill_value=0)
        counts.index = counts.index.normalize()
        return {pd.Timestamp(index): int(value) for index, value in counts.items()}

    def _build_row(
        self,
        current_day: date,
        from_area_id: int,
        vehicle_model_id: int,
        travel_type_id: int,
        history_lookup: dict[pd.Timestamp, int],
    ) -> dict[str, float | int]:
        current_timestamp = pd.Timestamp(current_day).normalize()

        def lookup(offset: int) -> float:
            value = history_lookup.get(current_timestamp - timedelta(days=offset))
            return float(value) if value is not None else np.nan

        window_values: dict[int, float] = {}
        for window in ROLLING_WINDOWS:
            values = [lookup(offset) for offset in range(1, window + 1)]
            valid_values = [value for value in values if not pd.isna(value)]
            window_values[window] = float(np.mean(valid_values)) if valid_values else np.nan

        row = {
            "from_area_id": int(from_area_id),
            "vehicle_model_id": int(vehicle_model_id),
            "travel_type_id": int(travel_type_id),
            "booking_date": current_timestamp,
            "lag_1": lookup(1),
            "lag_7": lookup(7),
            "lag_14": lookup(14),
            "lag_28": lookup(28),
            "rolling_mean_7": window_values[7],
            "rolling_mean_14": window_values[14],
            "rolling_mean_28": window_values[28],
            "rolling_std_7": float(np.std([value for value in [lookup(offset) for offset in range(1, 8)] if not pd.isna(value)]))
            if any(not pd.isna(lookup(offset)) for offset in range(1, 8))
            else np.nan,
        }

        row = _calendar_features(pd.DataFrame([row]))
        row = _holiday_flags(row)
        row = _add_static_features(row, self.maps)
        return row.iloc[0].to_dict()

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

        travel_type = 0 if travel_type_id is None else int(travel_type_id)
        history_lookup = self._segment_history_lookup(from_area_id, vehicle_model_id, travel_type)
        predictions = []
        total_predicted_bookings = 0

        day = start_date
        while day <= end_date:
            row = self._build_row(day, from_area_id, vehicle_model_id, travel_type, history_lookup)
            feature_frame = pd.DataFrame([{column: row.get(column, np.nan) for column in self.feature_columns}])
            predicted_value = float(self.model.predict(feature_frame)[0])
            predicted_bookings = max(0, int(round(predicted_value)))

            history_lookup[pd.Timestamp(day).normalize()] = predicted_bookings
            predictions.append({"date": day.isoformat(), "predicted_bookings": predicted_bookings})
            total_predicted_bookings += predicted_bookings
            day += timedelta(days=1)

        return {
            "predictions": predictions,
            "total_predicted_bookings": total_predicted_bookings,
            "number_of_days": len(predictions),
            "message": "Demand forecast generated successfully",
        }


class LazyDemandForecaster:
    def __init__(self, artifact_path: Path | str = DEFAULT_ARTIFACT_PATH, history_path: Path | str = DEFAULT_HISTORY_PATH):
        self.artifact_path = Path(artifact_path)
        self.history_path = Path(history_path)
        self._model: DemandForecaster | None = None

    def _ensure_model(self) -> DemandForecaster:
        if self._model is None:
            self._model = DemandForecaster(self.artifact_path, self.history_path)
        return self._model

    def reload(self):
        self._model = DemandForecaster(self.artifact_path, self.history_path)
        return self._model

    def predict_demand(self, *args, **kwargs):
        return self._ensure_model().predict_demand(*args, **kwargs)


demand_model_instance = LazyDemandForecaster()