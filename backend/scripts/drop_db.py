#!/usr/bin/env python3
"""Database reset script.

WARNING: This will delete all data! Use with caution.

Usage:
    python scripts/drop_db.py --yes
"""
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command

from app.core.config import get_settings

settings = get_settings()


def drop_tables():
    """Drop all tables using Alembic downgrade."""
    print("WARNING: This will delete all data!")
    print("Database:", settings.sync_database_url)

    # Get Alembic config
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.sync_database_url)

    # Run downgrade to base
    command.downgrade(alembic_cfg, "base")

    print("All tables dropped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Drop all database tables")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    if not args.yes:
        response = input("Are you sure you want to drop all tables? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted")
            sys.exit(0)

    try:
        drop_tables()
        print("\nDatabase reset complete!")

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
