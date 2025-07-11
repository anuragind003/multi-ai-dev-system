python
### FILE: README.md
# Task List API

## Overview

This is a REST API for managing a task list. It allows you to create, read, update, and delete tasks.

## Features

- Create tasks
- Retrieve all tasks
- Retrieve a task by ID
- Update tasks
- Delete tasks
- Authentication using API keys
- Input validation
- Error handling
- Basic documentation using OpenAPI

## Prerequisites

- Python 3.9+
- Docker (optional, for containerization)

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

4.  **Set up environment variables:**

    -   Create a `.env` file in the project root and add your API key:

        ```
        API_KEY=your_api_key_here
        DATABASE_URL=sqlite:///./test.db  # Or your preferred database URL
        ```

## Running the API

1.  **Using Uvicorn (for development):**

    ```bash
    uvicorn main:app --reload
    ```

    This will start the API server on `http://127.0.0.1:8000`.

2.  **Using Docker (for production or consistent environments):**

    -   Build the Docker image:

        ```bash
        docker build -t task-list-api .
        ```

    -   Run the Docker container:

        ```bash
        docker run -d -p 8000:8000 -e API_KEY=your_api_key_here task-list-api
        ```

        Replace `your_api_key_here` with your actual API key.

## API Documentation

The API documentation is available at:

-   `http://127.0.0.1:8000/docs` (for interactive documentation)
-   `http://127.0.0.1:8000/redoc` (for a more concise documentation)

## API Endpoints

### `/`

-   **Method:** `GET`
-   **Description:** Root endpoint. Returns a welcome message.

### `/tasks`

-   **Method:** `GET`
    -   **Description:** Retrieve all tasks.
    -   **Authentication:** Requires `X-API-Key` header.
-   **Method:** `POST`
    -   **Description:** Create a new task.
    -   **Request Body:**
        ```json
        {
          "title": "string",
          "description": "string (optional)",
          "due_date": "YYYY-MM-DD (optional)"
        }
        ```
    -   **Authentication:** Requires `X-API-Key` header.
    -   **Status Codes:**
        -   `201 Created`: Task created successfully.
        -   `400 Bad Request`: Invalid input data.
        -   `500 Internal Server Error`: Failed to create task.
-   **Method:** `GET`
    -   **Description:** Retrieve a task by ID.
    -   **Parameters:**
        -   `task_id`: The ID of the task to retrieve.
    -   **Authentication:** Requires `X-API-Key` header.
    -   **Status Codes:**
        -   `200 OK`: Task retrieved successfully.
        -   `404 Not Found`: Task not found.
        -   `500 Internal Server Error`: Failed to retrieve task.
-   **Method:** `PUT`
    -   **Description:** Update a task by ID.
    -   **Parameters:**
        -   `task_id`: The ID of the task to update.
    -   **Request Body:**
        ```json
        {
          "title": "string (optional)",
          "description": "string (optional)",
          "due_date": "YYYY-MM-DD (optional)",
          "completed": "boolean (optional)"
        }
        ```
    -   **Authentication:** Requires `X-API-Key` header.
    -   **Status Codes:**
        -   `200 OK`: Task updated successfully.
        -   `400 Bad Request`: Invalid input data.
        -   `404 Not Found`: Task not found.
        -   `500 Internal Server Error`: Failed to update task.
-   **Method:** `DELETE`
    -   **Description:** Delete a task by ID.
    -   **Parameters:**
        -   `task_id`: The ID of the task to delete.
    -   **Authentication:** Requires `X-API-Key` header.
    -   **Status Codes:**
        -   `204 No Content`: Task deleted successfully.
        -   `404 Not Found`: Task not found.
        -   `500 Internal Server Error`: Failed to delete task.

## Testing

1.  **Install pytest and pytest-asyncio:**

    ```bash
    pip install pytest pytest-asyncio
    ```

2.  **Run tests:**

    ```bash
    pytest
    ```

## Technologies Used

-   Python
-   FastAPI
-   SQLAlchemy
-   SQLite (for the example database)
-   Uvicorn (ASGI server)
-   Docker (optional)

## License

[MIT License](LICENSE)