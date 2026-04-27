from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import User, Vehicle, Booking, LogReport

# ---------------------------------------------------------------------------
# Lifespan: create tables + seed admin
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@example.com").first():
            admin = User(
                email="admin@example.com",
                username="admin@example.com",
                password="secret123",
                firstName="Admin",
                lastName="User",
                middleName="",
                sex="other",
                dateOfBirth=None,
                role="admin",
                active=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
    yield

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Car Rental API",
    description="A FastAPI backend for the Car Rental app backed by PostgreSQL.",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    firstName: Optional[str] = ""
    lastName: Optional[str] = ""
    middleName: Optional[str] = ""
    sex: Optional[str] = ""
    dateOfBirth: Optional[str] = None
    role: Optional[str] = "renter"   # renter | owner | admin

class UserUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    middleName: Optional[str] = None
    sex: Optional[str] = None
    dateOfBirth: Optional[str] = None
    active: Optional[bool] = None

class CarPayload(BaseModel):
    brand: Optional[str] = ""
    model: Optional[str] = ""
    year: Optional[int] = Field(default_factory=lambda: datetime.now().year)
    pricePerDay: Optional[float] = 0.0
    available: Optional[bool] = True
    image: Optional[str] = ""
    type: Optional[str] = ""
    transmission: Optional[str] = ""
    fuel: Optional[str] = ""
    seats: Optional[int] = None
    location: Optional[str] = ""
    description: Optional[str] = ""
    ownerId: Optional[int] = None
    ownerEmail: Optional[str] = None

class BookingPayload(BaseModel):
    vehicle: int
    renter: int
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    amount: Optional[float] = 0.0
    status: Optional[str] = "pending"

class BookingUpdate(BaseModel):
    vehicle: Optional[int] = None
    renter: Optional[int] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None

class LogReportPayload(BaseModel):
    type: str
    vehicleId: int
    vehicleName: Optional[str] = ""
    rentalId: int
    renterName: Optional[str] = ""
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    amount: Optional[float] = 0.0
    issues: Optional[List[str]] = []
    notes: Optional[str] = ""
    odometer: Optional[str] = ""
    fuelLevel: Optional[str] = ""
    photos: Optional[List[str]] = []
    customLabels: Optional[Dict[str, Any]] = {}
    checkout: Optional[Dict[str, Any]] = None
    comments: Optional[List[Dict[str, Any]]] = []

class LogReportUpdate(BaseModel):
    type: Optional[str] = None
    vehicleId: Optional[int] = None
    vehicleName: Optional[str] = None
    rentalId: Optional[int] = None
    renterName: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    amount: Optional[float] = None
    issues: Optional[List[str]] = None
    notes: Optional[str] = None
    odometer: Optional[str] = None
    fuelLevel: Optional[str] = None
    photos: Optional[List[str]] = None
    customLabels: Optional[Dict[str, Any]] = None
    checkout: Optional[Dict[str, Any]] = None
    comments: Optional[List[Dict[str, Any]]] = None

class CommentPayload(BaseModel):
    author: Optional[str] = "Anonymous"
    message: str
    createdAt: Optional[str] = None

class ClearBookingsRequest(BaseModel):
    user_id: int

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

# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Sanitizers
# ---------------------------------------------------------------------------

def sanitize_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "firstName": user.firstName or "",
        "lastName": user.lastName or "",
        "middleName": user.middleName or "",
        "sex": user.sex or "",
        "dateOfBirth": user.dateOfBirth,
        "role": user.role or "renter",   # renter | owner | admin
        "active": user.active,
        "fullName": " ".join(filter(None, [user.firstName, user.lastName])).strip(),
    }

def sanitize_vehicle(v: Vehicle) -> Dict[str, Any]:
    return {
        "id": v.id,
        "name": v.name or v.model or "",
        "brand": v.brand or "",
        "model": v.model or "",
        "year": v.year,
        "pricePerDay": float(v.pricePerDay or 0.0),
        "price": float(v.pricePerDay or 0.0),
        "available": bool(v.available),
        "status": "available" if v.available else "rented",
        "image": v.image or "",
        "type": v.type or "",
        "transmission": v.transmission or "",
        "fuel": v.fuel or "",
        "seats": v.seats,
        "location": v.location or "",
        "description": v.description or "",
        "ownerId": v.ownerId,
        "ownerEmail": v.ownerEmail or "",
    }

