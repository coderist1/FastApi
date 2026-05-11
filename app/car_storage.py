from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[1] / "car_rental.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _pick(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return default


def _json_load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _json_dump(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=True)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                middle_name TEXT DEFAULT '',
                sex TEXT DEFAULT '',
                date_of_birth TEXT DEFAULT '',
                role TEXT DEFAULT 'renter',
                active INTEGER DEFAULT 1,
                photo_uri TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT '',
                brand TEXT DEFAULT '',
                model TEXT DEFAULT '',
                year INTEGER DEFAULT NULL,
                price_per_day REAL DEFAULT 0,
                available INTEGER DEFAULT 1,
                photo_uri TEXT DEFAULT '',
                type TEXT DEFAULT '',
                transmission TEXT DEFAULT '',
                fuel TEXT DEFAULT '',
                seats INTEGER DEFAULT NULL,
                location TEXT DEFAULT '',
                description TEXT DEFAULT '',
                owner_id TEXT DEFAULT '',
                owner_email TEXT DEFAULT '',
                owner_name TEXT DEFAULT '',
                approval_status TEXT DEFAULT 'approved',
                status TEXT DEFAULT 'available',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle INTEGER NOT NULL,
                vehicle_name TEXT DEFAULT '',
                renter TEXT DEFAULT '',
                renter_id TEXT DEFAULT '',
                renter_email TEXT DEFAULT '',
                renter_name TEXT DEFAULT '',
                owner_id TEXT DEFAULT '',
                owner_email TEXT DEFAULT '',
                owner_name TEXT DEFAULT '',
                start_date TEXT DEFAULT '',
                end_date TEXT DEFAULT '',
                amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                notes TEXT DEFAULT '',
                cancel_reason TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS logreports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT DEFAULT '',
                vehicle_id INTEGER DEFAULT NULL,
                vehicle_name TEXT DEFAULT '',
                rental_id INTEGER DEFAULT NULL,
                renter_name TEXT DEFAULT '',
                start_date TEXT DEFAULT '',
                end_date TEXT DEFAULT '',
                amount REAL DEFAULT 0,
                issues TEXT DEFAULT '[]',
                notes TEXT DEFAULT '',
                odometer TEXT DEFAULT '',
                fuel_level TEXT DEFAULT '',
                photos TEXT DEFAULT '[]',
                custom_labels TEXT DEFAULT '{}',
                checkout TEXT DEFAULT '',
                comments TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _user_row(row: sqlite3.Row) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["username"],
        "password": row["password"],
        "firstName": row["first_name"],
        "lastName": row["last_name"],
        "middleName": row["middle_name"],
        "sex": row["sex"],
        "dateOfBirth": row["date_of_birth"],
        "role": row["role"],
        "active": bool(row["active"]),
        "photoUri": row["photo_uri"],
    }


def _vehicle_row(row: sqlite3.Row) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row["id"],
        "name": row["name"],
        "brand": row["brand"],
        "model": row["model"],
        "year": row["year"],
        "pricePerDay": row["price_per_day"],
        "available": bool(row["available"]),
        "status": row["status"],
        "photoUri": row["photo_uri"],
        "type": row["type"],
        "transmission": row["transmission"],
        "fuel": row["fuel"],
        "seats": row["seats"],
        "location": row["location"],
        "description": row["description"],
        "ownerId": row["owner_id"],
        "ownerEmail": row["owner_email"],
        "ownerName": row["owner_name"],
        "approvalStatus": row["approval_status"],
    }


def _booking_row(row: sqlite3.Row) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row["id"],
        "vehicle": row["vehicle"],
        "vehicleId": row["vehicle"],
        "vehicleName": row["vehicle_name"],
        "renter": row["renter"],
        "renterId": row["renter_id"],
        "renterEmail": row["renter_email"],
        "renterName": row["renter_name"],
        "ownerId": row["owner_id"],
        "ownerEmail": row["owner_email"],
        "ownerName": row["owner_name"],
        "startDate": row["start_date"],
        "endDate": row["end_date"],
        "amount": row["amount"],
        "status": row["status"],
        "notes": row["notes"],
        "cancelReason": row["cancel_reason"],
        "createdAt": row["created_at"],
    }


