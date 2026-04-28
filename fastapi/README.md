# FastAPI Backend for Car Rental Frontend

This backend implements a FastAPI API compatible with the attached `Car-Rental-` React frontend.

## Available endpoints

- `POST /api/login/`
- `POST /api/register/`
- `PATCH /api/me/`
- `GET /api/users/`
- `PATCH /api/users/{user_id}/`
- `DELETE /api/users/{user_id}/`
- `GET /api/cars/`
- `POST /api/cars/`
- `PATCH /api/cars/{vehicle_id}/`
- `DELETE /api/cars/{vehicle_id}/`
- `GET /api/bookings/`
- `POST /api/bookings/`
- `PATCH /api/bookings/{booking_id}/`
- `DELETE /api/bookings/{booking_id}/`
- `DELETE /api/bookings/clear_user_bookings/`
- `GET /api/logreports/`
- `POST /api/logreports/`
- `PATCH /api/logreports/{report_id}/`
- `POST /api/logreports/{report_id}/checkout/`
- `POST /api/logreports/{report_id}/comments/`
- `DELETE /api/logreports/{report_id}/`
- `WebSocket /ws/sync/`

## Run locally

1. Create a virtual environment

Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Mac / Linux

```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

Optionally save them:

```bash
pip freeze > requirements.txt
```

3. Model used

This project includes a small sentiment-analysis endpoint that uses the Hugging Face model:

distilbert-base-uncased-finetuned-sst-2-english

4. Run the app

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Notes

- Authentication is managed using a simple session cookie named `session_user_id`.
- A default admin user is created automatically:
  - `email`: `admin@example.com`
  - `password`: `secret123`
- This backing store is in-memory only.
