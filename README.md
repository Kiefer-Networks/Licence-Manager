# Licence Management System

A comprehensive SaaS license management platform for enterprises to track, manage, and optimize their software subscriptions across multiple providers.

## Features

### License Management
- **Multi-Provider Support**: Track licenses from 50+ SaaS providers including Microsoft 365, Google Workspace, Salesforce, Slack, Zoom, JetBrains, and more
- **Automatic Synchronization**: Connect to provider APIs for real-time license data
- **License Lifecycle Tracking**: Monitor expiring, cancelled, and pending licenses
- **Cost Tracking**: Track monthly and annual costs per license, provider, and department

### Employee Management
- **HR Integration**: Sync employees from HiBob, Personio, or manage manually
- **License Assignment**: Automatically match licenses to employees by email
- **Offboarding Detection**: Identify licenses still assigned to departed employees
- **Department Cost Allocation**: Track software costs per department

### Reporting & Analytics
- **Utilization Reports**: See assigned vs unassigned licenses
- **Cost Trend Analysis**: Track spending over time with visual charts
- **Inactive License Detection**: Find licenses unused for 30+ days
- **External User Tracking**: Identify licenses assigned to non-company emails
- **Duplicate Account Detection**: Find users with multiple accounts
- **License Recommendations**: Get actionable suggestions to reduce costs

### Administration
- **Role-Based Access Control**: Granular permissions for admins and users
- **Audit Logging**: Complete history of all system changes
- **Service Accounts**: Manage room systems and shared licenses separately
- **Admin Accounts**: Track privileged provider admin access

### User Experience
- **Localization**: Full German and English support
- **Locale Preferences**: Customizable date, number, and currency formats
- **Dark Mode**: System-aware or manual theme selection
- **Responsive Design**: Works on desktop, tablet, and mobile

## Technology Stack

### Backend
- **Python 3.12** with FastAPI
- **PostgreSQL 16** for data persistence
- **Redis 7** for caching and rate limiting
- **SQLAlchemy 2.0** with async support
- **Alembic** for database migrations
- **Pydantic** for data validation

### Frontend
- **Next.js 16** with App Router
- **React 19** with Server Components
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** component library
- **next-intl** for internationalization
- **NextAuth.js** for authentication

### Infrastructure
- **Docker** with multi-stage builds (linux/amd64)
- **GitHub Actions** for CI/CD (builds on version tags)
- **GitHub Container Registry** for images

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local development)
- Python 3.12+ (for local development)
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:Kiefer-Networks/Licence-Manager.git
   cd Licence-Manager
   ```

2. **Start infrastructure services**
   ```bash
   docker compose up -d postgres redis
   ```

3. **Set up the backend**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"

   # Copy and configure environment
   cp .env.example .env
   # Edit .env with your settings

   # Run migrations
   alembic upgrade head

   # Start the server
   uvicorn licence_api.main:app --reload
   ```

4. **Set up the frontend**
   ```bash
   cd frontend
   npm install

   # Copy and configure environment
   cp .env.example .env.local
   # Edit .env.local with your settings

   # Start the dev server
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Environment Variables

#### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://licence:password@localhost:5432/licence

# Redis
REDIS_URL=redis://localhost:6379

# Security (generate with: openssl rand -base64 32)
ENCRYPTION_KEY=your-32-byte-base64-key
JWT_SECRET=your-jwt-secret

# OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Production Deployment

### Using Docker Compose

1. **Configure environment**
   ```bash
   cp .env.prod.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Pull and start containers**
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

3. **Set up reverse proxy**

   Configure your preferred reverse proxy (nginx, Caddy, Traefik) to:
   - Proxy `/` to `localhost:3000` (frontend)
   - Proxy `/api` to `localhost:8000` (backend)
   - Handle SSL termination
   - Add security headers

### Exposed Ports

| Port | Service | Description |
|------|---------|-------------|
| 3000 | Frontend | Next.js application |
| 8000 | Backend | FastAPI application |

### Docker Images

Images are automatically built and pushed to GitHub Container Registry when a new version tag is created (e.g., `v1.0.0`).

```bash
# Pull latest release
docker pull ghcr.io/kiefer-networks/licence-manager/backend:latest
docker pull ghcr.io/kiefer-networks/licence-manager/frontend:latest

# Pull specific version
docker pull ghcr.io/kiefer-networks/licence-manager/backend:1.0.0
docker pull ghcr.io/kiefer-networks/licence-manager/frontend:1.0.0
```

To create a new release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Security Considerations

- All containers run as non-root users
- `no-new-privileges` security option enabled
- Backend network is internal (no external access)
- Redis requires password authentication
- Database credentials should use strong passwords
- Enable SSL/TLS on your reverse proxy
- Configure CORS origins appropriately

## Project Structure

```
Licence-Manager/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── src/licence_api/
│   │   ├── models/           # ORM and DTO models
│   │   ├── repositories/     # Data access layer
│   │   ├── services/         # Business logic
│   │   ├── routers/          # API endpoints
│   │   └── providers/        # SaaS provider integrations
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages
│   │   ├── components/       # React components
│   │   └── lib/              # Utilities
│   ├── messages/             # i18n translations
│   ├── Dockerfile
│   └── package.json
├── docs/                     # Documentation
│   └── provider-setup/       # Provider integration guides
├── docker-compose.yml        # Development
├── docker-compose.prod.yml   # Production
└── .github/workflows/        # CI/CD
```

## API Documentation

The API is documented using OpenAPI/Swagger:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Authentication

The API uses JWT tokens for authentication. Obtain a token via OAuth login through the frontend, then include it in API requests:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/providers
```

## Supported Providers

| Provider | Sync Method | Features |
|----------|-------------|----------|
| Microsoft 365 | Graph API | Licenses, users, groups |
| Google Workspace | Admin SDK | Licenses, users, domains |
| Slack | SCIM API | Users, workspaces |
| Zoom | REST API | Users, meetings |
| Salesforce | REST API | Users, licenses |
| JetBrains | License Server | Licenses, assignments |
| GitHub | REST API | Seats, members |
| Atlassian | REST API | Users, products |
| And 40+ more... | Various | - |

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting
cd backend
ruff check .
mypy .

# Frontend linting
cd frontend
npm run lint
npm run type-check
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software. All rights reserved.

## Support

For support, please contact your system administrator or open an issue in the repository.
