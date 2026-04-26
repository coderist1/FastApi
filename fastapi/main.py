from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

app = FastAPI(
    title="Car Rental API",
    description="A FastAPI backend matching the Car Rental frontend API contract.",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    firstName: Optional[str] = ''
    lastName: Optional[str] = ''
    middleName: Optional[str] = ''
    sex: Optional[str] = ''
    dateOfBirth: Optional[str] = None
    role: Optional[str] = 'renter'

class UserUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    middleName: Optional[str] = None
    sex: Optional[str] = None
    dateOfBirth: Optional[str] = None
    active: Optional[bool] = None

class CarPayload(BaseModel):
    brand: Optional[str] = ''
    model: Optional[str] = ''
    year: Optional[int] = Field(default_factory=lambda: datetime.now().year)
    pricePerDay: Optional[float] = 0.0
    available: Optional[bool] = True
    image: Optional[str] = ''
    type: Optional[str] = ''
    transmission: Optional[str] = ''
    fuel: Optional[str] = ''
    seats: Optional[int] = None
    location: Optional[str] = ''
    description: Optional[str] = ''
    ownerId: Optional[int] = None
    ownerEmail: Optional[str] = None

class BookingPayload(BaseModel):
    vehicle: int
    renter: int
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    amount: Optional[float] = 0.0
    status: Optional[str] = 'pending'

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
    vehicleName: Optional[str] = ''
    rentalId: int
    renterName: Optional[str] = ''
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    amount: Optional[float] = 0.0
    issues: Optional[List[str]] = []
    notes: Optional[str] = ''
    odometer: Optional[str] = ''
    fuelLevel: Optional[str] = ''
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
    author: Optional[str] = 'Anonymous'
    message: str
    createdAt: Optional[str] = None

class ClearBookingsRequest(BaseModel):
    user_id: int

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
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

DB: Dict[str, List[Dict[str, Any]]] = {
    'users': [],
    'vehicles': [],
    'bookings': [],
    'logreports': [],
}
COUNTERS = {
    'user': 1,
    'vehicle': 1,
    'booking': 1,
    'logreport': 1,
}

def next_id(name: str) -> int:
    COUNTERS[name] += 1
    return COUNTERS[name]


def sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': user['id'],
        'email': user['email'],
        'username': user['username'],
        'firstName': user.get('firstName', ''),
        'lastName': user.get('lastName', ''),
        'middleName': user.get('middleName', ''),
        'sex': user.get('sex', ''),
        'dateOfBirth': user.get('dateOfBirth'),
        'role': user.get('role', 'renter'),
        'active': user.get('active', True),
        'fullName': ' '.join(filter(None, [user.get('firstName', ''), user.get('lastName', '')])).strip(),
    }


def sanitize_vehicle(vehicle: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        **vehicle,
        'id': vehicle['id'],
        'pricePerDay': float(vehicle.get('pricePerDay', 0.0)),
        'price': float(vehicle.get('pricePerDay', 0.0)),
        'status': 'available' if vehicle.get('available', True) else 'rented',
        'available': bool(vehicle.get('available', True)),
    }
    if not result.get('name') and result.get('model'):
        result['name'] = result['model']
    return result


def sanitize_booking(booking: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **booking,
        'id': booking['id'],
        'vehicleId': booking.get('vehicle') or booking.get('vehicleId'),
        'renterId': booking.get('renter') or booking.get('renterId'),
        'startDate': booking.get('startDate') or booking.get('start_date'),
        'endDate': booking.get('endDate') or booking.get('end_date'),
        'amount': float(booking.get('amount', 0.0)),
    }


def sanitize_logreport(report: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        **report,
        'id': report['id'],
        'amount': float(report.get('amount', 0.0)),
        'issues': report.get('issues', []),
        'photos': report.get('photos', []),
        'customLabels': report.get('customLabels', {}),
        'comments': report.get('comments', []),
    }
    return result


