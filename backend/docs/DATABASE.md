# Database Migration Guide

## Overview

This database uses **Alembic** for migrations. All migrations are stored in `alembic/versions/`.

## Quick Start

### Initial Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your database credentials

# Create database and run migrations
python scripts/init_db.py --create-db --seed
```

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade +1

# Rollback one migration
alembic downgrade -1

# Rollback to base (drop all tables)
alembic downgrade base

# View current version
alembic current

# View migration history
alembic history
```

## Creating New Migrations

### Auto-generate from Models

```bash
# After modifying app/models/*.py, auto-generate migration
alembic revision --autogenerate -m "description of changes"
```

### Manual Migration

```bash
# Create empty migration file
alembic revision -m "description of changes"
```

Then edit the generated file in `alembic/versions/`:

```python
def upgrade() -> None:
    # Add your migration logic here
    pass

def downgrade() -> None:
    # Add rollback logic here
    pass
```

## Database Tables

| Table | Description | Foreign Keys |
|-------|-------------|--------------|
| `users` | User accounts | - |
| `notes` | Note content | users.id |
| `note_attachments` | File attachments | notes.id |
| `note_versions` | Version history | notes.id |
| `share_links` | Public sharing | notes.id, users.id |
| `tags` | Note tags | users.id |
| `note_tags` | Note-tag mapping | notes.id, tags.id |
| `categories` | Note categories | users.id, categories.id |
| `document_chunks` | RAG chunks | notes.id, users.id |
| `search_history` | Search queries | users.id, notes.id |
| `search_feedback` | Search feedback | search_history.id, users.id |
| `activity_logs` | Audit trail | users.id, notes.id |

## Extensions

### pgvector

The database uses the `pgvector` extension for semantic search:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Vector Index

The `document_chunks.embedding` column has an ivfflat index for similarity search:

```sql
CREATE INDEX ix_document_chunks_embedding
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Triggers

### Auto-update `updated_at`

The following tables have automatic `updated_at` triggers:

- `users`
- `notes`
- `categories`
- `document_chunks`

The trigger function:

```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Backup & Restore

### Backup

```bash
# Using pg_dump
pg_dump -h localhost -U user -d team1 -Fc > backup.dump

# Using Docker (if applicable)
docker exec postgres_container pg_dump -U user team1 > backup.sql
```

### Restore

```bash
# Using pg_restore
pg_restore -h localhost -U user -d team1 -Fc backup.dump

# Using Docker
docker exec -i postgres_container psql -U user team1 < backup.sql
```

## Troubleshooting

### Migration Conflicts

If you encounter migration conflicts:

```bash
# Reset to a specific version
alembic downgrade <revision_id>

# Then upgrade again
alembic upgrade head
```

### Database Locks

If migrations hang due to locks:

```sql
-- View locks
SELECT * FROM pg_stat_activity WHERE datname = 'team1';

-- Kill specific connection
SELECT pg_terminate_backend(pid);
```

### Missing pgvector Extension

If pgvector is not installed:

```bash
# Install on Ubuntu/Debian
sudo apt-get install postgresql-16-pgvector

# Install on macOS (Homebrew)
brew install pgvector

# Or load the extension manually
psql -d team1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
```
