from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[1] / "boardease.db"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _json_load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _json_dump(value: Any) -> str:
    return json.dumps(value or [], ensure_ascii=True)


def _pick(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return default


def _seed_listings() -> list[dict[str, Any]]:
    return [
        {
            "name": "Sunrise Boarding House",
            "price": 3500,
            "location": "Divisoria, Cagayan de Oro",
            "rating": 4.5,
            "reviews": 0,
            "images": [
                "https://q-xx.bstatic.com/xdata/images/hotel/max500/410394094.jpg?k=cce2a4d520a8a46c2188d53163afe508d71c3e43f3dc8a64448ba09cda13b116&o=",
                "https://q-xx.bstatic.com/xdata/images/hotel/max500/160733814.jpg?k=5ee8bfbefc802123d9c3970cea3c2f51953b7854e10c665456407437c5fbe1d2&o=",
            ],
            "floorPlans": [],
            "virtualTour": "",
            "type": "Single Room",
            "amenities": ["WiFi", "Laundry", "Kitchen", "CR", "Utilities Included"],
            "distance": "0.8 km",
            "description": "Cozy single rooms with basic amenities. Perfect for students and working professionals.",
            "rules": ["No smoking indoors", "Keep noise low after 10 PM"],
            "available": True,
            "availableFrom": "Immediately",
            "locationData": None,
            "landlord": {
                "id": "saul.goodman@boardease.local",
                "name": "Saul Goodman",
                "phone": "09123456789",
                "verified": True,
                "email": "saul.goodman@boardease.local",
                "image": "",
            },
        },
        {
            "name": "CDO Student Dorm",
            "price": 2800,
            "location": "Nazareth, Cagayan de Oro",
            "rating": 4.4,
            "reviews": 0,
            "images": [
                "https://i.ytimg.com/vi/yEwHy_U9ZKE/hq720.jpg?sqp=-oaymwE7CK4FEIIDSFryq4qpAIARUAAAAAGAElAADIQj0AgKJD8AEB-AH-CYAC0AWKAgwIABABGFUgXyhlMA8=&rs=AOn4CLCh2RvNAlKiqAwmrofXeupwFcvEFg",
                "https://cf.bstatic.com/xdata/images/hotel/max1024x768/560858655.jpg?k=37451059691736cd90e025ea14705eebafb92b2793f25b43da91aa40dff8ec3e&o=",
            ],
            "floorPlans": [],
            "virtualTour": "",
            "type": "Shared Room",
            "amenities": ["WiFi", "Study Area", "CR", "24/7 Security"],
            "distance": "1.2 km",
            "description": "Affordable shared accommodation for students near universities.",
            "rules": ["Visitors allowed until 9 PM"],
            "available": True,
            "availableFrom": "Immediately",
            "locationData": None,
            "landlord": {
                "id": "mike.ehrmantraut@boardease.local",
                "name": "Mike Ehrmantraut",
                "phone": "09198765432",
                "verified": True,
                "email": "mike.ehrmantraut@boardease.local",
                "image": "",
            },
        },
        {
            "name": "Green Valley Apartelle",
            "price": 4500,
            "location": "Carmen, Cagayan de Oro",
            "rating": 4.7,
            "reviews": 0,
            "images": [
                "https://josoromabuilders.wordpress.com/wp-content/uploads/2019/04/pers-01.jpg",
                "https://jcs-boarding-house.getmanilahotels.com/data/Pictures/OriginalPhoto/6009/600927/600927660/manila-jcs-boarding-house-picture-5.JPEG",
            ],
            "floorPlans": [],
            "virtualTour": "",
            "type": "Shared Room",
            "amenities": ["WiFi", "Aircon", "Kitchen", "CR", "Parking", "Pets Allowed"],
            "distance": "2.1 km",
            "description": "Modern studio units with complete amenities for comfortable living.",
            "rules": ["No loud parties"],
            "available": True,
            "availableFrom": "Immediately",
            "locationData": None,
            "landlord": {
                "id": "gustavo.fring@boardease.local",
                "name": "Gustavo Fring",
                "phone": "09151234567",
                "verified": True,
                "email": "gustavo.fring@boardease.local",
                "image": "",
            },
        },
    ]


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
                phone TEXT DEFAULT '',
                role TEXT DEFAULT 'tenant',
                photo_url TEXT DEFAULT '',
                verified INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_email TEXT DEFAULT '',
                owner_name TEXT DEFAULT '',
                owner_phone TEXT DEFAULT '',
                owner_image TEXT DEFAULT '',
                owner_verified INTEGER DEFAULT 1,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                price REAL DEFAULT 0,
                description TEXT DEFAULT '',
                type TEXT DEFAULT 'Boarding House',
                distance TEXT DEFAULT '',
                available INTEGER DEFAULT 1,
                available_from TEXT DEFAULT '',
                virtual_tour TEXT DEFAULT '',
                rating REAL DEFAULT 0,
                reviews_count INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                inquiries INTEGER DEFAULT 0,
                bookings_count INTEGER DEFAULT 0,
                images TEXT DEFAULT '[]',
                floor_plans TEXT DEFAULT '[]',
                amenities TEXT DEFAULT '[]',
                rules TEXT DEFAULT '[]',
                location_data TEXT DEFAULT '',
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
                listing_id INTEGER NOT NULL,
                tenant_id TEXT DEFAULT '',
                tenant_name TEXT DEFAULT '',
                tenant_email TEXT DEFAULT '',
                landlord_id TEXT DEFAULT '',
                landlord_name TEXT DEFAULT '',
                landlord_email TEXT DEFAULT '',
                landlord_phone TEXT DEFAULT '',
                landlord_image TEXT DEFAULT '',
                property TEXT DEFAULT '',
                move_in_date TEXT DEFAULT '',
                guests INTEGER DEFAULT 1,
                amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                booked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                cancelled_at TEXT DEFAULT '',
                cancel_reason TEXT DEFAULT '',
                cancelled_by TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        listing_count = connection.execute("SELECT COUNT(*) AS count FROM listings").fetchone()["count"]
        if listing_count == 0:
            for listing in _seed_listings():
                create_listing(listing, connection=connection)


def _listing_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    if row is None:
        return {}

    return {
        "id": row["id"],
        "name": row["name"],
        "price": row["price"],
        "location": row["location"],
        "rating": row["rating"],
        "reviews": row["reviews_count"],
        "images": _json_load(row["images"], []),
        "floorPlans": _json_load(row["floor_plans"], []),
        "virtualTour": row["virtual_tour"],
        "type": row["type"],
        "amenities": _json_load(row["amenities"], []),
        "distance": row["distance"],
        "description": row["description"],
        "rules": _json_load(row["rules"], []),
        "available": bool(row["available"]),
        "availableFrom": row["available_from"],
        "status": row["status"],
        "views": row["views"],
        "inquiries": row["inquiries"],
        "bookings": row["bookings_count"],
        "locationData": _json_load(row["location_data"], None),
        "landlord": {
            "id": row["owner_email"] or row["owner_name"] or str(row["id"]),
            "name": row["owner_name"] or "Landlord",
            "phone": row["owner_phone"] or "",
            "verified": bool(row["owner_verified"]),
            "email": row["owner_email"] or "",
            "image": row["owner_image"] or "",
        },
    }


def _booking_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    if row is None:
        return {}

    return {
        "id": row["id"],
        "listingId": row["listing_id"],
        "propertyId": row["listing_id"],
        "property": row["property"],
        "tenantId": row["tenant_id"],
        "tenantName": row["tenant_name"],
        "tenantEmail": row["tenant_email"],
        "landlordId": row["landlord_id"],
        "landlordName": row["landlord_name"],
        "landlordEmail": row["landlord_email"],
        "landlordPhone": row["landlord_phone"],
        "landlordImage": row["landlord_image"],
        "moveInDate": row["move_in_date"],
        "guests": row["guests"],
        "amount": row["amount"],
        "status": row["status"],
        "bookedAt": row["booked_at"],
        "cancelledAt": row["cancelled_at"],
        "cancelReason": row["cancel_reason"],
        "cancelledBy": row["cancelled_by"],
    }


def _user_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    if row is None:
        return {}

    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["username"],
        "firstName": row["first_name"],
        "lastName": row["last_name"],
        "phone": row["phone"],
        "role": row["role"],
        "photoURL": row["photo_url"],
        "verified": bool(row["verified"]),
        "active": bool(row["active"]),
    }


