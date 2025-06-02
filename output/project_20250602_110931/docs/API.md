# Simple Task Tracker API Documentation

This document provides a detailed overview of the RESTful API endpoints for the Simple Task Tracker application.

## Base URL

All API endpoints are prefixed with `/api`.
Example: `http://localhost:5000/api/register` (for local development)

## Authentication

Authentication is handled via JSON Web Tokens (JWT).
-   Upon successful login, an access token is returned.
-   This token must be included in the `Authorization` header of subsequent requests for protected endpoints.
-   Format: `Authorization: Bearer <access_token>`

## Error Handling

The API returns standard HTTP status codes to indicate the success or failure of a request.
In case of an error, a JSON object containing an `error` message will be returned.

**Common Error Responses:**

*   **400 Bad Request:** The request was malformed or missing required parameters.
    ```json
    {
        "error": "Missing required field: email"
    }
    ```
*   **401 Unauthorized:** Authentication is required but was not provided, or the token is invalid/expired.
    ```json
    {
        "error": "Missing Authorization Header"
    }
    ```
    ```json
    {
        "error": "Token is invalid or expired"
    }
    ```
*   **403 Forbidden:** The authenticated user does not have permission to access the requested resource.
    ```json
    {
        "error": "You do not have permission to access this task."
    }
    ```
*   **404 Not Found:** The requested resource does not exist.
    ```json
    {
        "error": "Task not found"
    }
    ```
*   **409 Conflict:** The request could not be completed due to a conflict with the current state of the resource (e.g., user already exists).
    ```json
    {
        "error": "User with this email already exists"
    }
    ```
*   **500 Internal Server Error:** An unexpected error occurred on the server.
    ```json
    {
        "error": "An unexpected error occurred."
    }
    ```

---

## User Endpoints

### 1. Register a New User

*   **Endpoint:** `POST /api/register`
*   **Description:** Creates a new user account.
*   **Authentication:** None
*   **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }
    ```
*   **Response (Success - 201 Created):**
    ```json
    {
        "message": "User registered successfully",
        "user_id": 1
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Missing required field: email"
    }
    ```
*   **Response (Error - 409 Conflict):**
    ```json
    {
        "error": "User with this email already exists"
    }
    ```
*   **Example Request:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{"email": "testuser@example.com", "password": "password123"}' \
         http://localhost:5000/api/register
    ```

### 2. Log In User

*   **Endpoint:** `POST /api/login`
*   **Description:** Authenticates a user and returns an access token.
*   **Authentication:** None
*   **Request Body:**
    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "message": "Login successful",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Missing required field: email"
    }
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Invalid email or password"
    }
    ```
*   **Example Request:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -d '{"email": "testuser@example.com", "password": "password123"}' \
         http://localhost:5000/api/login
    ```

### 3. Log Out User

*   **Endpoint:** `POST /api/logout`
*   **Description:** Invalidates the current user's session/token. For JWTs, this typically means the client should discard the token, or the server might blacklist it.
*   **Authentication:** Required (JWT)
*   **Request Body:** None
*   **Response (Success - 200 OK):**
    ```json
    {
        "message": "Successfully logged out"
    }
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Missing Authorization Header"
    }
    ```
*   **Example Request:**
    ```bash
    curl -X POST -H "Authorization: Bearer <your_access_token>" \
         http://localhost:5000/api/logout
    ```

---

## Task Endpoints

### 1. Create a New Task

*   **Endpoint:** `POST /api/tasks`
*   **Description:** Creates a new task for the authenticated user.
*   **Authentication:** Required (JWT)
*   **Request Body:**
    ```json
    {
        "title": "Buy groceries",
        "description": "Milk, eggs, bread, and cheese.",
        "due_date": "2023-12-31T17:00:00Z"
    }
    ```
    *   `title` (string, required): The title of the task.
    *   `description` (string, optional): A detailed description of the task.
    *   `due_date` (string, optional): The due date and time of the task in ISO 8601 format (e.g., `YYYY-MM-DDTHH:MM:SSZ`).
*   **Response (Success - 201 Created):**
    ```json
    {
        "id": 101,
        "title": "Buy groceries",
        "description": "Milk, eggs, bread, and cheese.",
        "due_date": "2023-12-31T17:00:00Z",
        "completed": false,
        "created_at": "2023-12-25T10:00:00Z",
        "updated_at": "2023-12-25T10:00:00Z",
        "user_id": 1
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Missing required field: title"
    }
    ```
    ```json
    {
        "error": "Invalid due_date format. Use ISO 8601."
    }
    ```
*   **Example Request:**
    ```bash
    curl -X POST -H "Content-Type: application/json" \
         -H "Authorization: Bearer <your_access_token>" \
         -d '{"title": "Plan holiday trip", "description": "Research destinations and book flights.", "due_date": "2024-01-15T23:59:59Z"}' \
         http://localhost:5000/api/tasks
    ```

### 2. Get All Tasks

*   **Endpoint:** `GET /api/tasks`
*   **Description:** Retrieves all tasks belonging to the authenticated user.
*   **Authentication:** Required (JWT)
*   **Query Parameters (Optional):**
    *   `completed` (boolean): Filter tasks by completion status (`true` or `false`).
    *   `sort_by` (string): Field to sort by (e.g., `due_date`, `created_at`, `title`).
    *   `order` (string): Sort order (`asc` or `desc`). Default is `asc`.
