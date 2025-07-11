# Task List API

This is a simple REST API for managing a task list, built with FastAPI and Python.

## Features

-   Create, read, update, and delete tasks.
-   Input validation using Pydantic.
-   Basic API key authentication.
-   CORS enabled for cross-origin requests.
-   Error handling and logging.
-   HTTPS (handled by deployment environment, e.g., using a reverse proxy like Nginx or a service like Heroku).

## Prerequisites

-   Python 3.9+
-   Docker (optional, for containerization)

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    # or
    .venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set environment variables:**

    -   Create a `.env` file in the project root:

        ```
        DATABASE_URL=sqlite:///./app.db  # Or your preferred database URL
        API_KEY=your_secure_api_key
        ALLOWED_ORIGINS=*  # Or specify allowed origins, e.g., "http://localhost:3000,https://yourdomain.com"
        ```

    -   Replace `your_secure_api_key` with a strong, unique API key.

## Running the API

1.  **Using Uvicorn (for development):**

    ```bash
    python -m uvicorn main:app --reload
    ```

    This will start the API on `http://127.0.0.1:8000`.

2.  **Using Docker (recommended for production):**

    -   Build the Docker image:

        ```bash
        docker build -t task-list-api .
        ```

    -   Run the Docker container:

        ```bash
        docker run -d -p 8000:8000 -e API_KEY=your_secure_api_key -e DATABASE_URL="sqlite:///./app.db" task-list-api
        ```

        Replace `your_secure_api_key` with your actual API key.

## API Endpoints

-   `GET /`:  Returns a welcome message.
-   `POST /tasks`: Creates a new task.
    -   Request body:
        ```json
        {
            "title": "Task title",
            "description": "Task description"
        }
        ```
    -   Requires `Authorization: Bearer <API_KEY>` header.
    -   Returns:  The created task.
-   `GET /tasks`:  Retrieves a list of tasks.
    -   Requires `Authorization: Bearer <API_KEY>` header.
    -   Query parameters: `skip` (int, default 0), `limit` (int, default 10).
    -   Returns:  A list of tasks.
-   `GET /tasks/{task_id}`:  Retrieves a specific task by ID.
    -   Requires `Authorization: Bearer <API_KEY>` header.
    -   Returns:  The task with the specified ID.
-   `PUT /tasks/{task_id}`:  Updates a task.
    -   Request body:
        ```json
        {
            "title": "Updated task title",
            "description": "Updated task description",
            "completed": true
        }
        ```
    -   Requires `Authorization: Bearer <API_KEY>` header.
    -   Returns:  The updated task.
-   `DELETE /tasks/{task_id}`:  Deletes a task.
    -   Requires `Authorization: Bearer <API_KEY>` header.
    -   Returns:  HTTP 204 No Content.

## Testing

1.  **Run tests:**

    ```bash
    pytest
    ```

    This will run the tests defined in `tests/test_main.py`.

## Security

-   **API Key Authentication:**  The API uses a simple API key for authentication.  **Important:**  In a production environment, use a more robust authentication mechanism (e.g., JWT, OAuth 2.0).
-   **CORS:**  CORS is configured to allow requests from specified origins.  Adjust the `ALLOWED_ORIGINS` environment variable accordingly.
-   **HTTPS:**  The application itself does not handle HTTPS.  It's recommended to deploy the API behind a reverse proxy (e.g., Nginx, Apache) or use a service like Heroku that handles HTTPS termination.  This is crucial for secure communication.
-   **Input Validation:**  Pydantic is used for input validation to prevent common vulnerabilities.
-   **Dependency Management:**  Keep dependencies up-to-date to mitigate security risks.

## Deployment

1.  **Choose a deployment platform:**  Consider options like:
    -   **Heroku:**  Easy to deploy, handles HTTPS automatically.
    -   **AWS (EC2, ECS, etc.):**  Scalable, but requires more configuration.
    -   **Google Cloud Platform (GCP):**  Similar to AWS.
    -   **DigitalOcean:**  A simpler alternative to AWS/GCP.

2.  **Configure the deployment environment:**
    -   Set environment variables (e.g., `DATABASE_URL`, `API_KEY`, `ALLOWED_ORIGINS`).
    -   Configure HTTPS (e.g., using a reverse proxy or platform-provided features).
    -   Set up a database (e.g., PostgreSQL, MySQL, or the platform's database service).

3.  **Deploy the application:**  Follow the platform's deployment instructions.  For example, with Heroku:

    ```bash
    heroku create
    git push heroku main
    heroku run python -m uvicorn main:app --host 0.0.0.0 --port $PORT  # or use a Procfile
    ```

## Future Improvements

-   Implement more robust authentication (e.g., JWT, OAuth 2.0).
-   Add user roles and permissions.
-   Implement pagination for large datasets.
-   Add more comprehensive error handling and logging.
-   Implement rate limiting.
-   Add database migrations.
-   Implement background tasks (e.g., using Celery).
-   Add Swagger/OpenAPI documentation.