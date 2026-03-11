# Team1 Backend API

FastAPI-based backend service for Team1 application.

## Features

- RESTful API with OpenAPI documentation
- PostgreSQL with async SQLAlchemy ORM
- Redis caching and rate limiting
- JWT authentication
- Structured logging with JSON output
- Prometheus metrics
- OpenTelemetry tracing
- Comprehensive middleware stack

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# or
pip install -e .

# Copy environment configuration
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload
```

### Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy app/
```

### Production

```bash
# Run with uvicorn (using gunicorn for multi-worker)
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Project Structure

```
backend/
├── app/
│   ├── api/           # API routes
│   ├── core/          # Core configuration
│   ├── models/        # ORM models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   ├── middleware/    # Custom middleware
│   └── utils/         # Utilities
├── tests/             # Test suite
├── alembic/           # Database migrations
└── scripts/           # Utility scripts
```