def _report_row(row: sqlite3.Row) -> dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": row["id"],
        "type": row["type"],
        "vehicleId": row["vehicle_id"],
        "vehicleName": row["vehicle_name"],
        "rentalId": row["rental_id"],
        "renterName": row["renter_name"],
        "startDate": row["start_date"],
        "endDate": row["end_date"],
        "amount": row["amount"],
        "issues": _json_load(row["issues"], []),
        "notes": row["notes"],
        "odometer": row["odometer"],
        "fuelLevel": row["fuel_level"],
        "photos": _json_load(row["photos"], []),
        "customLabels": _json_load(row["custom_labels"], {}),
        "checkout": row["checkout"],
        "comments": _json_load(row["comments"], []),
        "createdAt": row["created_at"],
    }


def upsert_user(payload: dict[str, Any]) -> dict[str, Any]:
    email = str(_pick(payload, "email", "username", default="")).strip().lower()
    username = str(_pick(payload, "username", "email", default="")).strip().lower()
    password = str(_pick(payload, "password", default=""))
    if not email or not username or not password:
        raise ValueError("email, username, and password are required")

    with _connect() as connection:
        existing = connection.execute(
            "SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ?",
            (email, username),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE users
                SET email = ?, username = ?, password = ?, first_name = ?, last_name = ?, middle_name = ?,
                    sex = ?, date_of_birth = ?, role = ?, active = ?, photo_uri = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    email,
                    username,
                    password,
                    str(_pick(payload, "firstName", "first_name", default="")),
                    str(_pick(payload, "lastName", "last_name", default="")),
                    str(_pick(payload, "middleName", "middle_name", default="")),
                    str(_pick(payload, "sex", default="")),
                    str(_pick(payload, "dateOfBirth", "date_of_birth", default="")),
                    str(_pick(payload, "role", default="renter")),
                    1 if bool(_pick(payload, "active", default=True)) else 0,
                    str(_pick(payload, "photoUri", "photo_url", default="")),
                    datetime.utcnow().isoformat(),
                    existing["id"],
                ),
            )
            row = connection.execute("SELECT * FROM users WHERE id = ?", (existing["id"],)).fetchone()
            return _user_row(row)

        cursor = connection.execute(
            """
            INSERT INTO users (email, username, password, first_name, last_name, middle_name, sex, date_of_birth, role, active, photo_uri)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                username,
                password,
                str(_pick(payload, "firstName", "first_name", default="")),
                str(_pick(payload, "lastName", "last_name", default="")),
                str(_pick(payload, "middleName", "middle_name", default="")),
                str(_pick(payload, "sex", default="")),
                str(_pick(payload, "dateOfBirth", "date_of_birth", default="")),
                str(_pick(payload, "role", default="renter")),
                1 if bool(_pick(payload, "active", default=True)) else 0,
                str(_pick(payload, "photoUri", "photo_url", default="")),
            ),
        )
        row = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _user_row(row)


def authenticate_user(credentials: dict[str, Any]) -> dict[str, Any] | None:
    identifier = str(_pick(credentials, "username", "email", default="")).strip().lower()
    password = str(_pick(credentials, "password", default=""))
    if not identifier or not password:
        return None
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE (lower(email) = ? OR lower(username) = ?) AND password = ?",
            (identifier, identifier, password),
        ).fetchone()
        return _user_row(row) if row else None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE lower(email) = ?", (email.strip().lower(),)).fetchone()
        return _user_row(row) if row else None


def update_user(email: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    current = get_user_by_email(email)
    if not current:
        return None
    with _connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET first_name = ?, last_name = ?, middle_name = ?, sex = ?, date_of_birth = ?,
                photo_uri = ?, updated_at = ?
            WHERE lower(email) = ?
            """,
            (
                str(_pick(payload, "firstName", "first_name", default=current["firstName"])),
                str(_pick(payload, "lastName", "last_name", default=current["lastName"])),
                str(_pick(payload, "middleName", "middle_name", default=current["middleName"])),
                str(_pick(payload, "sex", default=current["sex"])),
                str(_pick(payload, "dateOfBirth", "date_of_birth", default=current["dateOfBirth"])),
                str(_pick(payload, "photoUri", "photo_url", default=current["photoUri"])),
                datetime.utcnow().isoformat(),
                email.strip().lower(),
            ),
        )
    return get_user_by_email(email)


