# Simple Task Tracker

A web-based application designed to help users manage their daily tasks. It allows users to create, view, update, and mark tasks as complete.

## Table of Contents

-   [Features](#features)
-   [Technology Stack](#technology-stack)
-   [Getting Started](#getting-started)
    -   [Prerequisites](#prerequisites)
    -   [Installation](#installation)
    -   [Database Setup](#database-setup)
-   [Running the Application](#running-the-application)
-   [Project Structure](#project-structure)
-   [Security Considerations](#security-considerations)
-   [Performance & Scalability](#performance--scalability)
-   [Contributing](#contributing)
-   [License](#license)

## Features

The Simple Task Tracker provides the following core functionalities:

-   **User Authentication:**
    -   Create a new account using an email address and password.
    -   Log in with registered credentials.
    -   Securely stored user passwords (hashed).
    -   Log out of the account.
-   **Task Management:**
    -   Authenticated users can create new tasks with a title/description and an optional due date.
    -   View a list of all their tasks.
    -   Update existing task details.
    -   Mark tasks as complete.

## Technology Stack

-   **Backend:** Python 3.x, Flask
-   **Database:**
    -   **Development/Small-scale Production:** SQLite
    -   **Future Scalability:** PostgreSQL
-   **Architecture:** Monolithic (Client-Server / MVC-like)

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Ensure you have the following installed:

-   [Python 3.8+](https://www.python.org/downloads/)
-   [pip](https://pip.pypa.io/en/stable/installation/) (Python package installer, usually comes with Python)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/simple-task-tracker.git
    cd simple-task-tracker
    ```

2.  **Create and activate a virtual environment:**

    It's highly recommended to use a virtual environment to manage project dependencies.

    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    Install all required Python packages using pip. You will need a `requirements.txt` file in your project root.

    ```bash
    pip install -r requirements.txt
    ```

    A typical `requirements.txt` for this project might look like:
    ```
    Flask==2.3.3
    Flask-SQLAlchemy==3.1.1
    Flask-Login==0.6.3
    Werkzeug==2.3.7
    python-dotenv==1.0.0 # For managing environment variables
    ```

### Database Setup

The application uses SQLite for development by default. The database file (`instance/tasks.sqlite`) will be automatically created when the application runs for the first time if it doesn't exist.

**For SQLite (Development):**
No manual setup is typically required. The application will create the `instance/` directory and `tasks.sqlite` file upon first run.

**For PostgreSQL (Production/Scalability):**
If you plan to use PostgreSQL, you'll need to:
1.  Install PostgreSQL on your system or have access to a PostgreSQL server.
2.  Create a database for the application (e.g., `task_tracker_db`).
3.  Set the `DATABASE_URL` environment variable to your PostgreSQL connection string.
    Example: `export DATABASE_URL="postgresql://user:password@host:port/task_tracker_db"`
    (You might use a `.env` file and `python-dotenv` for this.)

## Running the Application

1.  **Ensure your virtual environment is active.**

2.  **Set Flask environment variables:**

    These variables tell Flask where to find your application and how to run it.

    ```bash
    # On macOS/Linux
    export FLASK_APP=app
    export FLASK_ENV=development # Set to 'production' for production deployment
    
    # On Windows (Command Prompt)
    set FLASK_APP=app
    set FLASK_ENV=development
    
    # On Windows (PowerShell)
    $env:FLASK_APP="app"
    $env:FLASK_ENV="development"
    ```

    *(Note: `app` refers to the main Flask application instance, typically defined in `app/__init__.py`.)*

3.  **Run the Flask application:**

    ```bash
    flask run
    ```

    The application will typically be accessible at `http://127.0.0.1:5000/`.

## Project Structure

```
.
├── app/
│   ├── __init__.py         # Application factory, configuration, database setup
│   ├── models.py           # Database models (User, Task)
│   ├── auth/               # Authentication blueprint (login, register, logout)
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── tasks/              # Task management blueprint (create, view, update, delete)
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── static/             # CSS, JS, images for the frontend
│   └── templates/          # HTML templates for rendering pages
├── instance/               # Instance-specific configuration and database (e.g., tasks.sqlite)
├── config.py               # Application configuration settings (e.g., SECRET_KEY, DB_URI)
├── requirements.txt        # Python dependencies list
├── .env                    # Environment variables (for local development, not committed to Git)
└── README.md               # This documentation file
```

## Security Considerations

-   **Password Hashing:** User passwords are never stored in plain text. They are securely hashed using `Werkzeug`'s `generate_password_hash` function and verified with `check_password_hash` during login. This protects against data breaches.
-   **Session Management:** Flask's built-in session management is utilized, which relies on cryptographically signed cookies. This ensures that session data (like user login status) is tamper-proof.
-   **Input Validation:** While not explicitly detailed in this README, proper input validation on both client and server sides is crucial to prevent common web vulnerabilities such as Cross-Site Scripting (XSS) and SQL Injection.

## Performance & Scalability

-   **Performance (NFR4.2.1):** The application is designed to ensure the task list loads in under 3 seconds. This is achieved through efficient database queries, appropriate indexing on key columns (e.g., user ID for tasks), and minimal data processing on the backend before rendering.
-   **Scalability:**
    -   The choice of PostgreSQL for future scalability allows for handling larger datasets and higher concurrent user loads more efficiently than SQLite.
    -   The monolithic architecture can be scaled vertically (by deploying on a more powerful server) initially. For further horizontal scaling, the application could be containerized (e.g., using Docker) and deployed on platforms that support load balancing and multiple instances.
    -   Database indexing will be crucial for maintaining performance as the number of users and tasks grows.

## Contributing

Contributions are welcome! If you'd like to contribute to the Simple Task Tracker, please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix: `git checkout -b feature/YourFeatureName` or `git checkout -b bugfix/FixDescription`.
3.  Make your changes and ensure tests pass (if applicable).
4.  Commit your changes with a clear and concise message: `git commit -m 'Add new feature: description of feature'`.
5.  Push your branch to your forked repository: `git push origin feature/YourFeatureName`.
6.  Open a Pull Request to the `main` branch of the original repository, describing your changes.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.