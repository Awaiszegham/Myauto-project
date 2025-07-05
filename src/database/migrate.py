"""
Database migration utilities for Flask-Migrate.
"""

from flask_migrate import upgrade, migrate, init, revision
import os

def init_migrations(app):
    """Initialize Flask-Migrate for the application."""
    with app.app_context():
        if not os.path.exists('migrations'):
            init()
            print("Migrations folder initialized")
        else:
            print("Migrations folder already exists")

def create_migration(app, message="Auto migration"):
    """Create a new migration."""
    with app.app_context():
        migrate(message=message)
        print(f"Migration created: {message}")

def upgrade_database(app):
    """Upgrade database to latest migration."""
    with app.app_context():
        upgrade()
        print("Database upgraded successfully")

def create_revision(app, message="Manual revision"):
    """Create a manual revision."""
    with app.app_context():
        revision(message=message)
        print(f"Revision created: {message}")

# Railway-specific migration helpers
def railway_migrate(app):
    """Handle migrations for Railway deployment."""
    with app.app_context():
        try:
            # Check if migrations folder exists
            if not os.path.exists('migrations'):
                print("Initializing migrations for Railway...")
                init()
            
            # Run migrations
            print("Running database migrations...")
            upgrade()
            print("Database migrations completed successfully")
            
        except Exception as e:
            print(f"Migration error: {e}")
            raise

def check_migration_status(app):
    """Check current migration status."""
    with app.app_context():
        from flask_migrate import current, show
        try:
            current_rev = current()
            print(f"Current migration: {current_rev}")
            show(current_rev)
        except Exception as e:
            print(f"Could not get migration status: {e}")