def list_vehicles(owner_email: str | None = None) -> list[dict[str, Any]]:
    with _connect() as connection:
        if owner_email:
            rows = connection.execute(
                "SELECT * FROM vehicles WHERE lower(owner_email) = ? ORDER BY id DESC",
                (owner_email.strip().lower(),),
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM vehicles ORDER BY id DESC").fetchall()
        return [_vehicle_row(row) for row in rows]


def get_vehicle(vehicle_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
        return _vehicle_row(row) if row else None


def create_vehicle(payload: dict[str, Any]) -> dict[str, Any]:
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO vehicles (
                name, brand, model, year, price_per_day, available, photo_uri,
                type, transmission, fuel, seats, location, description,
                owner_id, owner_email, owner_name, approval_status, status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(_pick(payload, "name", default=_pick(payload, "model", default=""))),
                str(_pick(payload, "brand", default="")),
                str(_pick(payload, "model", default=_pick(payload, "name", default=""))),
                int(_pick(payload, "year", default=datetime.utcnow().year) or datetime.utcnow().year),
                float(_pick(payload, "pricePerDay", "price", "daily_rate", default=0) or 0),
                1 if bool(_pick(payload, "available", default=(_pick(payload, "status", default="available") == "available"))) else 0,
                str(_pick(payload, "photoUri", "photo_url", "photo", "image", default="")),
                str(_pick(payload, "type", default="")),
                str(_pick(payload, "transmission", default="")),
                str(_pick(payload, "fuel", default="")),
                int(_pick(payload, "seats", default=0) or 0),
                str(_pick(payload, "location", default="")),
                str(_pick(payload, "description", default="")),
                str(_pick(payload, "ownerId", "owner_id", "owner", "user_id", default="")),
                str(_pick(payload, "ownerEmail", "owner_email", default="")),
                str(_pick(payload, "ownerName", "owner_name", default="")),
                str(_pick(payload, "approvalStatus", "approval_status", default="approved")),
                str(_pick(payload, "status", default="available")),
                datetime.utcnow().isoformat(),
            ),
        )
        row = connection.execute("SELECT * FROM vehicles WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _vehicle_row(row)


def update_vehicle(vehicle_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    current = get_vehicle(vehicle_id)
    if not current:
        return None
    with _connect() as connection:
        connection.execute(
            """
            UPDATE vehicles
            SET name = ?, brand = ?, model = ?, year = ?, price_per_day = ?, available = ?, photo_uri = ?,
                type = ?, transmission = ?, fuel = ?, seats = ?, location = ?, description = ?,
                owner_id = ?, owner_email = ?, owner_name = ?, approval_status = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(_pick(payload, "name", default=current["name"])),
                str(_pick(payload, "brand", default=current["brand"])),
                str(_pick(payload, "model", default=current["model"])),
                int(_pick(payload, "year", default=current["year"] or 0) or 0),
                float(_pick(payload, "pricePerDay", "price", "daily_rate", default=current["pricePerDay"] or 0) or 0),
                1 if bool(_pick(payload, "available", default=current["available"])) else 0,
                str(_pick(payload, "photoUri", "photo_url", "photo", "image", default=current["photoUri"])),
                str(_pick(payload, "type", default=current["type"])),
                str(_pick(payload, "transmission", default=current["transmission"])),
                str(_pick(payload, "fuel", default=current["fuel"])),
                int(_pick(payload, "seats", default=current["seats"] or 0) or 0),
                str(_pick(payload, "location", default=current["location"])),
                str(_pick(payload, "description", default=current["description"])),
                str(_pick(payload, "ownerId", "owner_id", "owner", "user_id", default=current["ownerId"])),
                str(_pick(payload, "ownerEmail", "owner_email", default=current["ownerEmail"])),
                str(_pick(payload, "ownerName", "owner_name", default=current["ownerName"])),
                str(_pick(payload, "approvalStatus", "approval_status", default=current["approvalStatus"])),
                str(_pick(payload, "status", default=current["status"])),
                datetime.utcnow().isoformat(),
                vehicle_id,
            ),
        )
    return get_vehicle(vehicle_id)


def delete_vehicle(vehicle_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        return cursor.rowcount > 0


def list_bookings(renter_email: str | None = None, owner_email: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM bookings"
    params: list[Any] = []
    filters: list[str] = []
    if renter_email:
        filters.append("lower(renter_email) = ?")
        params.append(renter_email.strip().lower())
    if owner_email:
        filters.append("lower(owner_email) = ?")
        params.append(owner_email.strip().lower())
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY id DESC"
    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()
        return [_booking_row(row) for row in rows]


def get_booking(booking_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return _booking_row(row) if row else None


def create_booking(payload: dict[str, Any]) -> dict[str, Any]:
    vehicle_id = int(_pick(payload, "vehicle", "vehicleId", "vehicle_id", "car", "carId", default=0) or 0)
    vehicle = get_vehicle(vehicle_id)
    if not vehicle:
      raise ValueError("vehicle not found")

    renter_email = str(_pick(payload, "renterEmail", "renter_email", default="")).strip().lower()
    renter_name = str(_pick(payload, "renterName", "renter_name", default=""))
    renter_id = str(_pick(payload, "renterId", "renter_id", "renter", default=""))
    start_date = str(_pick(payload, "startDate", "start_date", "fromDate", "from", default=""))
    end_date = str(_pick(payload, "endDate", "end_date", "toDate", "to", default=""))
    amount = float(_pick(payload, "amount", "totalPrice", "total_price", default=vehicle["pricePerDay"] or 0) or 0)
    status = str(_pick(payload, "status", default="pending"))

    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO bookings (
                vehicle, vehicle_name, renter, renter_id, renter_email, renter_name,
                owner_id, owner_email, owner_name, start_date, end_date, amount, status, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vehicle_id,
                str(vehicle["name"]),
                renter_id or renter_email,
                renter_id,
                renter_email,
                renter_name,
                str(vehicle["ownerId"] or ""),
                str(vehicle["ownerEmail"] or ""),
                str(vehicle["ownerName"] or ""),
                start_date,
                end_date,
                amount,
                status,
                str(_pick(payload, "notes", default="")),
                datetime.utcnow().isoformat(),
            ),
        )
        row = connection.execute("SELECT * FROM bookings WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _booking_row(row)


def update_booking(booking_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    current = get_booking(booking_id)
    if not current:
        return None
    with _connect() as connection:
        connection.execute(
            """
            UPDATE bookings
            SET status = ?, notes = ?, cancel_reason = ?, start_date = ?, end_date = ?, amount = ?,
                renter_email = ?, renter_name = ?, renter_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(_pick(payload, "status", default=current["status"])),
                str(_pick(payload, "notes", default=current["notes"])),
                str(_pick(payload, "cancelReason", "cancel_reason", default=current["cancelReason"])),
                str(_pick(payload, "startDate", "start_date", default=current["startDate"])),
                str(_pick(payload, "endDate", "end_date", default=current["endDate"])),
                float(_pick(payload, "amount", "totalPrice", "total_price", default=current["amount"] or 0) or 0),
                str(_pick(payload, "renterEmail", "renter_email", default=current["renterEmail"])),
                str(_pick(payload, "renterName", "renter_name", default=current["renterName"])),
                str(_pick(payload, "renterId", "renter_id", "renter", default=current["renterId"])),
                datetime.utcnow().isoformat(),
                booking_id,
            ),
        )
    return get_booking(booking_id)


def delete_booking(booking_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        return cursor.rowcount > 0


def list_logreports() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM logreports ORDER BY id DESC").fetchall()
        return [_report_row(row) for row in rows]