def upsert_user(payload: dict[str, Any], connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    own_connection = connection is None
    connection = connection or _connect()
    try:
        email = (_pick(payload, "email", "username") or "").strip().lower()
        username = (_pick(payload, "username", "email") or "").strip().lower()
        password = str(_pick(payload, "password", default=""))
        first_name = str(_pick(payload, "firstName", "first_name", default=""))
        last_name = str(_pick(payload, "lastName", "last_name", default=""))
        phone = str(_pick(payload, "phone", "phoneNumber", default=""))
        role = str(_pick(payload, "role", default="tenant"))
        photo_url = str(_pick(payload, "photoURL", "photoUrl", "photo_url", default=""))
        verified = 1 if bool(_pick(payload, "verified", default=False)) else 0
        active = 1 if bool(_pick(payload, "active", default=True)) else 0

        if not email or not username or not password:
            raise ValueError("email, username, and password are required")

        existing = connection.execute(
            "SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ?",
            (email, username),
        ).fetchone()

        if existing:
            connection.execute(
                """
                UPDATE users
                SET email = ?, username = ?, password = ?, first_name = ?, last_name = ?, phone = ?,
                    role = ?, photo_url = ?, verified = ?, active = ?, updated_at = ?
                WHERE id = ?
                """,
                (email, username, password, first_name, last_name, phone, role, photo_url, verified, active, datetime.utcnow().isoformat(), existing["id"]),
            )
            user_row = connection.execute("SELECT * FROM users WHERE id = ?", (existing["id"],)).fetchone()
            return _user_row_to_dict(user_row)

        cursor = connection.execute(
            """
            INSERT INTO users (email, username, password, first_name, last_name, phone, role, photo_url, verified, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (email, username, password, first_name, last_name, phone, role, photo_url, verified, active),
        )
        user_row = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _user_row_to_dict(user_row)
    finally:
        if own_connection:
            connection.commit()
            connection.close()


def authenticate_user(credentials: dict[str, Any]) -> dict[str, Any] | None:
    email = (_pick(credentials, "email", "username") or "").strip().lower()
    password = str(_pick(credentials, "password", default=""))
    if not email or not password:
        return None

    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE (lower(email) = ? OR lower(username) = ?) AND password = ?",
            (email, email, password),
        ).fetchone()
        return _user_row_to_dict(row) if row else None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE lower(email) = ?", (email.strip().lower(),)).fetchone()
        return _user_row_to_dict(row) if row else None


def list_listings(owner_email: str | None = None) -> list[dict[str, Any]]:
    with _connect() as connection:
        if owner_email:
            rows = connection.execute(
                "SELECT * FROM listings WHERE lower(owner_email) = ? ORDER BY id DESC",
                (owner_email.strip().lower(),),
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM listings ORDER BY id DESC").fetchall()
        return [_listing_row_to_dict(row) for row in rows]


def get_listing(listing_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        return _listing_row_to_dict(row) if row else None


def create_listing(payload: dict[str, Any], connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    own_connection = connection is None
    connection = connection or _connect()
    try:
        landlord = payload.get("landlord") or {}
        owner_email = str(_pick(landlord, "email", default=_pick(payload, "ownerEmail", "owner_email", default=""))).strip().lower()
        owner_name = str(_pick(landlord, "name", default=_pick(payload, "ownerName", "owner_name", default="Landlord")))
        owner_phone = str(_pick(landlord, "phone", default=_pick(payload, "ownerPhone", "owner_phone", default="")))
        owner_image = str(_pick(landlord, "image", default=_pick(payload, "ownerImage", "owner_image", default="")))
        owner_verified = 1 if bool(_pick(landlord, "verified", default=_pick(payload, "ownerVerified", "owner_verified", default=True))) else 0

        name = str(_pick(payload, "name", default="")).strip()
        if not name:
            raise ValueError("name is required")

        cursor = connection.execute(
            """
            INSERT INTO listings (
                owner_email, owner_name, owner_phone, owner_image, owner_verified,
                name, location, price, description, type, distance, available, available_from,
                virtual_tour, rating, reviews_count, views, inquiries, bookings_count,
                images, floor_plans, amenities, rules, location_data, status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_email,
                owner_name,
                owner_phone,
                owner_image,
                owner_verified,
                name,
                str(_pick(payload, "location", default="")),
                float(_pick(payload, "price", default=0) or 0),
                str(_pick(payload, "description", default="")),
                str(_pick(payload, "type", default="Boarding House")),
                str(_pick(payload, "distance", default="")),
                1 if bool(_pick(payload, "available", default=True)) else 0,
                str(_pick(payload, "availableFrom", "available_from", default="")),
                str(_pick(payload, "virtualTour", "virtual_tour", default="")),
                float(_pick(payload, "rating", default=0) or 0),
                int(_pick(payload, "reviews", "reviewsCount", "reviews_count", default=0) or 0),
                int(_pick(payload, "views", default=0) or 0),
                int(_pick(payload, "inquiries", default=0) or 0),
                int(_pick(payload, "bookings", "bookingsCount", "bookings_count", default=0) or 0),
                _json_dump(_pick(payload, "images", default=[])),
                _json_dump(_pick(payload, "floorPlans", "floor_plans", default=[])),
                _json_dump(_pick(payload, "amenities", default=[])),
                _json_dump(_pick(payload, "rules", default=[])),
                json.dumps(_pick(payload, "locationData", "location_data", default=None), ensure_ascii=True),
                "available" if bool(_pick(payload, "available", default=True)) else "occupied",
                datetime.utcnow().isoformat(),
            ),
        )
        listing = get_listing(cursor.lastrowid)
        return listing or {}
    finally:
        if own_connection:
            connection.commit()
            connection.close()


def update_listing(listing_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    existing = get_listing(listing_id)
    if not existing:
        return None

    merged_payload = {
        "name": _pick(payload, "name", default=existing["name"]),
        "location": _pick(payload, "location", default=existing["location"]),
        "price": _pick(payload, "price", default=existing["price"]),
        "description": _pick(payload, "description", default=existing["description"]),
        "type": _pick(payload, "type", default=existing["type"]),
        "distance": _pick(payload, "distance", default=existing["distance"]),
        "available": _pick(payload, "available", default=existing["available"]),
        "availableFrom": _pick(payload, "availableFrom", "available_from", default=existing["availableFrom"]),
        "virtualTour": _pick(payload, "virtualTour", "virtual_tour", default=existing["virtualTour"]),
        "rating": _pick(payload, "rating", default=existing["rating"]),
        "reviews": _pick(payload, "reviews", "reviewsCount", "reviews_count", default=existing["reviews"]),
        "views": _pick(payload, "views", default=existing["views"]),
        "inquiries": _pick(payload, "inquiries", default=existing["inquiries"]),
        "bookings": _pick(payload, "bookings", "bookingsCount", "bookings_count", default=existing["bookings"]),
        "images": _pick(payload, "images", default=existing["images"]),
        "floorPlans": _pick(payload, "floorPlans", "floor_plans", default=existing["floorPlans"]),
        "amenities": _pick(payload, "amenities", default=existing["amenities"]),
        "rules": _pick(payload, "rules", default=existing["rules"]),
        "locationData": _pick(payload, "locationData", "location_data", default=existing["locationData"]),
        "landlord": _pick(payload, "landlord", default=existing["landlord"]),
    }

    landlord = merged_payload["landlord"] or {}
    with _connect() as connection:
        connection.execute(
            """
            UPDATE listings
            SET owner_email = ?, owner_name = ?, owner_phone = ?, owner_image = ?, owner_verified = ?,
                name = ?, location = ?, price = ?, description = ?, type = ?, distance = ?, available = ?,
                available_from = ?, virtual_tour = ?, rating = ?, reviews_count = ?, views = ?, inquiries = ?,
                bookings_count = ?, images = ?, floor_plans = ?, amenities = ?, rules = ?, location_data = ?,
                status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(_pick(landlord, "email", default=existing["landlord"]["email"])).strip().lower(),
                str(_pick(landlord, "name", default=existing["landlord"]["name"])),
                str(_pick(landlord, "phone", default=existing["landlord"]["phone"])),
                str(_pick(landlord, "image", default=existing["landlord"]["image"])),
                1 if bool(_pick(landlord, "verified", default=existing["landlord"]["verified"])) else 0,
                str(merged_payload["name"]),
                str(merged_payload["location"]),
                float(merged_payload["price"] or 0),
                str(merged_payload["description"]),
                str(merged_payload["type"]),
                str(merged_payload["distance"]),
                1 if bool(merged_payload["available"]) else 0,
                str(merged_payload["availableFrom"]),
                str(merged_payload["virtualTour"]),
                float(merged_payload["rating"] or 0),
                int(merged_payload["reviews"] or 0),
                int(merged_payload["views"] or 0),
                int(merged_payload["inquiries"] or 0),
                int(merged_payload["bookings"] or 0),
                _json_dump(merged_payload["images"]),
                _json_dump(merged_payload["floorPlans"]),
                _json_dump(merged_payload["amenities"]),
                _json_dump(merged_payload["rules"]),
                json.dumps(merged_payload["locationData"], ensure_ascii=True),
                "available" if bool(merged_payload["available"]) else "occupied",
                datetime.utcnow().isoformat(),
                listing_id,
            ),
        )
    return get_listing(listing_id)


def delete_listing(listing_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
        return cursor.rowcount > 0


def list_bookings(tenant_email: str | None = None, landlord_email: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM bookings"
    params: list[Any] = []
    filters: list[str] = []

    if tenant_email:
        filters.append("lower(tenant_email) = ?")
        params.append(tenant_email.strip().lower())
    if landlord_email:
        filters.append("lower(landlord_email) = ?")
        params.append(landlord_email.strip().lower())

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY id DESC"
    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()
        return [_booking_row_to_dict(row) for row in rows]


def get_booking(booking_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return _booking_row_to_dict(row) if row else None


def create_booking(payload: dict[str, Any]) -> dict[str, Any]:
    listing_id = int(_pick(payload, "listingId", "listing_id", "propertyId", "property_id", default=0) or 0)
    listing = get_listing(listing_id)
    if not listing:
        raise ValueError("listing not found")

    landlord = listing["landlord"] or {}
    tenant_id = str(_pick(payload, "tenantId", "tenant_id", default=""))
    tenant_name = str(_pick(payload, "tenantName", "tenant_name", default=""))
    tenant_email = str(_pick(payload, "tenantEmail", "tenant_email", default=""))
    move_in_date = str(_pick(payload, "moveInDate", "move_in_date", default=""))
    guests = int(_pick(payload, "guests", default=1) or 1)
    amount = float(_pick(payload, "amount", default=listing["price"]) or listing["price"])
    status = str(_pick(payload, "status", default="pending"))

    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO bookings (
                listing_id, tenant_id, tenant_name, tenant_email, landlord_id, landlord_name,
                landlord_email, landlord_phone, landlord_image, property, move_in_date,
                guests, amount, status, booked_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                listing_id,
                tenant_id,
                tenant_name,
                tenant_email,
                landlord.get("id", ""),
                landlord.get("name", "Landlord"),
                landlord.get("email", ""),
                landlord.get("phone", ""),
                landlord.get("image", ""),
                listing["name"],
                move_in_date,
                guests,
                amount,
                status,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
            ),
        )
        connection.execute(
            "UPDATE listings SET bookings_count = bookings_count + 1, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), listing_id),
        )
        return get_booking(cursor.lastrowid) or {}


def update_booking(booking_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    booking = get_booking(booking_id)
    if not booking:
        return None

    status = str(_pick(payload, "status", default=booking["status"]))
    cancelled_at = str(_pick(payload, "cancelledAt", "cancelled_at", default=booking["cancelledAt"]))
    cancel_reason = str(_pick(payload, "cancelReason", "cancel_reason", default=booking["cancelReason"]))
    cancelled_by = str(_pick(payload, "cancelledBy", "cancelled_by", default=booking["cancelledBy"]))

    with _connect() as connection:
        connection.execute(
            """
            UPDATE bookings
            SET status = ?, cancelled_at = ?, cancel_reason = ?, cancelled_by = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, cancelled_at, cancel_reason, cancelled_by, datetime.utcnow().isoformat(), booking_id),
        )
    return get_booking(booking_id)


def delete_booking(booking_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        return cursor.rowcount > 0
