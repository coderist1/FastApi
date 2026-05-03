from __future__ import annotations

import numpy as np
import pandas as pd


BASE_NUMERIC_COLUMNS = [
	"vehicle_model_id",
	"package_id",
	"travel_type_id",
	"from_area_id",
	"to_area_id",
	"from_city_id",
	"to_city_id",
	"online_booking",
	"mobile_site_booking",
	"from_lat",
	"from_long",
	"to_lat",
	"to_long",
]

DATE_COLUMNS = ["from_date", "to_date", "booking_created"]

FEATURE_COLUMNS = [
	*BASE_NUMERIC_COLUMNS,
	"booking_lead_hours",
	"trip_duration_hours",
	"booking_created_hour",
	"booking_created_dayofweek",
	"from_date_hour",
	"from_date_dayofweek",
	"to_date_hour",
	"to_date_dayofweek",
	"route_distance_km",
]


def _ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
	for column in columns:
		if column not in frame.columns:
			frame[column] = pd.NA
	return frame


def _coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
	for column in columns:
		frame[column] = pd.to_numeric(frame[column], errors="coerce")
	return frame


def _coerce_datetime(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
	for column in columns:
		frame[column] = pd.to_datetime(frame[column], errors="coerce")
	return frame


def _haversine_km(frame: pd.DataFrame) -> pd.Series:
	from_lat = np.radians(pd.to_numeric(frame["from_lat"], errors="coerce"))
	from_long = np.radians(pd.to_numeric(frame["from_long"], errors="coerce"))
	to_lat = np.radians(pd.to_numeric(frame["to_lat"], errors="coerce"))
	to_long = np.radians(pd.to_numeric(frame["to_long"], errors="coerce"))

	dlat = to_lat - from_lat
	dlon = to_long - from_long
	a = np.sin(dlat / 2) ** 2 + np.cos(from_lat) * np.cos(to_lat) * np.sin(dlon / 2) ** 2
	return 6371.0 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)) * 2


def prepare_feature_frame(raw_frame: pd.DataFrame) -> pd.DataFrame:
	frame = raw_frame.copy()
	frame = _ensure_columns(frame, [*BASE_NUMERIC_COLUMNS, *DATE_COLUMNS])
	frame = _coerce_numeric(frame, BASE_NUMERIC_COLUMNS)
	frame = _coerce_datetime(frame, DATE_COLUMNS)

	frame["booking_lead_hours"] = (frame["from_date"] - frame["booking_created"]).dt.total_seconds() / 3600.0
	frame["trip_duration_hours"] = (frame["to_date"] - frame["from_date"]).dt.total_seconds() / 3600.0
	frame["booking_created_hour"] = frame["booking_created"].dt.hour
	frame["booking_created_dayofweek"] = frame["booking_created"].dt.dayofweek
	frame["from_date_hour"] = frame["from_date"].dt.hour
	frame["from_date_dayofweek"] = frame["from_date"].dt.dayofweek
	frame["to_date_hour"] = frame["to_date"].dt.hour
	frame["to_date_dayofweek"] = frame["to_date"].dt.dayofweek
	frame["route_distance_km"] = _haversine_km(frame)

	feature_frame = frame[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)
	return feature_frame