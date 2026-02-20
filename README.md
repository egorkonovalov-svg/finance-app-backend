# FinTrack Backend API

A comprehensive FastAPI-based backend service for the FinTrack personal finance management application. This RESTful API provides secure authentication, transaction management, category organization, and financial analytics for tracking income and expenses.

## Overview

FinTrack Backend is a modern, async-first Python backend built with FastAPI that powers a React Native mobile application. It implements email-based two-factor authentication (2FA), JWT-based session management, and provides a complete API for managing personal financial data including transactions, categories, and statistical insights.

## Features

### Authentication & Security
- **Email-based 2FA**: Two-step authentication flow with 6-digit verification codes sent via email
- **JWT Authentication**: Secure token-based authentication with configurable expiration
- **Password Security**: Bcrypt password hashing for secure credential storage
- **Social Authentication**: Support for Google and Apple OAuth integration
- **Email Verification**: New users must verify their email before accessing the application
- **Session Management**: Secure session handling with verification code expiration and attempt limiting

### Transaction Management
- **CRUD Operations**: Full create, read, update, and delete support for financial transactions
- **Advanced Filtering**: Filter transactions by type (income/expense), category, date range, amount range, and text search
- **Pagination**: Efficient pagination for large transaction lists
- **Currency Support**: Multi-currency transaction recording (stored in USD)
- **Recurring Transactions**: Support for marking transactions as recurring
- **Transaction Notes**: Optional notes for additional transaction details

### Category Management
- **Custom Categories**: Users can create, update, and delete their own categories
- **Default Categories**: 12 pre-seeded default categories for new users (Salary, Freelance, Investments, Food & Drinks, Transport, Shopping, Entertainment, Health, Bills & Utilities, Education, Gifts, Other)
- **Category Types**: Categories support income, expense, or both transaction types
- **Visual Customization**: Each category includes an icon and color for UI display
- **User-Scoped**: All categories are user-specific and private

### Analytics & Statistics
- **Monthly Statistics**: Comprehensive monthly financial overview
- **Income/Expense Totals**: Aggregate totals for income and expenses
- **Balance Calculation**: Automatic balance calculation (income - expenses)
- **Category Breakdown**: Expense breakdown by category with associated colors
- **Daily Trends**: Daily income and expense trends for the requested month
- **Date Range Support**: Flexible date filtering for custom reporting periods

### Developer Tools
- **Database Reset**: Development endpoint for resetting the database schema
- **Health Check**: Application health monitoring endpoint
- **API Documentation**: Interactive Swagger/OpenAPI documentation (available in local/staging environments)

## Technology Stack

- **Framework**: FastAPI 0.129+ (Python 3.14)
- **Database**: PostgreSQL 17+ with asyncpg driver
- **ORM**: SQLAlchemy 2.0 (async mode)
- **Migrations**: Alembic for database schema management
- **Authentication**: python-jose for JWT, bcrypt for password hashing
- **Email**: aiosmtplib for SMTP email delivery
- **Server**: Uvicorn with async support
- **Validation**: Pydantic for request/response validation
- **HTTP Client**: httpx for external API calls (OAuth providers)

## Project Structure

```
finance-app-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Application settings and environment variables
│   ├── database.py             # SQLAlchemy async engine and session configuration
│   ├── dependencies.py          # FastAPI dependencies (get_db, get_current_user)
│   ├── models/                 # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── user.py             # User model
│   │   ├── category.py         # Category model
│   │   ├── transaction.py     # Transaction model
│   │   └── verification_code.py # Email verification code model
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── auth.py             # Authentication schemas
│   │   ├── category.py         # Category schemas
│   │   └── transaction.py     # Transaction schemas
│   ├── routers/                # API route handlers
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── categories.py       # Category management endpoints
│   │   ├── transactions.py     # Transaction endpoints
│   │   └── dev.py              # Development utilities
│   └── services/               # Business logic services
│       ├── auth.py             # Authentication utilities (JWT, password hashing, verification)
│       ├── email.py            # Email sending service
│       └── stats.py            # Statistics aggregation service
├── alembic/                    # Database migration scripts
│   ├── env.py                  # Alembic environment configuration
│   └── versions/               # Migration version files
├── alembic.ini                 # Alembic configuration
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not committed)
└── README.md                   # This file
```

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /auth/signup` - Register a new user (returns verification session)
- `POST /auth/login` - Authenticate with email/password (returns verification session)
- `POST /auth/verify-code` - Verify email code and complete authentication (returns JWT)
- `POST /auth/resend-code` - Request a new verification code
- `POST /auth/social` - Authenticate via Google/Apple OAuth (bypasses 2FA)
- `GET /auth/me` - Get current authenticated user (requires JWT)
- `POST /auth/logout` - Logout (requires JWT)

### Transactions (`/api/v1/transactions`)
- `GET /transactions` - List transactions with filtering and pagination
- `GET /transactions/{id}` - Get a single transaction
- `POST /transactions` - Create a new transaction
- `PUT /transactions/{id}` - Update a transaction
- `DELETE /transactions/{id}` - Delete a transaction
- `GET /transactions/stats` - Get monthly statistics and analytics

### Categories (`/api/v1/categories`)
- `GET /categories` - List all user categories
- `POST /categories` - Create a new category
- `PUT /categories/{id}` - Update a category
- `DELETE /categories/{id}` - Delete a category

### Development (`/api/v1/dev`)
- `POST /dev/reset-db` - Drop and recreate all database tables

## Database Schema

### Users Table
- `id` (UUID, Primary Key)
- `email` (String, Unique, Not Null)
- `password_hash` (String, Nullable for social auth users)
- `name` (String, Nullable)
- `avatar` (String, Nullable - URL)
- `provider` (String, Nullable - "google", "apple", or null)
- `is_verified` (Boolean, Default False)
- `created_at` (Timestamp)

### Categories Table
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key → users.id)
- `name` (String, Not Null)
- `icon` (String, Not Null - Ionicons icon name)
- `color` (String, Not Null - Hex color code)
- `type` (String, Not Null - "income", "expense", or "both")

### Transactions Table
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key → users.id)
- `type` (String, Not Null - "income" or "expense")
- `amount` (Decimal(12,2), Not Null - stored in USD)
- `currency` (String(3), Not Null - currency code at time of entry)
- `category` (String, Not Null - category name)
- `note` (Text, Nullable)
- `date` (Timestamp, Not Null)
- `recurring` (Boolean, Default False)
- `created_at` (Timestamp)

### Verification Codes Table
- `id` (UUID, Primary Key - serves as session_id)
- `user_id` (UUID, Foreign Key → users.id)
- `code` (String(6), Not Null - 6-digit verification code)
- `purpose` (String(10), Not Null - "signup" or "login")
- `expires_at` (Timestamp, Not Null - 10 minutes from creation)
- `used` (Boolean, Default False)
- `attempts` (Integer, Default 0 - tracks wrong code attempts)
- `created_at` (Timestamp)

## Security Features

- **Email Verification**: All new users must verify their email before accessing the application
- **Code Expiration**: Verification codes expire after 10 minutes
- **Attempt Limiting**: Maximum 5 wrong code attempts per session before invalidation
- **Resend Limiting**: Maximum 3 code resends per session
- **JWT Expiration**: Configurable JWT token expiration (default 60 minutes)
- **Password Hashing**: Bcrypt with automatic salt generation
- **CORS Configuration**: Configurable CORS for frontend integration
- **Input Validation**: Pydantic schemas validate all request data
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection attacks

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/fintrack

# JWT Configuration
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Environment
ENVIRONMENT=local  # Options: local, staging, production

# SMTP Configuration (for email verification codes)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
VERIFICATION_CODE_EXPIRE_MINUTES=10
```

## Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd finance-app-backend
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**
   ```bash
   createdb fintrack
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env  # If you have an example file
   # Edit .env with your configuration
   ```

6. **Run database migrations** (if using Alembic)
   ```bash
   alembic upgrade head
   ```

7. **Start the development server**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

8. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Default Categories

When a new user signs up and verifies their email, the following 12 default categories are automatically created:

**Income Categories:**
- Salary (cash icon, #10B981)
- Freelance (laptop icon, #6366F1)
- Investments (trending-up icon, #8B5CF6)

**Expense Categories:**
- Food & Drinks (restaurant icon, #F59E0B)
- Transport (car icon, #3B82F6)
- Shopping (cart icon, #EC4899)
- Entertainment (game-controller icon, #F97316)
- Health (fitness icon, #EF4444)
- Bills & Utilities (flash icon, #14B8A6)
- Education (school icon, #0EA5E9)

**Both Types:**
- Gifts (gift icon, #D946EF)
- Other (ellipsis-horizontal icon, #6B7280)

## Development Notes

- **Database Reset**: The application automatically drops and recreates all tables on startup when `ENVIRONMENT=local`. This is controlled in `app/main.py` lifespan function.
- **Email Fallback**: If SMTP is not configured, verification codes are printed to the server console for development purposes.
- **API Documentation**: Swagger docs are only available in `local` and `staging` environments for security.
- **Async Operations**: All database operations use async/await for optimal performance.
- **Transaction Isolation**: Each API request uses its own database session with proper transaction handling.

## API Response Format

### Success Responses
- `200 OK` - Successful GET/PUT requests
- `201 Created` - Successful POST requests (resource created)
- `204 No Content` - Successful DELETE requests

### Error Responses
All errors follow this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400 Bad Request` - Invalid request data or expired verification codes
- `401 Unauthorized` - Invalid or missing authentication token
- `403 Forbidden` - User not verified or insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Email already registered
- `429 Too Many Requests` - Rate limit exceeded (too many code attempts/resends)

## Testing

The API can be tested using:
- **Swagger UI**: Interactive testing at `/docs` endpoint
- **curl**: Command-line HTTP requests
- **Postman**: API testing tool
- **Frontend Application**: React Native Expo app

Example signup flow:
1. `POST /auth/signup` with email, password, name
2. Receive `session_id` in response
3. Check email (or server console) for 6-digit code
4. `POST /auth/verify-code` with `session_id` and code
5. Receive JWT token in response
6. Use JWT token in `Authorization: Bearer <token>` header for protected endpoints

## Production Considerations

- **Change JWT_SECRET**: Use a strong, randomly generated secret in production
- **Configure SMTP**: Set up proper email service (Gmail, SendGrid, Mailgun, etc.)
- **Database Backups**: Implement regular database backups
- **Rate Limiting**: Consider adding rate limiting middleware
- **Monitoring**: Set up application monitoring and logging
- **HTTPS**: Use HTTPS in production (configure reverse proxy like Nginx)
- **Environment Variables**: Never commit `.env` file to version control
- **Database Migrations**: Use Alembic migrations for schema changes in production
- **Disable Auto-Drop**: Remove the `drop_all` in lifespan for production

## License

[Specify your license here]

## Support

For issues, questions, or contributions, please [specify your support channels].
