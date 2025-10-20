# Mini-CRM Repair Requests

A scalable repair request management system with FastAPI backend and Streamlit UI.

## Features

- **Public API** for customers to submit repair requests
- **Admin panel** to review, assign, and manage workers
- **Worker interface** to view and progress assigned requests
- **JWT authentication** with role-based access control
- **Pagination, search, and filtering** on all list endpoints
- **Docker containerization** with PostgreSQL database
- **Real-time status tracking** with timestamps

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and start services:**

```bash
git clone <repository-url>
cd TestTask
docker compose up -d
```

2. **Access the application:**

- **UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **API**: http://localhost:8000

3. **Default accounts:**

- **Admin**: `admin` / `admin123`
- **Worker**: `worker` / `worker123`

### Manual Setup

1. **Install dependencies:**

```bash
pip install poetry
poetry install
```

2. **Setup database:**

```bash
# Start PostgreSQL
docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15

# Run migrations
alembic upgrade head
```

3. **Start services:**

```bash
# Terminal 1 - API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - UI
streamlit run ui/app.py --server.port 8501
```

## API Documentation

### Authentication

**Login:**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Response:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Public Endpoints

**Submit repair request:**

```bash
curl -X POST http://localhost:8000/public/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Broken laptop screen",
    "description": "Screen flickers and has dead pixels",
    "client": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890"
    }
  }'
```

### Protected Endpoints (Require JWT)

**List tickets:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/tickets/?page=1&size=10&status=new"
```

**Assign ticket to worker:**

```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"worker_id": 2}' \
  http://localhost:8000/tickets/1/assign
```

**Update ticket status:**

```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_status": "in_progress"}' \
  http://localhost:8000/tickets/1/status
```

**Create worker (admin only):**

```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "worker1",
    "password": "worker123",
    "role": "worker"
  }' \
  http://localhost:8000/users/
```

**Get worker stats:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/tickets/stats?worker_id=2"
```

### API Endpoints Summary

| Method   | Endpoint               | Description           | Auth  |
| -------- | ---------------------- | --------------------- | ----- |
| `POST`   | `/auth/login`          | User login            | -     |
| `GET`    | `/auth/me`             | Get current user      | ✓     |
| `POST`   | `/public/tickets`      | Submit repair request | -     |
| `GET`    | `/tickets/`            | List tickets          | ✓     |
| `POST`   | `/tickets/{id}/assign` | Assign to worker      | Admin |
| `POST`   | `/tickets/{id}/status` | Update status         | ✓     |
| `GET`    | `/tickets/stats`       | Worker statistics     | Admin |
| `GET`    | `/users/`              | List workers          | Admin |
| `POST`   | `/users/`              | Create worker         | Admin |
| `DELETE` | `/users/{id}`          | Delete worker         | Admin |

### Query Parameters

**Tickets list:**

- `page` (int): Page number (default: 1)
- `size` (int): Page size 1-100 (default: 10)
- `search` (str): Search by title
- `status` (str): Filter by status (`new`, `in_progress`, `done`)
- `worker_id` (int): Filter by worker (admin only)

**Status values:**

- `new` - Unassigned tickets
- `in_progress` - Assigned and being worked on
- `done` - Completed tickets

## User Roles

### Admin

- Full access to all tickets
- Create/delete workers
- Assign tickets to workers
- View worker statistics
- Access to all endpoints

### Worker

- View only assigned tickets
- Update status of assigned tickets
- Cannot access other workers' tickets

## Database Schema

**Users:**

- `id`, `username`, `password_hash`, `role`, `created_at`

**Clients:**

- `id`, `name`, `email`, `phone`, `created_at`

**Tickets:**

- `id`, `title`, `description`, `status`, `viewed`
- `client_id`, `worker_id`
- `created_at`, `updated_at`
- `assigned_at`, `in_progress_at`, `done_at`
- `requester_ip`, `requester_ua`

## Development

### Project Structure

```
TestTask/
├── app/                    # FastAPI application
│   ├── main.py            # App entry point
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── security.py        # JWT & password hashing
│   ├── db.py             # Database configuration
│   └── routers/           # API endpoints
├── ui/                    # Streamlit UI
│   └── app.py            # Main UI application
├── alembic/               # Database migrations
├── docker-compose.yml     # Docker services
├── Dockerfile            # API container
└── pyproject.toml        # Dependencies
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/app

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Default users
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
WORKER_USERNAME=worker
WORKER_PASSWORD=worker123
```

### Running Tests

```bash
# Start test database
docker run -d --name test-postgres -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:15

# Run tests
pytest
```

## Production Deployment

### Docker Hub

1. **Build and push:**

```bash
docker build -t your-username/mini-crm-repair:latest .
docker push your-username/mini-crm-repair:latest
```

2. **Deploy:**

```bash
# Update docker-compose.yml with your image
docker compose up -d
```

### Environment Setup

```bash
# Production environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
export SECRET_KEY="your-production-secret-key"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="secure-password"
```

## Troubleshooting

### Common Issues

1. **Database connection failed:**

   - Check PostgreSQL is running
   - Verify DATABASE_URL format
   - Run migrations: `alembic upgrade head`

2. **JWT token expired:**

   - Re-login to get new token
   - Check ACCESS_TOKEN_EXPIRE_MINUTES

3. **Permission denied:**

   - Verify user role (admin/worker)
   - Check JWT token is valid

4. **Duplicate ticket error:**
   - System prevents exact duplicates (same title, description, email)
   - Modify request details to submit

### Logs

```bash
# View API logs
docker compose logs api

# View UI logs
docker compose logs ui

# View database logs
docker compose logs db
```

## License

MIT License - see LICENSE file for details.
