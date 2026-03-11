#!/usr/bin/env python3
"""Database initialization script.

This script creates the database, applies migrations, and optionally seeds data.

Usage:
    python scripts/init_db.py [--create-db] [--seed]

Options:
    --create-db    Create the database if it doesn't exist
    --seed         Seed with sample data
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic import command

from app.core.config import get_settings

settings = get_settings()


def create_database():
    """Create the database if it doesn't exist.

    Requires superuser privileges. Uses psycopg3 for synchronous connection.
    """
    try:
        import psycopg
        from urllib.parse import urlparse

        # Parse database URL
        parsed = urlparse(settings.DATABASE_URL)
        dbname = parsed.path[1:]  # Remove leading slash
        user = parsed.username or "postgres"
        password = parsed.password
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432

        # Connect to postgres database to create our database
        conn = psycopg.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port,
            autocommit=True,
        )

        conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (dbname,))

        # Check if database exists
        cursor = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        )
        if not cursor.fetchone():
            print(f"Creating database: {dbname}")
            conn.execute(f"CREATE DATABASE {dbname} OWNER {user}")
            print(f"Database '{dbname}' created successfully")
        else:
            print(f"Database '{dbname}' already exists")

        conn.close()

    except ImportError:
        print("Warning: psycopg3 not installed. Cannot create database automatically.")
        print("Please create the database manually:")
        print(f"  createdb {settings.DATABASE_URL.split('/')[-1]}")
    except Exception as e:
        print(f"Error creating database: {e}")
        raise


def run_migrations():
    """Run Alembic migrations to create tables."""
    print("Running database migrations...")

    # Get Alembic config
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.sync_database_url)

    # Run upgrade
    command.upgrade(alembic_cfg, "head")

    print("Migrations completed successfully")


async def seed_database():
    """Seed database with sample data for development."""
    print("Seeding database with sample data...")

    from app.core.database import async_session_maker
    from app.models.user import User
    from app.models.note import Note, Category, Tag
    from app.core.security import get_password_hash

    async with async_session_maker() as session:
        # Create test user
        user = User(
            email="demo@example.com",
            username="demo",
            hashed_password=get_password_hash("demo123"),
            full_name="Demo User",
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        # Create sample category
        category = Category(
            user_id=user.id,
            name="Work",
            description="Work-related notes",
            icon="briefcase",
            color="#3b82f6",
        )
        session.add(category)
        await session.flush()

        # Create sample tags
        tag1 = Tag(user_id=user.id, name="important", color="#ef4444")
        tag2 = Tag(user_id=user.id, name="todo", color="#f59e0b")
        session.add(tag1)
        session.add(tag2)
        await session.flush()

        # Create sample notes
        note1 = Note(
            user_id=user.id,
            title="Welcome to NotebookLLM",
            content="""# Welcome to NotebookLLM

This is your new intelligent note-taking application.

## Features

- **AI-Powered Search**: Find notes using semantic search
- **Rich Editing**: Write in Markdown with live preview
- **Tags & Categories**: Organize your notes
- **Share Links**: Share notes with others

## Getting Started

1. Create your first note
2. Add some tags
3. Try the AI search feature

Enjoy writing!""",
            is_pinned=True,
        )
        session.add(note1)

        note2 = Note(
            user_id=user.id,
            title="Project Ideas",
            content="""# Project Ideas

## AI Assistant
- Build a personal assistant
- Use LLM for context understanding
- Integrate with calendar and email

## Mobile App
- Cross-platform note-taking
- Offline support
- Cloud sync""",
        )
        session.add(note2)

        await session.commit()

    print("Sample data seeded successfully")
    print("  Login: demo / demo123")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize the database")
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Create the database if it doesn't exist",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed with sample data",
    )

    args = parser.parse_args()

    try:
        if args.create_db:
            create_database()

        run_migrations()

        if args.seed:
            asyncio.run(seed_database())

        print("\nDatabase initialization complete!")

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
