import os
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

# Add project root to path
# This ensures that imports like 'backend.app' work correctly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set the FLASK_APP environment variable.
# This tells Flask where to find the application factory.
# It's good practice to explicitly set it here for manage.py,
# especially if running Flask commands directly (e.g., `flask run`).
os.environ['FLASK_APP'] = 'backend.app'

from flask.cli import FlaskGroup
from backend.app import create_app
from backend.models import db, User, Task # Assuming db and models are defined here

# Attempt to import Flask-Migrate.
# If Flask-Migrate is installed and configured within `create_app`,
# its commands (e.g., `flask db init`, `flask db migrate`, `flask db upgrade`)
# will automatically be registered with the FlaskGroup CLI.
try:
    from flask_migrate import Migrate
    # No explicit initialization of Migrate here, as it's typically done
    # within the `create_app` function or in a dedicated `extensions.py` file.
    # FlaskGroup will automatically pick up the commands if Migrate is initialized
    # with the app instance returned by `create_app`.
    pass
except ImportError:
    print("Warning: Flask-Migrate not installed. Database migration commands will not be available.", file=sys.stderr)
    print("Install with: pip install Flask-Migrate", file=sys.stderr)


def make_shell_context():
    """
    Returns application and database instances, and models
    to the shell for easy use with 'flask shell'.
    When `flask shell` is run, FlaskGroup calls `create_app` to get the app,
    then calls this function to populate the shell's namespace.
    """
    # Create an app instance specifically for the shell context.
    # This ensures the app context is available for database operations within the shell.
    app_instance = create_app(os.getenv('FLASK_ENV') or 'development')
    # Push an application context to ensure database operations (e.g., db.session)
    # work correctly without explicit `with app.app_context():` in the shell.
    app_instance.app_context().push()
    return dict(app=app_instance, db=db, User=User, Task=Task)

# Create a FlaskGroup instance.
# This provides the 'flask' command and its subcommands (e.g., `flask run`, `flask shell`).
# `create_app` is passed as a callable that FlaskGroup will use to get the app instance
# when a command is executed.
# `shell_context_processor` provides the context for the `flask shell` command.
cli = FlaskGroup(create_app=create_app, shell_context_processor=make_shell_context)

# Custom CLI commands can be added using the @cli.command() decorator.

@cli.command()
def test():
    """Runs the unit tests for the application."""
    import unittest
    # Discover tests in the 'tests' directory relative to the project root.
    # Assumes tests are located in `project_root/tests`.
    tests_dir = project_root / 'tests'
    if not tests_dir.is_dir():
        print(f"Error: 'tests' directory not found at {tests_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Add the tests directory to sys.path temporarily for test discovery.
    # This allows `unittest.TestLoader().discover` to find test modules correctly.
    sys.path.insert(0, str(tests_dir))
    
    try:
        # Discover all test files matching 'test_*.py' pattern within the tests directory.
        tests = unittest.TestLoader().discover(str(tests_dir), pattern='test_*.py')
        # Run the discovered tests with verbose output.
        unittest.TextTestRunner(verbosity=2).run(tests)
    finally:
        # Ensure the tests directory is removed from sys.path after execution.
        sys.path.remove(str(tests_dir))


@cli.command()
def deploy():
    """
    Run deployment tasks for the application.
    This command can be extended to include various steps necessary for deployment,
    such as applying database migrations, seeding initial data, creating an admin user, etc.
    """
    print("Running deployment tasks...")
    
    # Example: Placeholder for database migrations.
    # In a real deployment, you would typically run `flask db upgrade` separately
    # or integrate it directly here using subprocess calls if needed.
    print("  - Database migrations (ensure 'flask db upgrade' is run separately if needed).")
    
    # Example: Creating an initial admin user.
    # This requires an application context to interact with the database.
    # For production, consider using environment variables or prompting for admin credentials.
    admin_email = os.getenv('FLASK_ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.getenv('FLASK_ADMIN_PASSWORD', 'admin_password') # WARNING: Do not hardcode in production!

    with create_app(os.getenv('FLASK_ENV') or 'development').app_context():
        if not User.query.filter_by(email=admin_email).first():
            admin_user = User(email=admin_email, password_hash=generate_password_hash(admin_password))
            db.session.add(admin_user)
            db.session.commit()
            print(f"  - Admin user '{admin_email}' created.")
        else:
            print(f"  - Admin user '{admin_email}' already exists.")
            
    print("Deployment tasks completed.")


if __name__ == '__main__':
    # This block makes the script executable directly from the command line,
    # e.g., `python manage.py run` or `python manage.py test`.
    # It invokes the FlaskGroup CLI, which then dispatches to the appropriate command.
    cli()