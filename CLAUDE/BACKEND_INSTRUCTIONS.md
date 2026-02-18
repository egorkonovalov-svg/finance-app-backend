# FinTrack Backend Handoff

This document describes the full API contract that the React Native (Expo) frontend expects. Use it to build the FastAPI backend from scratch.

## Tech Stack (recommended)

- **Framework**: Python 3.14 / FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Auth**: JWT (PyJWT / python-jose), bcrypt for password hashing
- **Server**: Uvicorn

## Base URL

```
http://localhost:8000/api/v1
```

The frontend reads from `EXPO_PUBLIC_API_URL` env variable, defaulting to the above. All endpoints below are relative to this base.

## General Conventions

| Convention | Detail |
|---|---|
| Content-Type | `application/json` for all requests and responses |
| Auth header | `Authorization: Bearer <access_token>` on all protected endpoints |
| IDs | Strings (UUIDs recommended) |
| Dates | ISO 8601 strings, e.g. `"2026-02-17T10:30:00.000Z"` |
| Amounts | Numbers (floats). All amounts stored in **USD** |
| Deletion | Returns `204 No Content` (no response body) |
| Errors | Non-2xx status with JSON body: `{ "detail": "error message" }` |

---

## 1. Authentication

All auth endpoints are **public** (no Bearer token required) except `GET /auth/me` and `POST /auth/logout`.

### `POST /auth/signup`

Register a new user.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "securepass123",
  "name": "John Doe"           // optional
}
```

**Response `201`:**
```json
{
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "name": "John Doe",
    "avatar": null
  },
  "access_token": "jwt-token-string",
  "refresh_token": "optional-refresh-token"
}
```

### `POST /auth/login`

Authenticate with email and password.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

**Response `200`:** Same shape as signup response (`AuthResponse`).

### `POST /auth/social`

Authenticate via Google or Apple ID token. Create user on first login.

**Request body:**
```json
{
  "provider": "google",
  "id_token": "id-token-from-oauth-provider"
}
```

`provider` is `"google"` or `"apple"`. The backend should verify the `id_token` with the respective provider, extract the email/name, and create or find the user.

**Response `200`:** Same shape as signup response (`AuthResponse`).

### `GET /auth/me`

Returns the currently authenticated user. **Requires Bearer token.**

**Response `200`:**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar": null
}
```

Returns `401` if the token is invalid or expired.

### `POST /auth/logout`

Invalidate the current token. **Requires Bearer token.**

**Response `204`:** No body.

---

## 2. Transactions

All transaction endpoints **require authentication**. Transactions are scoped to the authenticated user.

### `GET /transactions`

List transactions with optional filtering and pagination.

**Query parameters (all optional):**

| Param | Type | Description |
|---|---|---|
| `type` | `"income"` or `"expense"` | Filter by transaction type |
| `category` | string | Filter by category name |
| `date_from` | ISO date string | Minimum date (inclusive) |
| `date_to` | ISO date string | Maximum date (inclusive) |
| `amount_min` | number | Minimum amount |
| `amount_max` | number | Maximum amount |
| `search` | string | Search in `note` and `category` fields (case-insensitive) |
| `page` | integer | Page number, defaults to `1` |
| `page_size` | integer | Items per page, defaults to `20` |

