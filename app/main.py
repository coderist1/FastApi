from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    RentalBookingInput, 
    PredictionOutput, 
    DemandRequest, 
    DemandResponse
)
from app.model import LightGBMModel, model_instance
from app.demand_model import demand_model_instance

app = FastAPI(title="Car Rental AI System")

# Allow CORS requests from mobile and web clients during development.
# In production, restrict `allow_origins` to your frontend domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Car Rental Demand Forecasting API is running"}

@app.get("/health")
def health():
    return {"status": "ok", "model": "lightgbm", "demand_model": "lightgbm-regressor"}

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

@app.post("/api/login")
@app.post("/api/login/")
def api_login(credentials: dict):
    """Mobile compatibility login endpoint.
    Accepts {username, password} and returns {user: {...}}.
    """
    username = (credentials.get("username") or credentials.get("email") or "").strip().lower()
    password = credentials.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username/email and password are required")

    return {
        "user": {
            "id": 1,
            "email": username,
            "username": username,
            "firstName": credentials.get("firstName", "Mobile"),
            "lastName": credentials.get("lastName", "User"),
            "role": credentials.get("role", "renter"),
            "active": True,
        }
    }

@app.get("/api/cars")
def get_cars():
    """Get all available cars for rental"""
    return {
        "cars": [
            {"id": 1, "name": "Toyota Camry", "model_id": 1, "category": "Sedan", "price_per_day": 50},
            {"id": 2, "name": "Honda CRV", "model_id": 2, "category": "SUV", "price_per_day": 75},
            {"id": 3, "name": "Tesla Model 3", "model_id": 3, "category": "Electric", "price_per_day": 100},
        ]
    }

@app.get("/api/bookings")
def get_bookings():
    """Get all user bookings"""
    return {
        "bookings": [
            # Return user's rental bookings here
            # Example: {"id": 1, "car_id": 1, "start_date": "2024-05-10", "end_date": "2024-05-15", "status": "confirmed"}
        ]
    }


@app.get("/api/rentals")
@app.get("/api/rentals/")
def get_rentals_alias():
    """Mobile compatibility alias expected by BookingContext.
    Must return an array payload.
    """
    return []

@app.post("/api/bookings")
def create_booking(booking_data: dict):
    """Create a new booking"""
    try:
        # TODO: Save booking to database
        return {
            "id": 1,
            "message": "Booking created successfully",
            "booking": booking_data
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/api/log-reports")
def get_log_reports():
    """Get user's rental history and reports"""
    return {
        "reports": [
            # Return rental history/reports here
            # Example: {"id": 1, "car": "Toyota Camry", "rental_date": "2024-04-01", "return_date": "2024-04-05", "total_cost": 250}
        ]
    }


@app.get("/api/logs")
@app.get("/api/logs/")
def get_logs_alias():
    """Mobile compatibility alias expected by LogReportContext.
    Must return an array payload.
    """
    return []

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
def register(user_data: dict):
    """Register a new user - flexible field acceptance"""
    try:
        # Accept either email OR username
        email = user_data.get("email")
        username = user_data.get("username")
        password = user_data.get("password")
        full_name = user_data.get("full_name") or user_data.get("name")
        
        # Validate required fields
        if not password:
            raise HTTPException(status_code=400, detail="Password is required")
        
        if not (email or username):
            raise HTTPException(status_code=400, detail="Email or username is required")
        
        # TODO: Save user to database with: email, username, password, full_name
        return {
            "message": "User registered successfully",
            "user": {
                "id": 1,
                "email": email,
                "username": username,
                "full_name": full_name or "User"
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/register")
def register_no_prefix(user_data: dict):
    """Register endpoint without /api prefix (for api.js variants)"""
    return register(user_data)

# === Reports Endpoints ===

@app.get("/api/reports")
def get_reports():
    """Get all user reports"""
    return {
        "reports": [
            # Return user rental reports/history
            # Example: {"id": 1, "car": "Toyota Camry", "rental_date": "2024-04-01", "total_cost": 250}
        ]
    }

@app.get("/reports")
def get_reports_no_prefix():
    """Get reports endpoint without /api prefix (for api.js variants)"""
    return get_reports()

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