def get_current_user(request: Request) -> Dict[str, Any]:
    session_user = request.cookies.get('session_user_id')
    if not session_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication required')
    user = next((u for u in DB['users'] if str(u['id']) == session_user and u.get('active', True)), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session')
    return user


def get_admin_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get('role') != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin privileges required')
    return user


@app.on_event('startup')
async def startup_data():
    admin_user = {
        'id': 1,
        'email': 'admin@example.com',
        'username': 'admin@example.com',
        'password': 'secret123',
        'firstName': 'Admin',
        'lastName': 'User',
        'middleName': '',
        'sex': 'other',
        'dateOfBirth': None,
        'role': 'admin',
        'active': True,
    }
    if not DB['users']:
        DB['users'].append(admin_user)


@app.post('/api/login/')
async def login(payload: LoginRequest, response: Response):
    user = next(
        (
            u
            for u in DB['users']
            if u.get('username') == payload.username or u.get('email') == payload.username
        ),
        None,
    )
    if not user or user.get('password') != payload.password or not user.get('active', True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username or password')
    response.set_cookie('session_user_id', str(user['id']), httponly=True, samesite='lax')
    return {'user': sanitize_user(user)}


@app.post('/api/register/')
async def register(payload: RegisterRequest, response: Response):
    if any(u for u in DB['users'] if u['email'] == payload.email or u['username'] == payload.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email or username already exists')
    user = {
        'id': next_id('user'),
        'email': payload.email,
        'username': payload.username,
        'password': payload.password,
        'firstName': payload.firstName or '',
        'lastName': payload.lastName or '',
        'middleName': payload.middleName or '',
        'sex': payload.sex or '',
        'dateOfBirth': payload.dateOfBirth,
        'role': payload.role or 'renter',
        'active': True,
    }
    DB['users'].append(user)
    response.set_cookie('session_user_id', str(user['id']), httponly=True, samesite='lax')
    await manager.broadcast({'type': 'user_created', 'action': 'created', 'id': user['id'], 'payload': sanitize_user(user)})
    return {'user': sanitize_user(user)}


@app.patch('/api/me/')
async def update_me(payload: UserUpdate, request: Request):
    user = get_current_user(request)
    if payload.firstName is not None:
        user['firstName'] = payload.firstName
    if payload.lastName is not None:
        user['lastName'] = payload.lastName
    if payload.middleName is not None:
        user['middleName'] = payload.middleName
    if payload.sex is not None:
        user['sex'] = payload.sex
    if payload.dateOfBirth is not None:
        user['dateOfBirth'] = payload.dateOfBirth
    await manager.broadcast({'type': 'profile_updated', 'action': 'updated', 'id': user['id'], 'payload': sanitize_user(user)})
    return sanitize_user(user)


@app.get('/api/users/')
async def list_users(admin: Dict[str, Any] = Depends(get_admin_user)):
    return [sanitize_user(u) for u in DB['users'] if u.get('active', True)]


@app.patch('/api/users/{user_id}/')
async def patch_user(user_id: int, payload: UserUpdate, admin: Dict[str, Any] = Depends(get_admin_user)):
    user = next((u for u in DB['users'] if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    if payload.firstName is not None:
        user['firstName'] = payload.firstName
    if payload.lastName is not None:
        user['lastName'] = payload.lastName
    if payload.middleName is not None:
        user['middleName'] = payload.middleName
    if payload.sex is not None:
        user['sex'] = payload.sex
    if payload.dateOfBirth is not None:
        user['dateOfBirth'] = payload.dateOfBirth
    if payload.active is not None:
        user['active'] = payload.active
    await manager.broadcast({'type': 'user_updated', 'action': 'updated', 'id': user_id, 'payload': sanitize_user(user)})
    return sanitize_user(user)


@app.delete('/api/users/{user_id}/')
async def delete_user(user_id: int, admin: Dict[str, Any] = Depends(get_admin_user)):
    index = next((i for i, u in enumerate(DB['users']) if u['id'] == user_id), None)
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    user = DB['users'].pop(index)
    await manager.broadcast({'type': 'user_deleted', 'action': 'deleted', 'id': user_id, 'payload': sanitize_user(user)})
    return {'success': True}


@app.get('/api/cars/')
async def list_cars():
    return [sanitize_vehicle(v) for v in DB['vehicles']]


@app.post('/api/cars/')
async def create_car(payload: CarPayload, current_user: Dict[str, Any] = Depends(get_current_user)):
    vehicle = {
        'id': next_id('vehicle'),
        'name': payload.model or payload.brand,
        'brand': payload.brand or '',
        'model': payload.model or payload.name if hasattr(payload, 'name') else payload.model or '',
        'year': payload.year or datetime.now().year,
        'pricePerDay': float(payload.pricePerDay or 0.0),
        'available': payload.available if payload.available is not None else True,
        'image': payload.image or '',
        'type': payload.type or '',
        'transmission': payload.transmission or '',
        'fuel': payload.fuel or '',
        'seats': payload.seats,
        'location': payload.location or '',
        'description': payload.description or '',
        'ownerId': payload.ownerId or current_user['id'],
        'ownerEmail': payload.ownerEmail or current_user['email'],
    }
    DB['vehicles'].append(vehicle)
    result = sanitize_vehicle(vehicle)
    await manager.broadcast({'type': 'vehicle_created', 'action': 'created', 'id': result['id'], 'payload': result})
    return result


@app.patch('/api/cars/{vehicle_id}/')
async def update_car(vehicle_id: int, payload: CarPayload, current_user: Dict[str, Any] = Depends(get_current_user)):
    vehicle = next((v for v in DB['vehicles'] if v['id'] == vehicle_id), None)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vehicle not found')
    for field in payload.dict(exclude_unset=True):
        vehicle[field] = payload.dict(exclude_unset=True)[field]
    result = sanitize_vehicle(vehicle)
    await manager.broadcast({'type': 'vehicle_updated', 'action': 'updated', 'id': vehicle_id, 'payload': result})
    return result


@app.delete('/api/cars/{vehicle_id}/')
async def delete_car(vehicle_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    index = next((i for i, v in enumerate(DB['vehicles']) if v['id'] == vehicle_id), None)
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vehicle not found')
    vehicle = DB['vehicles'].pop(index)
    await manager.broadcast({'type': 'vehicle_deleted', 'action': 'deleted', 'id': vehicle_id, 'payload': sanitize_vehicle(vehicle)})
    return {'success': True}


@app.get('/api/bookings/')
async def list_bookings():
    return [sanitize_booking(b) for b in DB['bookings']]


@app.post('/api/bookings/')
async def create_booking(payload: BookingPayload, current_user: Dict[str, Any] = Depends(get_current_user)):
    booking = {
        'id': next_id('booking'),
        'vehicle': payload.vehicle,
        'renter': payload.renter,
        'startDate': payload.startDate or datetime.now().isoformat(),
        'endDate': payload.endDate,
        'amount': float(payload.amount or 0.0),
        'status': payload.status or 'pending',
    }
    DB['bookings'].append(booking)
    result = sanitize_booking(booking)
    await manager.broadcast({'type': 'booking_created', 'action': 'created', 'id': result['id'], 'payload': result})
    return result


@app.patch('/api/bookings/{booking_id}/')
async def update_booking(booking_id: int, payload: BookingUpdate, current_user: Dict[str, Any] = Depends(get_current_user)):
    booking = next((b for b in DB['bookings'] if b['id'] == booking_id), None)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found')
    if payload.vehicle is not None:
        booking['vehicle'] = payload.vehicle
    if payload.renter is not None:
        booking['renter'] = payload.renter
    if payload.startDate is not None:
        booking['startDate'] = payload.startDate
    if payload.endDate is not None:
        booking['endDate'] = payload.endDate
    if payload.amount is not None:
        booking['amount'] = float(payload.amount)
    if payload.status is not None:
        booking['status'] = payload.status
    result = sanitize_booking(booking)
    await manager.broadcast({'type': 'booking_updated', 'action': 'updated', 'id': booking_id, 'payload': result})
    return result


@app.delete('/api/bookings/{booking_id}/')
async def delete_booking(booking_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    index = next((i for i, b in enumerate(DB['bookings']) if b['id'] == booking_id), None)
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Booking not found')
    booking = DB['bookings'].pop(index)
    await manager.broadcast({'type': 'booking_deleted', 'action': 'deleted', 'id': booking_id, 'payload': sanitize_booking(booking)})
    return {'success': True}


@app.delete('/api/bookings/clear_user_bookings/')
async def clear_user_bookings(payload: ClearBookingsRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user['role'] != 'admin' and current_user['id'] != payload.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to clear these bookings')
    remaining = [b for b in DB['bookings'] if b.get('renter') != payload.user_id]
    deleted = [b for b in DB['bookings'] if b.get('renter') == payload.user_id]
    DB['bookings'][:] = remaining
    for booking in deleted:
        await manager.broadcast({'type': 'booking_deleted', 'action': 'deleted', 'id': booking['id'], 'payload': sanitize_booking(booking)})
    return {'success': True}


@app.get('/api/logreports/')
async def list_logreports():
    return [sanitize_logreport(r) for r in DB['logreports']]


@app.post('/api/logreports/')
async def create_logreport(payload: LogReportPayload, current_user: Dict[str, Any] = Depends(get_current_user)):
    report = {
        'id': next_id('logreport'),
        'type': payload.type,
        'vehicleId': payload.vehicleId,
        'vehicleName': payload.vehicleName,
        'rentalId': payload.rentalId,
        'renterName': payload.renterName,
        'startDate': payload.startDate or datetime.now().isoformat(),
        'endDate': payload.endDate,
        'amount': float(payload.amount or 0.0),
        'issues': payload.issues or [],
        'notes': payload.notes or '',
        'odometer': payload.odometer or '',
        'fuelLevel': payload.fuelLevel or '',
        'photos': payload.photos or [],
        'customLabels': payload.customLabels or {},
        'checkout': payload.checkout,
        'comments': payload.comments or [],
        'createdAt': datetime.now().isoformat(),
    }
    DB['logreports'].append(report)
    result = sanitize_logreport(report)
    await manager.broadcast({'type': 'logreport_created', 'action': 'created', 'id': result['id'], 'payload': result})
    return result


@app.patch('/api/logreports/{report_id}/')
async def update_logreport(report_id: int, payload: LogReportUpdate, current_user: Dict[str, Any] = Depends(get_current_user)):
    report = next((r for r in DB['logreports'] if r['id'] == report_id), None)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Log report not found')
    update_data = payload.dict(exclude_unset=True)
    report.update(update_data)
    result = sanitize_logreport(report)
    await manager.broadcast({'type': 'logreport_updated', 'action': 'updated', 'id': report_id, 'payload': result})
    return result


@app.post('/api/logreports/{report_id}/checkout/')
async def checkout_logreport(report_id: int, payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(get_current_user)):
    report = next((r for r in DB['logreports'] if r['id'] == report_id), None)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Log report not found')
    report['checkout'] = payload
    result = sanitize_logreport(report)
    await manager.broadcast({'type': 'logreport_updated', 'action': 'checkout', 'id': report_id, 'payload': result})
    return result


@app.post('/api/logreports/{report_id}/comments/')
async def add_comment(report_id: int, payload: CommentPayload, current_user: Dict[str, Any] = Depends(get_current_user)):
    report = next((r for r in DB['logreports'] if r['id'] == report_id), None)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Log report not found')
    comment = payload.dict()
    comment['createdAt'] = comment.get('createdAt') or datetime.now().isoformat()
    report.setdefault('comments', []).append(comment)
    result = sanitize_logreport(report)
    await manager.broadcast({'type': 'logreport_updated', 'action': 'comment_added', 'id': report_id, 'payload': result})
    return result


@app.delete('/api/logreports/{report_id}/')
async def delete_logreport(report_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    index = next((i for i, r in enumerate(DB['logreports']) if r['id'] == report_id), None)
    if index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Log report not found')
    report = DB['logreports'].pop(index)
    await manager.broadcast({'type': 'logreport_deleted', 'action': 'deleted', 'id': report_id, 'payload': sanitize_logreport(report)})
    return {'success': True}


@app.websocket('/ws/sync/')
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