def sanitize_booking(b: Booking) -> Dict[str, Any]:
    return {
        "id": b.id,
        "vehicle": b.vehicle,
        "vehicleId": b.vehicle,
        "renter": b.renter,
        "renterId": b.renter,
        "startDate": b.startDate,
        "endDate": b.endDate,
        "amount": float(b.amount or 0.0),
        "status": b.status or "pending",
    }

def sanitize_logreport(r: LogReport) -> Dict[str, Any]:
    return {
        "id": r.id,
        "type": r.type,
        "vehicleId": r.vehicleId,
        "vehicleName": r.vehicleName or "",
        "rentalId": r.rentalId,
        "renterName": r.renterName or "",
        "startDate": r.startDate,
        "endDate": r.endDate,
        "amount": float(r.amount or 0.0),
        "issues": r.issues or [],
        "notes": r.notes or "",
        "odometer": r.odometer or "",
        "fuelLevel": r.fuelLevel or "",
        "photos": r.photos or [],
        "customLabels": r.customLabels or {},
        "checkout": r.checkout,
        "comments": r.comments or [],
        "createdAt": r.createdAt,
    }

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    session_user_id = request.cookies.get("session_user_id")
    if not session_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = db.query(User).filter(User.id == int(session_user_id), User.active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user

def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user

def get_owner_user(user: User = Depends(get_current_user)) -> User:
    """Allows both owners and admins to manage vehicles."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner privileges required")
    return user

# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/api/login/")
async def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        ((User.username == payload.username) | (User.email == payload.username)),
        User.active == True
    ).first()
    if not user or user.password != payload.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    response.set_cookie("session_user_id", str(user.id), httponly=True, samesite="lax")
    return {"user": sanitize_user(user)}


@app.post("/api/logout/")
async def logout(response: Response):
    response.delete_cookie("session_user_id")
    return {"success": True}


@app.post("/api/register/")
async def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    # Validate role
    if payload.role not in ("renter", "owner", "admin"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role. Must be renter, owner, or admin.")
    existing = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.username)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username already exists")
    user = User(
        email=payload.email,
        username=payload.username,
        password=payload.password,
        firstName=payload.firstName or "",
        lastName=payload.lastName or "",
        middleName=payload.middleName or "",
        sex=payload.sex or "",
        dateOfBirth=payload.dateOfBirth,
        role=payload.role or "renter",
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie("session_user_id", str(user.id), httponly=True, samesite="lax")
    result = sanitize_user(user)
    await manager.broadcast({"type": "user_created", "action": "created", "id": user.id, "payload": result})
    return {"user": result}

# ---------------------------------------------------------------------------
# User routes
# ---------------------------------------------------------------------------

@app.get("/api/me/")
async def get_me(current_user: User = Depends(get_current_user)):
    return sanitize_user(current_user)


@app.patch("/api/me/")
async def update_me(payload: UserUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if payload.firstName is not None:
        user.firstName = payload.firstName
    if payload.lastName is not None:
        user.lastName = payload.lastName
    if payload.middleName is not None:
        user.middleName = payload.middleName
    if payload.sex is not None:
        user.sex = payload.sex
    if payload.dateOfBirth is not None:
        user.dateOfBirth = payload.dateOfBirth
    db.commit()
    db.refresh(user)
    result = sanitize_user(user)
    await manager.broadcast({"type": "profile_updated", "action": "updated", "id": user.id, "payload": result})
    return result


@app.get("/api/users/")
async def list_users(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.active == True).all()
    return [sanitize_user(u) for u in users]


@app.patch("/api/users/{user_id}/")
async def patch_user(user_id: int, payload: UserUpdate, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.firstName is not None:
        user.firstName = payload.firstName
    if payload.lastName is not None:
        user.lastName = payload.lastName
    if payload.middleName is not None:
        user.middleName = payload.middleName
    if payload.sex is not None:
        user.sex = payload.sex
    if payload.dateOfBirth is not None:
        user.dateOfBirth = payload.dateOfBirth
    if payload.active is not None:
        user.active = payload.active
    db.commit()
    db.refresh(user)
    result = sanitize_user(user)
    await manager.broadcast({"type": "user_updated", "action": "updated", "id": user_id, "payload": result})
    return result


@app.delete("/api/users/{user_id}/")
async def delete_user(user_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    result = sanitize_user(user)
    db.delete(user)
    db.commit()
    await manager.broadcast({"type": "user_deleted", "action": "deleted", "id": user_id, "payload": result})
    return {"success": True}

# ---------------------------------------------------------------------------
# Vehicle (car) routes — owner or admin only for write operations
# ---------------------------------------------------------------------------

@app.get("/api/cars/")
async def list_cars(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()
    return [sanitize_vehicle(v) for v in vehicles]


@app.post("/api/cars/")
async def create_car(payload: CarPayload, current_user: User = Depends(get_owner_user), db: Session = Depends(get_db)):
    vehicle = Vehicle(
        name=payload.model or payload.brand or "",
        brand=payload.brand or "",
        model=payload.model or "",
        year=payload.year or datetime.now().year,
        pricePerDay=float(payload.pricePerDay or 0.0),
        available=payload.available if payload.available is not None else True,
        image=payload.image or "",
        type=payload.type or "",
        transmission=payload.transmission or "",
        fuel=payload.fuel or "",
        seats=payload.seats,
        location=payload.location or "",
        description=payload.description or "",
        ownerId=payload.ownerId or current_user.id,
        ownerEmail=payload.ownerEmail or current_user.email,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    result = sanitize_vehicle(vehicle)
    await manager.broadcast({"type": "vehicle_created", "action": "created", "id": vehicle.id, "payload": result})
    return result


@app.patch("/api/cars/{vehicle_id}/")
async def update_car(vehicle_id: int, payload: CarPayload, current_user: User = Depends(get_owner_user), db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    # Owners can only edit their own vehicles; admins can edit any
    if current_user.role == "owner" and vehicle.ownerId != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own vehicles")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    result = sanitize_vehicle(vehicle)
    await manager.broadcast({"type": "vehicle_updated", "action": "updated", "id": vehicle_id, "payload": result})
    return result


@app.delete("/api/cars/{vehicle_id}/")
async def delete_car(vehicle_id: int, current_user: User = Depends(get_owner_user), db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    # Owners can only delete their own vehicles; admins can delete any
    if current_user.role == "owner" and vehicle.ownerId != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own vehicles")
    result = sanitize_vehicle(vehicle)
    db.delete(vehicle)
    db.commit()
    await manager.broadcast({"type": "vehicle_deleted", "action": "deleted", "id": vehicle_id, "payload": result})
    return {"success": True}

# ---------------------------------------------------------------------------
# Booking routes — renters and admins
# ---------------------------------------------------------------------------

@app.get("/api/bookings/")
async def list_bookings(db: Session = Depends(get_db)):
    bookings = db.query(Booking).all()
    return [sanitize_booking(b) for b in bookings]


@app.post("/api/bookings/")
async def create_booking(payload: BookingPayload, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Only renters and admins can create bookings
    if current_user.role == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners cannot make bookings")
    booking = Booking(
        vehicle=payload.vehicle,
        renter=payload.renter,
        startDate=payload.startDate or datetime.now().isoformat(),
        endDate=payload.endDate,
        amount=float(payload.amount or 0.0),
        status=payload.status or "pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    result = sanitize_booking(booking)
    await manager.broadcast({"type": "booking_created", "action": "created", "id": booking.id, "payload": result})
    return result


@app.patch("/api/bookings/{booking_id}/")
async def update_booking(booking_id: int, payload: BookingUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if payload.vehicle is not None:
        booking.vehicle = payload.vehicle
    if payload.renter is not None:
        booking.renter = payload.renter
    if payload.startDate is not None:
        booking.startDate = payload.startDate
    if payload.endDate is not None:
        booking.endDate = payload.endDate
    if payload.amount is not None:
        booking.amount = float(payload.amount)
    if payload.status is not None:
        booking.status = payload.status
    db.commit()
    db.refresh(booking)
    result = sanitize_booking(booking)
    await manager.broadcast({"type": "booking_updated", "action": "updated", "id": booking_id, "payload": result})
    return result


@app.delete("/api/bookings/clear_user_bookings/")
async def clear_user_bookings(payload: ClearBookingsRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin" and current_user.id != payload.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to clear these bookings")
    bookings_to_delete = db.query(Booking).filter(Booking.renter == payload.user_id).all()
    for booking in bookings_to_delete:
        result = sanitize_booking(booking)
        db.delete(booking)
        await manager.broadcast({"type": "booking_deleted", "action": "deleted", "id": booking.id, "payload": result})
    db.commit()
    return {"success": True}


@app.delete("/api/bookings/{booking_id}/")
async def delete_booking(booking_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    result = sanitize_booking(booking)
    db.delete(booking)
    db.commit()
    await manager.broadcast({"type": "booking_deleted", "action": "deleted", "id": booking_id, "payload": result})
    return {"success": True}

# ---------------------------------------------------------------------------
# Log report routes
# ---------------------------------------------------------------------------

@app.get("/api/logreports/")
async def list_logreports(db: Session = Depends(get_db)):
    reports = db.query(LogReport).all()
    return [sanitize_logreport(r) for r in reports]


@app.post("/api/logreports/")
async def create_logreport(payload: LogReportPayload, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = LogReport(
        type=payload.type,
        vehicleId=payload.vehicleId,
        vehicleName=payload.vehicleName or "",
        rentalId=payload.rentalId,
        renterName=payload.renterName or "",
        startDate=payload.startDate or datetime.now().isoformat(),
        endDate=payload.endDate,
        amount=float(payload.amount or 0.0),
        issues=payload.issues or [],
        notes=payload.notes or "",
        odometer=payload.odometer or "",
        fuelLevel=payload.fuelLevel or "",
        photos=payload.photos or [],
        customLabels=payload.customLabels or {},
        checkout=payload.checkout,
        comments=payload.comments or [],
        createdAt=datetime.now().isoformat(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    result = sanitize_logreport(report)
    await manager.broadcast({"type": "logreport_created", "action": "created", "id": report.id, "payload": result})
    return result


@app.patch("/api/logreports/{report_id}/")
async def update_logreport(report_id: int, payload: LogReportUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(LogReport).filter(LogReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log report not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(report, field, value)
    db.commit()
    db.refresh(report)
    result = sanitize_logreport(report)
    await manager.broadcast({"type": "logreport_updated", "action": "updated", "id": report_id, "payload": result})
    return result


@app.post("/api/logreports/{report_id}/checkout/")
async def checkout_logreport(report_id: int, payload: Dict[str, Any], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(LogReport).filter(LogReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log report not found")
    report.checkout = payload
    db.commit()
    db.refresh(report)
    result = sanitize_logreport(report)
    await manager.broadcast({"type": "logreport_updated", "action": "checkout", "id": report_id, "payload": result})
    return result


@app.post("/api/logreports/{report_id}/comments/")
async def add_comment(report_id: int, payload: CommentPayload, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(LogReport).filter(LogReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log report not found")
    comment = payload.dict()
    comment["createdAt"] = comment.get("createdAt") or datetime.now().isoformat()
    comments = list(report.comments or [])
    comments.append(comment)
    report.comments = comments
    db.commit()
    db.refresh(report)
    result = sanitize_logreport(report)
    await manager.broadcast({"type": "logreport_updated", "action": "comment_added", "id": report_id, "payload": result})
    return result


@app.delete("/api/logreports/{report_id}/")
async def delete_logreport(report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(LogReport).filter(LogReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log report not found")
    result = sanitize_logreport(report)
    db.delete(report)
    db.commit()
    await manager.broadcast({"type": "logreport_deleted", "action": "deleted", "id": report_id, "payload": result})
    return {"success": True}

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
        