**Response `200`:**
```json
{
  "items": [
    {
      "id": "tx-uuid",
      "type": "expense",
      "amount": 42.50,
      "currency": "USD",
      "category": "Food & Drinks",
      "note": "Lunch at café",
      "date": "2026-02-17T12:30:00.000Z",
      "recurring": false
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

Default sort: by `date` descending (newest first).

### `GET /transactions/:id`

Get a single transaction by ID.

**Response `200`:** A single `Transaction` object (same shape as items above).

Returns `404` if not found or doesn't belong to the user.

### `POST /transactions`

Create a new transaction.

**Request body:**
```json
{
  "type": "expense",
  "amount": 42.50,
  "currency": "USD",
  "category": "Food & Drinks",
  "note": "Lunch at café",
  "date": "2026-02-17T12:30:00.000Z",
  "recurring": false
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | `"income"` or `"expense"` | Yes | |
| `amount` | number | Yes | Stored in USD |
| `currency` | string | Yes | Currency code at time of entry (e.g. `"USD"`, `"EUR"`) |
| `category` | string | Yes | Category name |
| `note` | string | No | User note |
| `date` | string | Yes | ISO 8601 |
| `recurring` | boolean | No | Defaults to `false` |

**Response `201`:** The created `Transaction` object with server-generated `id`.

### `PUT /transactions/:id`

Update an existing transaction. Partial updates allowed.

**Request body:** Any subset of the create fields.
```json
{
  "amount": 50.00,
  "note": "Updated note"
}
```

**Response `200`:** The full updated `Transaction` object.

### `DELETE /transactions/:id`

Delete a transaction.

**Response `204`:** No body.

### `GET /transactions/stats`

Aggregated statistics for the dashboard and analytics screens.

**Query parameters:**

| Param | Type | Description |
|---|---|---|
| `month` | string | Format `"YYYY-MM"`, e.g. `"2026-02"`. Defaults to current month. |

**Response `200`:**
```json
{
  "total_income": 5450.00,
  "total_expenses": 1843.48,
  "balance": 3606.52,
  "by_category": [
    {
      "category": "Food & Drinks",
      "amount": 423.50,
      "color": "#F59E0B"
    },
    {
      "category": "Transport",
      "amount": 60.00,
      "color": "#3B82F6"
    }
  ],
  "daily": [
    {
      "date": "2026-02-11",
      "income": 0,
      "expense": 28.00
    },
    {
      "date": "2026-02-12",
      "income": 0,
      "expense": 32.00
    }
  ]
}
```

Notes:
- `by_category` should include the category color from the categories table.
- `daily` should cover at least the last 7 days within the requested month.
- All amounts are in USD.

---

## 3. Categories

All category endpoints **require authentication**. Categories are scoped to the authenticated user.

### `GET /categories`

List all categories for the user. No pagination (flat array).

**Response `200`:**
```json
[
  {
    "id": "cat-uuid",
    "name": "Food & Drinks",
    "icon": "restaurant",
    "color": "#F59E0B",
    "type": "expense"
  }
]
```

### `POST /categories`

Create a new category.

**Request body:**
```json
{
  "name": "Food & Drinks",
  "icon": "restaurant",
  "color": "#F59E0B",
  "type": "expense"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | Yes | Display name |
| `icon` | string | Yes | Ionicons icon name (e.g. `"restaurant"`, `"car"`, `"cash"`) |
| `color` | string | Yes | Hex color (e.g. `"#F59E0B"`) |
| `type` | `"income"`, `"expense"`, or `"both"` | Yes | Which transaction types this category applies to |

**Response `201`:** The created `Category` with server-generated `id`.

### `PUT /categories/:id`

Update a category. Partial updates allowed.

**Response `200`:** The full updated `Category`.

### `DELETE /categories/:id`

Delete a category.

**Response `204`:** No body.

---

## 4. Data Models (Database Schema)

### `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `email` | VARCHAR(255) | Unique, not null |
| `password_hash` | VARCHAR(255) | Nullable (social-auth users may not have one) |
| `name` | VARCHAR(255) | Nullable |
| `avatar` | VARCHAR(512) | Nullable (URL) |
| `provider` | VARCHAR(50) | Nullable (`"google"`, `"apple"`, or null for email) |
| `created_at` | TIMESTAMP | Default now |

### `categories`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key -> users.id, not null |
| `name` | VARCHAR(100) | Not null |
| `icon` | VARCHAR(50) | Not null |
| `color` | VARCHAR(7) | Not null (hex) |
| `type` | VARCHAR(10) | Not null (`"income"`, `"expense"`, `"both"`) |

### `transactions`

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | Foreign key -> users.id, not null |
| `type` | VARCHAR(10) | Not null (`"income"`, `"expense"`) |
| `amount` | DECIMAL(12,2) | Not null (in USD) |
| `currency` | VARCHAR(3) | Not null |
| `category` | VARCHAR(100) | Not null (category name) |
| `note` | TEXT | Nullable |
| `date` | TIMESTAMP | Not null |
| `recurring` | BOOLEAN | Default false |
| `created_at` | TIMESTAMP | Default now |

---

## 5. Seed Data

Create these default categories for every new user on signup:

```python
DEFAULT_CATEGORIES = [
    {"name": "Salary",           "icon": "cash",               "color": "#10B981", "type": "income"},
    {"name": "Freelance",        "icon": "laptop",             "color": "#6366F1", "type": "income"},
    {"name": "Investments",      "icon": "trending-up",        "color": "#8B5CF6", "type": "income"},
    {"name": "Food & Drinks",    "icon": "restaurant",         "color": "#F59E0B", "type": "expense"},
    {"name": "Transport",        "icon": "car",                "color": "#3B82F6", "type": "expense"},
    {"name": "Shopping",         "icon": "cart",               "color": "#EC4899", "type": "expense"},
    {"name": "Entertainment",    "icon": "game-controller",    "color": "#F97316", "type": "expense"},
    {"name": "Health",           "icon": "fitness",            "color": "#EF4444", "type": "expense"},
    {"name": "Bills & Utilities","icon": "flash",              "color": "#14B8A6", "type": "expense"},
    {"name": "Education",        "icon": "school",             "color": "#0EA5E9", "type": "expense"},
    {"name": "Gifts",            "icon": "gift",               "color": "#D946EF", "type": "both"},
    {"name": "Other",            "icon": "ellipsis-horizontal","color": "#6B7280", "type": "both"},
]
```

---

## 6. What the Backend Does NOT Need

- **Exchange rates** -- the frontend fetches these directly from `https://open.er-api.com/v6/latest/USD` and caches locally.
- **User preferences** (currency, theme, locale) -- stored in AsyncStorage on the device.
- **Onboarding state** -- stored locally.

---

## 7. Frontend Connection

Once the backend is running, update the frontend:

1. In `services/api-client.ts`, set `USE_MOCK = false`
2. Set the `EXPO_PUBLIC_API_URL` env variable to your backend URL (or use the default `http://localhost:8000/api/v1`)

---

## 8. CORS

The backend should allow requests from all origins during development. For FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 9. Project Structure (suggested)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, router mounting
│   ├── config.py             # Settings (DB URL, JWT secret, etc.)
│   ├── database.py           # SQLAlchemy engine & session
│   ├── models/
│   │   ├── user.py
│   │   ├── transaction.py
│   │   └── category.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── transaction.py
│   │   └── category.py
│   ├── routers/
│   │   ├── auth.py           # /auth/*
│   │   ├── transactions.py   # /transactions/*
│   │   └── categories.py     # /categories/*
│   ├── services/
│   │   ├── auth.py           # JWT, password hashing, social token verify
│   │   └── stats.py          # Transaction stats aggregation
│   └── dependencies.py       # get_current_user, get_db
├── alembic/
│   └── versions/
├── alembic.ini
├── requirements.txt
└── .env
```