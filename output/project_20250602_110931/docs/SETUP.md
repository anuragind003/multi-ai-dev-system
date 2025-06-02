# Simple Task Tracker - Setup Guide

This document provides comprehensive instructions for setting up the Simple Task Tracker application for both development and production environments.

## Table of Contents
1.  [Prerequisites](#prerequisites)
2.  [Development Environment Setup](#development-environment-setup)
    *   [Clone the Repository](#clone-the-repository)
    *   [Create and Activate Virtual Environment](#create-and-activate-virtual-environment)
    *   [Install Dependencies](#install-dependencies)
    *   [Database Setup (SQLite)](#database-setup-sqlite)
    *   [Environment Variables](#environment-variables)
    *   [Run the Application](#run-the-application)
    *   [Running Tests](#running-tests)
3.  [Production Environment Setup](#production-environment-setup)
    *   [Prerequisites for Production](#prerequisites-for-production)
    *   [Clone and Setup](#clone-and-setup-1)
    *   [Database Setup (PostgreSQL)](#database-setup-postgresql)
    *   [Environment Variables for Production](#environment-variables-for-production)
    *   [Running with a WSGI Server (Gunicorn)](#running-with-a-wsgi-server-gunicorn)
    *   [Web Server (Nginx - Optional but Recommended)](#web-server-nginx---optional-but-recommended)
    *   [Process Management (Systemd - Optional but Recommended)](#process-management-systemd---optional-but-recommended)
4.  [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Python 3.8 or higher**:
    ```bash
    python --version
    # Expected output: Python 3.8.x or higher
    ```
*   **pip (Python package installer)**: Usually comes with Python.
    ```bash
    pip --version
    # Expected output: pip 20.x.x or higher
    ```
*   **Git**: For cloning the repository.
    ```bash
    git --version
    # Expected output: git version x.x.x
    ```

## 2. Development Environment Setup

Follow these steps to set up the Simple Task Tracker for local development.

### Clone the Repository

First, clone the project repository to your local machine:

```bash
git clone https://github.com/your-username/simple-task-tracker.git
cd simple-task-tracker
```

### Create and Activate Virtual Environment

It's highly recommended to use a Python virtual environment to manage project dependencies.

```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```
You should see `(venv)` prefix in your terminal prompt, indicating the virtual environment is active.

### Install Dependencies

Install all required Python packages using `pip` and the `requirements.txt` file.
(If `requirements.txt` does not exist, you might need to generate it first using `pip freeze > requirements.txt` after manually installing core dependencies like `Flask`, `SQLAlchemy`, etc., or install them directly: `pip install Flask Flask-SQLAlchemy python-dotenv`)

```bash
pip install -r requirements.txt
```

### Database Setup (SQLite)

For development, Simple Task Tracker uses SQLite, which is a file-based database.

1.  **Create the `instance` directory**: This directory will hold the SQLite database file.
    ```bash
    mkdir -p instance
    ```

2.  **Initialize the database**: The application needs to create its database schema.
    *   If your project uses Flask-Migrate (recommended for production-grade apps):
        ```bash
        flask db upgrade
        ```
    *   If not using Flask-Migrate, you might have a custom script or need to run a command to create tables. Assuming your `app` object is accessible and `db` is your SQLAlchemy instance:
        ```bash
        # Ensure your virtual environment is active
        python -c "from app import create_app, db; app = create_app(); with app.app_context(): db.create_all()"
        ```
        This command will create the `app.db` file inside the `instance/` directory.

### Environment Variables

The application uses environment variables for configuration (e.g., database URL, secret key). Create a `.env` file in the root directory of the project.

1.  **Create `.env` file**:
    ```bash
    touch .env
    ```

2.  **Add the following content to `.env`**:
    ```dotenv
    # Flask application entry point (e.g., app.py or wsgi.py)
    FLASK_APP=app.py
    # Set to 'development' for development features (e.g., debug mode)
    FLASK_ENV=development
    # A strong, random secret key for session management and security.
    # For development, a simple string is fine, but use a complex one for production.
    SECRET_KEY='your_development_secret_key_here'
    # Database URL for SQLite (development database)
    DATABASE_URL='sqlite:///instance/app.db'
    # Optional: Set to 'True' to enable Flask's debug mode
    FLASK_DEBUG=True
    ```
    **Important**: Replace `'your_development_secret_key_here'` with a random string. For production, this must be a very strong, unique, and securely stored key.

### Run the Application

With the virtual environment active and dependencies installed, you can now run the Flask application.

```bash
flask run
```
This will start the development server, usually accessible at `http://127.0.0.1:5000/`.

### Running Tests

To ensure everything is working correctly, you can run the project's tests.
(Assuming `pytest` is used and installed via `requirements.txt`)

```bash
pytest
```

## 3. Production Environment Setup

Setting up for production requires more robust configurations for security, performance, and reliability.

### Prerequisites for Production

In addition to the development prerequisites, you'll likely need:

*   **PostgreSQL**: Install PostgreSQL server on your production machine.
*   **Gunicorn**: A Python WSGI HTTP Server for UNIX.
*   **Nginx (Optional but Recommended)**: A high-performance web server and reverse proxy.
*   **Systemd (Optional but Recommended)**: For managing the Gunicorn process.

### Clone and Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/simple-task-tracker.git /var/www/simple-task-tracker
    cd /var/www/simple-task-tracker
    ```
    (Using `/var/www/` is a common convention for web applications)

2.  **Create and activate virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    Ensure `gunicorn` is included in your `requirements.txt` or install it: `pip install gunicorn psycopg2-binary` (for PostgreSQL).

### Database Setup (PostgreSQL)

For production, PostgreSQL is recommended for its robustness and scalability.

1.  **Install PostgreSQL client libraries**:
    ```bash
    # On Debian/Ubuntu
    sudo apt update
    sudo apt install libpq-dev python3-dev

    # On CentOS/RHEL
    sudo yum install postgresql-devel python3-devel
    ```

2.  **Create a PostgreSQL database and user**:
    Log in to your PostgreSQL server (e.g., as `postgres` user):
    ```bash
    sudo -u postgres psql
    ```
    Inside `psql` prompt:
    ```sql
    CREATE DATABASE tasktracker_db;
    CREATE USER tasktracker_user WITH PASSWORD 'your_strong_db_password';
    GRANT ALL PRIVILEGES ON DATABASE tasktracker_db TO tasktracker_user;
    \q
    ```
    **Important**: Replace `'your_strong_db_password'` with a very strong, unique password.

3.  **Initialize the database schema**:
    Similar to development, but ensure the `DATABASE_URL` in your `.env` points to PostgreSQL.
    ```bash
    # Ensure your virtual environment is active
    # Ensure your .env file is configured for PostgreSQL (see next section)
    flask db upgrade
    # Or, if not using Flask-Migrate:
    # python -c "from app import create_app, db; app = create_app(); with app.app_context(): db.create_all()"
    ```

### Environment Variables for Production

Create a `.env` file in the project root (`/var/www/simple-task-tracker/.env`) with production-specific settings.

```dotenv
# Flask application entry point (e.g., wsgi.py for Gunicorn)
FLASK_APP=wsgi.py
# Set to 'production' for optimized performance and security
FLASK_ENV=production
# A very strong, unique, and securely generated secret key.
# DO NOT use the development key. Generate a new one (e.g., using os.urandom(24).hex())
SECRET_KEY='your_very_strong_production_secret_key_here'
# Database URL for PostgreSQL
DATABASE_URL='postgresql://tasktracker_user:your_strong_db_password@localhost:5432/tasktracker_db'
# Disable Flask's debug mode in production
FLASK_DEBUG=False
```
**Crucial**: Generate a truly random and complex `SECRET_KEY` for production. Store it securely (e.g., using a secrets manager or environment variables provided by your deployment platform).

### Running with a WSGI Server (Gunicorn)

Gunicorn is a production-ready WSGI server.

1.  **Create a `wsgi.py` file**:
    In your project root, create a `wsgi.py` file to serve as the entry point for Gunicorn.
    ```python
    # wsgi.py
    from app import create_app

    app = create_app()

    if __name__ == "__main__":
        app.run()
    ```
    (Assuming `app` is your main Flask application package/module and `create_app()` is your application factory function).

2.  **Test Gunicorn locally**:
    ```bash
    # Ensure virtual environment is active and .env is set up
    gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
    ```
    This runs Gunicorn with 4 worker processes, binding to all network interfaces on port 5000.

### Web Server (Nginx - Optional but Recommended)

Nginx acts as a reverse proxy, serving static files directly and forwarding dynamic requests to Gunicorn.

1.  **Install Nginx**:
    ```bash
    sudo apt install nginx # On Debian/Ubuntu
    # sudo yum install nginx # On CentOS/RHEL
    ```

2.  **Create an Nginx configuration file**:
    Create a new file, e.g., `/etc/nginx/sites-available/tasktracker`.

    ```nginx
    server {
        listen 80;
        server_name your_domain.com www.your_domain.com; # Replace with your domain or IP

        location /static {
            alias /var/www/simple-task-tracker/static; # Path to your static files
        }

        location / {
            proxy_pass http://127.0.0.1:5000; # Gunicorn listens on this address
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            include proxy_params; # Often found in /etc/nginx/proxy_params
        }
    }
    ```

3.  **Enable the Nginx configuration**:
    ```bash
    sudo ln -s /etc/nginx/sites-available/tasktracker /etc/nginx/sites-enabled/
    sudo nginx -t # Test Nginx configuration for syntax errors
    sudo systemctl restart nginx
    ```

### Process Management (Systemd - Optional but Recommended)

Systemd can manage the Gunicorn process, ensuring it starts on boot and restarts if it crashes.

1.  **Create a Systemd service file**:
    Create `/etc/systemd/system/tasktracker.service`.

    ```ini
    [Unit]
    Description=Gunicorn instance for Simple Task Tracker
    After=network.target

    [Service]
    User=www-data # Or a dedicated user for your application
    Group=www-data # Or a dedicated group
    WorkingDirectory=/var/www/simple-task-tracker
    Environment="PATH=/var/www/simple-task-tracker/venv/bin"
    ExecStart=/var/www/simple-task-tracker/venv/bin/gunicorn --workers 4 --bind unix:/tmp/tasktracker.sock -m 007 wsgi:app
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
    **Note**: This example uses a Unix socket (`unix:/tmp/tasktracker.sock`) for Gunicorn, which is more efficient when proxied by Nginx on the same machine. If you use a socket, update your Nginx config:
    ```nginx
    # In Nginx config:
    upstream tasktracker_app {
        server unix:/tmp/tasktracker.sock fail_timeout=0;
    }

    server {
        # ...
        location / {
            proxy_pass http://tasktracker_app;
            # ... other proxy headers
        }
    }
    ```

2.  **Enable and start the Systemd service**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start tasktracker
    sudo systemctl enable tasktracker # Start on boot
    sudo systemctl status tasktracker # Check status
    ```

## 4. Troubleshooting

*   **`ModuleNotFoundError` or `ImportError`**:
    *   Ensure your virtual environment is active (`(venv)` in your prompt).
    *   Run `pip install -r requirements.txt` again to ensure all dependencies are installed.
    *   Check `FLASK_APP` in your `.env` file points to the correct entry file (e.g., `app.py` or `wsgi.py`).

*   **Database Connection Errors**:
    *   **SQLite**: Check if `instance/app.db` exists and has write permissions for the user running the Flask app. Verify `DATABASE_URL` in `.env`.
    *   **PostgreSQL**:
        *   Verify PostgreSQL server is running.
        *   Check `DATABASE_URL` in `.env` for correct username, password, host, port, and database name.
        *   Ensure the `psycopg2-binary` package is installed (`pip install psycopg2-binary`).
        *   Check firewall rules if the database is on a different host.

*   **`flask run` or Gunicorn not starting**:
    *   Check the console output for error messages.
    *   Ensure `SECRET_KEY` is set in your `.env`.
    *   If using Gunicorn with a socket, ensure the socket file (`/tmp/tasktracker.sock`) has correct permissions or is being created.

*   **Nginx 502 Bad Gateway**:
    *   This usually means Nginx couldn't connect to Gunicorn.
    *   Check if Gunicorn is running and listening on the correct address/port (or socket).
    *   Check Nginx error logs (`/var/log/nginx/error.log`).
    *   Ensure firewall rules allow Nginx to connect to Gunicorn.

*   **Permissions Issues**:
    *   Ensure the user running the Flask/Gunicorn application has read/write permissions to the project directory, especially `instance/` for SQLite, and any static/media file directories.
    *   For production, ensure the user running Gunicorn (e.g., `www-data`) has necessary permissions.