*   **Response (Success - 200 OK):**
    ```json
    [
        {
            "id": 101,
            "title": "Buy groceries",
            "description": "Milk, eggs, bread, and cheese.",
            "due_date": "2023-12-31T17:00:00Z",
            "completed": false,
            "created_at": "2023-12-25T10:00:00Z",
            "updated_at": "2023-12-25T10:00:00Z",
            "user_id": 1
        },
        {
            "id": 102,
            "title": "Finish API docs",
            "description": "Complete the API.md file.",
            "due_date": null,
            "completed": true,
            "created_at": "2023-12-20T09:00:00Z",
            "updated_at": "2023-12-22T14:30:00Z",
            "user_id": 1
        }
    ]
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Missing Authorization Header"
    }
    ```
*   **Example Request (All tasks):**
    ```bash
    curl -X GET -H "Authorization: Bearer <your_access_token>" \
         http://localhost:5000/api/tasks
    ```
*   **Example Request (Completed tasks, sorted by due date descending):**
    ```bash
    curl -X GET -H "Authorization: Bearer <your_access_token>" \
         "http://localhost:5000/api/tasks?completed=true&sort_by=due_date&order=desc"
    ```

### 3. Get a Single Task

*   **Endpoint:** `GET /api/tasks/<int:task_id>`
*   **Description:** Retrieves a specific task by its ID, belonging to the authenticated user.
*   **Authentication:** Required (JWT)
*   **Path Parameters:**
    *   `task_id` (integer, required): The unique identifier of the task.
*   **Response (Success - 200 OK):**
    ```json
    {
        "id": 101,
        "title": "Buy groceries",
        "description": "Milk, eggs, bread, and cheese.",
        "due_date": "2023-12-31T17:00:00Z",
        "completed": false,
        "created_at": "2023-12-25T10:00:00Z",
        "updated_at": "2023-12-25T10:00:00Z",
        "user_id": 1
    }
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Missing Authorization Header"
    }
    ```
*   **Response (Error - 403 Forbidden):**
    ```json
    {
        "error": "You do not have permission to access this task."
    }
    ```
*   **Response (Error - 404 Not Found):**
    ```json
    {
        "error": "Task not found"
    }
    ```
*   **Example Request:**
    ```bash
    curl -X GET -H "Authorization: Bearer <your_access_token>" \
         http://localhost:5000/api/tasks/101
    ```

### 4. Update an Existing Task

*   **Endpoint:** `PUT /api/tasks/<int:task_id>`
*   **Description:** Updates an existing task for the authenticated user.
*   **Authentication:** Required (JWT)
*   **Path Parameters:**
    *   `task_id` (integer, required): The unique identifier of the task.
*   **Request Body (Partial Update - all fields optional):**
    ```json
    {
        "title": "Buy organic groceries",
        "description": "Organic milk, eggs, bread, and cheese.",
        "due_date": "2024-01-05T10:00:00Z",
        "completed": true
    }
    ```
    *   `title` (string, optional): New title for the task.
    *   `description` (string, optional): New description for the task.
    *   `due_date` (string, optional): New due date and time in ISO 8601 format. Can be `null` to clear.
    *   `completed` (boolean, optional): Set to `true` to mark as complete, `false` otherwise.
*   **Response (Success - 200 OK):**
    ```json
    {
        "id": 101,
        "title": "Buy organic groceries",
        "description": "Organic milk, eggs, bread, and cheese.",
        "due_date": "2024-01-05T10:00:00Z",
        "completed": true,
        "created_at": "2023-12-25T10:00:00Z",
        "updated_at": "2023-12-25T10:30:00Z",
        "user_id": 1
    }
    ```
*   **Response (Error - 400 Bad Request):**
    ```json
    {
        "error": "Invalid due_date format. Use ISO 8601."
    }
    ```
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Missing Authorization Header"
    }
    ```
*   **Response (Error - 403 Forbidden):**
    ```json
    {
        "error": "You do not have permission to update this task."
    }
    ```
*   **Response (Error - 404 Not Found):**
    ```json
    {
        "error": "Task not found"
    }
    ```
*   **Example Request (Mark as complete):**
    ```bash
    curl -X PUT -H "Content-Type: application/json" \
         -H "Authorization: Bearer <your_access_token>" \
         -d '{"completed": true}' \
         http://localhost:5000/api/tasks/101
    ```
*   **Example Request (Update title and description):**
    ```bash
    curl -X PUT -H "Content-Type: application/json" \
         -H "Authorization: Bearer <your_access_token>" \
         -d '{"title": "Buy organic groceries", "description": "Organic milk, eggs, bread, and cheese."}' \
         http://localhost:5000/api/tasks/101
    ```

### 5. Delete a Task

*   **Endpoint:** `DELETE /api/tasks/<int:task_id>`
*   **Description:** Deletes a specific task belonging to the authenticated user.
*   **Authentication:** Required (JWT)
*   **Path Parameters:**
    *   `task_id` (integer, required): The unique identifier of the task.
*   **Request Body:** None
*   **Response (Success - 204 No Content):**
    *   No content is returned for a successful deletion.
*   **Response (Error - 401 Unauthorized):**
    ```json
    {
        "error": "Missing Authorization Header"
    }
    ```
*   **Response (Error - 403 Forbidden):**
    ```json
    {
        "error": "You do not have permission to delete this task."
    }
    ```
*   **Response (Error - 404 Not Found):**
    ```json
    {
        "error": "Task not found"
    }
    ```
*   **Example Request:**
    ```bash
    curl -X DELETE -H "Authorization: Bearer <your_access_token>" \
         http://localhost:5000/api/tasks/101
    ```