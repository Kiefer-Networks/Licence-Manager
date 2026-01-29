# License Management System

A license management system to track software licenses across multiple providers, integrated with HiBob as HRIS source of truth.

## Features

- **HiBob Integration**: Sync employees from your HRIS
- **Multi-Provider Support**: Google Workspace, Slack, OpenAI, Figma, Cursor
- **Dashboard**: Overview of licenses, costs, and alerts
- **Reports**: Inactive licenses, offboarding, cost analysis
- **Slack Notifications**: Alerts for offboarding and inactive licenses
- **Role-Based Access**: Admin and Viewer roles

## Tech Stack

- **Backend**: Python 3.12+ with FastAPI
- **Frontend**: TypeScript with Next.js 14+
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0 + Alembic
- **Authentication**: Google OAuth 2.0

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.12+

### Setup

1. Clone the repository and copy the environment file:

```bash
cp .env.example .env
```

2. Generate secrets and update `.env`:

```bash
# Generate encryption key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT secret
openssl rand -base64 32

# Generate NextAuth secret
openssl rand -base64 32
```

3. Set up Google OAuth (see `docs/setup-google-oauth.md`)

4. Start the services:

```bash
docker-compose up -d
```

5. Run database migrations:

```bash
cd backend
alembic upgrade head
```

6. Access the application at http://localhost:3000

## Development

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn licence_api.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API Documentation

When running in development mode, API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
licence/
├── docker-compose.yml
├── backend/
│   ├── src/licence_api/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Configuration
│   │   ├── models/           # Domain, ORM, DTO models
│   │   ├── repositories/     # Database access
│   │   ├── services/         # Business logic
│   │   ├── providers/        # Provider integrations
│   │   ├── routers/          # API endpoints
│   │   ├── security/         # Auth & encryption
│   │   └── tasks/            # Background jobs
│   └── alembic/              # Database migrations
├── frontend/
│   └── src/
│       ├── app/              # Next.js pages
│       ├── components/       # React components
│       └── lib/              # Utilities
└── docs/                     # Documentation
```

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `ENCRYPTION_KEY` | 32-byte key for credential encryption |
| `JWT_SECRET` | Secret for JWT tokens |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `NEXTAUTH_URL` | NextAuth.js URL |
| `NEXTAUTH_SECRET` | NextAuth.js secret |

## License

MIT
