from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime
import shutil
from typing import List, Dict, Any
from app.schemas import (
    RentalBookingInput, 
    PredictionOutput, 
    DemandRequest, 
    DemandResponse
)
from app.model import LightGBMModel, model_instance
from app.demand_model import demand_model_instance
from .car_storage import (
    authenticate_user as car_authenticate_user,
    create_booking as car_create_booking,
    create_logreport as car_create_logreport,
    create_vehicle as car_create_vehicle,
    delete_booking as car_delete_booking,
    delete_vehicle as car_delete_vehicle,
    get_booking as car_get_booking,
    get_logreport as car_get_logreport,
    get_user_by_email as car_get_user_by_email,
    get_vehicle as car_get_vehicle,
    init_db as car_init_db,
    list_bookings as car_list_bookings,
    list_logreports as car_list_logreports,
    list_vehicles as car_list_vehicles,
    update_booking as car_update_booking,
    update_logreport as car_update_logreport,
    update_user as car_update_user,
    update_vehicle as car_update_vehicle,
    upsert_user as car_upsert_user,
)

app = FastAPI(title="Car Rental AI System")

# Ensure uploads directory exists and mount it to serve static files (images)
uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

@app.on_event("startup")
def startup_event():
    car_init_db()


async def parse_request_payload(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        payload = {}
        uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        for key, value in form.multi_items():
            if hasattr(value, "filename"):
                file_path = uploads_dir / value.filename
                with file_path.open("wb") as file_handle:
                    shutil.copyfileobj(value.file, file_handle)
                if key in {"photo", "image"}:
                    payload["photoUri"] = f"/uploads/{value.filename}"
                else:
                    payload[key] = f"/uploads/{value.filename}"
            else:
                payload[key] = value
        return payload

    if "application/json" in content_type or content_type == "":
        try:
            return await request.json()
        except Exception:
            return {}

    form = await request.form()
    return dict(form)

# Allow CORS requests from mobile and web clients during development.
# In production, restrict `allow_origins` to your frontend domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, Exception):
                self.disconnect(connection)

manager = ConnectionManager()

@app.get("/")
def home():
    return {"message": "Car Rental Demand Forecasting API is running"}

@app.get("/health")
def health():
    return {"status": "ok", "model": "lightgbm", "demand_model": "prophet-forecaster"}

# === Existing Single Booking Prediction ===
@app.post("/predict", response_model=PredictionOutput)
def predict(data: RentalBookingInput):
    try:
        return model_instance.predict(data.model_dump())
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

# === NEW: Demand Forecasting Endpoint ===
@app.post("/predict_demand", response_model=DemandResponse)
def predict_demand(request: DemandRequest):
    try:
        result = demand_model_instance.predict_demand(
            start_date=request.start_date,
            end_date=request.end_date,
            from_area_id=request.from_area_id,
            vehicle_model_id=request.vehicle_model_id,
            travel_type_id=request.travel_type_id,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/reload-model")
def reload_model():
    global model_instance
    model_instance = LightGBMModel()
    return {"message": "LightGBM model reloaded"}


@app.post("/reload-demand-model")
def reload_demand_model():
    demand_model_instance.reload()
    return {"message": "Demand forecasting model reloaded"}

# === Mobile App Endpoints ===


@app.get("/api/me")
def api_me(email: str = Query(..., min_length=1)):
    user = car_get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/login")
@app.post("/api/login/")
def api_login(credentials: dict):
    """Mobile compatibility login endpoint.
    Accepts {username, password} and returns {user: {...}}.
    """
    user = car_authenticate_user(credentials)
    if not user:
        raise HTTPException(status_code=400, detail="Username/email and password are required")
    return {"user": user}


@app.post("/api/me/")
@app.patch("/api/me")
@app.patch("/api/me/")
def api_update_me(payload: dict):
    email = (payload.get("email") or payload.get("username") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    user = car_update_user(email, payload)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/cars")
@app.get("/api/cars/")
def get_cars(owner_email: str | None = None):
    """Get all available cars for rental"""
    return car_list_vehicles(owner_email=owner_email)


@app.get("/api/cars/{vehicle_id}")
def get_car(vehicle_id: int):
    vehicle = car_get_vehicle(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@app.post("/api/cars")
@app.post("/api/cars/")
async def create_car(request: Request):
    try:
        payload = await parse_request_payload(request)
        vehicle = car_create_vehicle(payload)
        return vehicle
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/cars/{vehicle_id}")
@app.patch("/api/cars/{vehicle_id}")
@app.patch("/api/cars/{vehicle_id}/")
async def update_car(vehicle_id: int, request: Request):
    payload = await parse_request_payload(request)
    vehicle = car_update_vehicle(vehicle_id, payload)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@app.delete("/api/cars/{vehicle_id}")
@app.delete("/api/cars/{vehicle_id}/")
def remove_car(vehicle_id: int):
    if not car_delete_vehicle(vehicle_id):
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"message": "Vehicle deleted successfully"}

@app.get("/api/bookings")
@app.get("/api/bookings/")
def get_bookings(renter_email: str | None = None, owner_email: str | None = None):
    """Get all user bookings"""
    return car_list_bookings(renter_email=renter_email, owner_email=owner_email)


@app.get("/api/bookings/{booking_id}")
def get_booking(booking_id: int):
    booking = car_get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.post("/api/bookings")
@app.post("/api/bookings/")
def create_booking(booking_data: dict):
    """Create a new booking"""
    try:
        booking = car_create_booking(booking_data)
        return booking
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/bookings/{booking_id}")
@app.patch("/api/bookings/{booking_id}")
@app.patch("/api/bookings/{booking_id}/")
def edit_booking(booking_id: int, booking_data: dict):
    booking = car_update_booking(booking_id, booking_data)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.delete("/api/bookings/{booking_id}")
@app.delete("/api/bookings/{booking_id}/")
def remove_booking(booking_id: int):
    if not car_delete_booking(booking_id):
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted successfully"}


@app.get("/api/rentals")
@app.get("/api/rentals/")
def get_rentals_alias():
    return car_list_bookings()


@app.get("/api/reservations")
@app.get("/api/reservations/")
def get_reservations_alias():
    return car_list_bookings()


@app.post("/api/reservations")
@app.post("/api/reservations/")
def create_reservation(reservation_data: dict):
    return car_create_booking(reservation_data)


@app.patch("/api/reservations/{booking_id}")
@app.patch("/api/reservations/{booking_id}/")
def update_reservation(booking_id: int, reservation_data: dict):
    booking = car_update_booking(booking_id, reservation_data)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@app.delete("/api/reservations/{booking_id}")
@app.delete("/api/reservations/{booking_id}/")
def delete_reservation(booking_id: int):
    if not car_delete_booking(booking_id):
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Reservation deleted successfully"}


@app.get("/api/log-reports")
@app.get("/api/logreports")
@app.get("/api/logreports/")
def get_log_reports():
    """Get user's rental history and reports"""
    return car_list_logreports()


@app.get("/api/logs")
@app.get("/api/logs/")
def get_logs_alias():
    """Mobile compatibility alias expected by LogReportContext.
    Must return an array payload.
    """
    return car_list_logreports()


@app.post("/api/logreports")
@app.post("/api/logreports/")
def create_log_report(payload: dict):
    try:
        return car_create_logreport(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/api/log-reports/{report_id}")
def get_log_report(report_id: int):
    """Get a specific report by ID"""
    return {
        "report": {
            "id": report_id,
            "car": "Toyota Camry",
            "rental_date": "2024-04-01",
            "return_date": "2024-04-05",
            "total_cost": 250
        }
    }

# === Authentication Endpoints ===

@app.post("/api/register")
@app.post("/api/register/")
def register(user_data: dict):
    """Register a new user - flexible field acceptance"""
    try:
        user = car_upsert_user(user_data)
        return {"message": "User registered successfully", "user": user}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/register")
@app.post("/register/")
def register_no_prefix(user_data: dict):
    """Register endpoint without /api prefix (for api.js variants)"""
    return register(user_data)

# === Reports Endpoints ===

@app.get("/api/reports")
@app.get("/api/reports/")
def get_reports():
    """Get all user reports"""
    reports = car_list_logreports()
    return {"reports": reports} if isinstance(reports, list) else reports


@app.post("/api/reports")
@app.post("/api/reports/")
def create_report(payload: dict):
    """Create a new rental report (check-in) - ✅ FIXED: Added POST support"""
    try:
        report = car_create_logreport(payload)
        return report
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/reports")
def get_reports_no_prefix():
    """Get reports endpoint without /api prefix (for api.js variants)"""
    return get_reports()


@app.post("/reports")
@app.post("/reports/")
def create_report_no_prefix(payload: dict):
    """Create report endpoint without /api prefix"""
    return create_report(payload)

# === Reservations Endpoints ===

@app.get("/api/reservations")
def get_reservations():
    """Get all user reservations"""
    return {
        "reservations": [
            # Return user reservations
            # Example: {"id": 1, "car_id": 1, "status": "confirmed", "from_date": "2024-05-10", "to_date": "2024-05-15"}
        ]
    }

@app.get("/reservations")
def get_reservations_no_prefix():
    """Get reservations endpoint without /api prefix (for api.js variants)"""
    return get_reservations()

@app.post("/api/reservations")
def create_reservation(reservation_data: dict):
    """Create a new reservation"""
    try:
        # TODO: Save reservation to database
        return {
            "id": 1,
            "message": "Reservation created successfully",
            "reservation": reservation_data
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/reservations")
def create_reservation_no_prefix(reservation_data: dict):
    """Create reservation endpoint without /api prefix"""
    return create_reservation(reservation_data)

# === Log Report Endpoints ===

@app.patch("/api/logreports/{report_id}")
@app.patch("/api/logreports/{report_id}/")
def update_log_report(report_id: int, payload: dict):
    """Update a log report"""
    try:
        report = car_update_logreport(report_id, payload)
        if not report:
            raise HTTPException(status_code=404, detail="Log report not found")
        return report
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/logreports/{report_id}/checkout")
@app.post("/api/logreports/{report_id}/checkout/")
def checkout_log_report(report_id: int, payload: dict):
    """Save checkout data for a log report"""
    try:
        report = car_get_logreport(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Log report not found")
        # Merge checkout data into the report
        updated = {**report, "checkout": payload}
        result = car_update_logreport(report_id, updated)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/logreports/{report_id}/comments")
@app.post("/api/logreports/{report_id}/comments/")
def add_comment_to_report(report_id: int, payload: dict):
    """Add a comment to a log report"""
    try:
        report = car_get_logreport(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Log report not found")
        
        comment = {
            "author": payload.get("author", "Anonymous"),
            "message": payload.get("message", ""),
            "createdAt": payload.get("createdAt") or datetime.utcnow().isoformat()
        }
        
        comments = list(report.get("comments", []) or [])
        comments.append(comment)
        
        updated = {**report, "comments": comments}
        result = car_update_logreport(report_id, updated)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# === User Endpoints ===

@app.get("/api/users")
@app.get("/api/users/")
def get_users():
    """Get all users - returns empty list for compatibility"""
    return []

# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/sync/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)