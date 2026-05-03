from datetime import date
from pydantic import BaseModel
from typing import List, Optional

# Keep your old schema for backward compatibility
class RentalBookingInput(BaseModel):
    vehicle_model_id: int | None = None
    package_id: int | None = None
    travel_type_id: int | None = None
    from_area_id: int | None = None
    to_area_id: int | None = None
    from_city_id: int | None = None
    to_city_id: int | None = None
    online_booking: int | None = None
    mobile_site_booking: int | None = None
    from_lat: float | None = None
    from_long: float | None = None
    to_lat: float | None = None
    to_long: float | None = None
    from_date: date | None = None
    to_date: date | None = None
    booking_created: date | None = None


class PredictionOutput(BaseModel):
    label: str
    score: float

# NEW: For Demand Forecasting
class DemandRequest(BaseModel):
    start_date: date
    end_date: date
    from_area_id: int = 0
    vehicle_model_id: int = 0
    travel_type_id: Optional[int] = None

class DailyPrediction(BaseModel):
    date: str
    predicted_bookings: int

class DemandResponse(BaseModel):
    predictions: List[DailyPrediction]
    total_predicted_bookings: int
    number_of_days: int
    message: str = "Demand forecast generated successfully"