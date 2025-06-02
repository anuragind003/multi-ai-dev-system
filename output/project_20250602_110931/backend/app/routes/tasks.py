from flask import Blueprint, request, jsonify, g, abort
from app.database import get_db_connection
from app.utils.auth import login_required
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

def dict_from_row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """
    Helper function to convert a sqlite3.Row object to a dictionary.
    This makes the JSON output more readable and consistent.
    """
    if row is None:
        return None
    return dict(row)

def _validate_iso_date(date_str: Optional[str]) -> Optional[str]:
    """
    Validates if a string is a valid ISO 8601 date/time format.
    Returns the cleaned string or raises ValueError.
    """
    if date_str is None:
        return None
    try:
        # .replace('Z', '+00:00') handles 'Z' for UTC timezone in ISO 8601
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_str # Return original string if valid
    except ValueError:
        raise ValueError("Invalid due_date format. Use ISO 8601 (e.g., 'YYYY-MM-DDTHH:MM:SSZ').")

def _get_task_by_id_and_user(conn: sqlite3.Connection, task_id: int, user_id: int) -> Optional[sqlite3.Row]:
    """
    Helper function to fetch a single task by its ID and user_id.
    Sets row_factory for the connection.
    """
    conn.row_factory = sqlite3.Row
    task = conn.execute(
        'SELECT id, title, description, due_date, completed, user_id, created_at FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, user_id)
    ).fetchone()
    return task

@tasks_bp.route('/', methods=['GET'])
@login_required
def get_tasks():
    """
    Retrieves all tasks for the authenticated user.
    Requires authentication via the login_required decorator, which sets g.user_id.
    ---
    GET /tasks
    Responses:
      200:
        description: A list of tasks belonging to the authenticated user.
        schema:
          type: array
          items:
            type: object
            properties:
              id: {type: integer, description: "Unique ID of the task"}
              title: {type: string, description: "Title of the task"}
              description: {type: string, nullable: true, description: "Optional description of the task"}
              due_date: {type: string, format: date-time, nullable: true, description: "Optional due date in ISO 8601 format"}
              completed: {type: boolean, description: "True if the task is completed, False otherwise"}
              user_id: {type: integer, description: "ID of the user who owns the task"}
              created_at: {type: string, format: date-time, description: "Timestamp when the task was created"}
      401:
        description: Unauthorized if no valid authentication token is provided.
      500:
        description: Internal server error due to database issues.
    """
    user_id: int = g.user_id
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        tasks = conn.execute(
            'SELECT id, title, description, due_date, completed, user_id, created_at FROM tasks WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        ).fetchall()
        return jsonify([dict_from_row(task) for task in tasks]), 200
    except sqlite3.Error as e:
        # In a real application, use a proper logging framework (e.g., `logging.error(f"...")`)
        print(f"Database error in get_tasks: {e}")
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@tasks_bp.route('/', methods=['POST'])
@login_required
def create_task():
    """
    Creates a new task for the authenticated user.
    Requires authentication.
    ---
    POST /tasks
    Request Body:
      application/json:
        schema:
          type: object
          required: [title]
          properties:
            title: {type: string, description: "Title of the task"}
            description: {type: string, nullable: true, description: "Optional description of the task"}
            due_date: {type: string, format: date-time, nullable: true, description: "Optional due date (ISO 8601 format)"}
    Responses:
      201:
        description: Task created successfully. Returns the newly created task object.
        schema:
          type: object
          properties:
            id: {type: integer}
            title: {type: string}
            description: {type: string, nullable: true}
            due_date: {type: string, format: date-time, nullable: true}
            completed: {type: boolean}
            user_id: {type: integer}
            created_at: {type: string, format: date-time}
      400:
        description: Bad request if required fields are missing or invalid data is provided.
      401:
        description: Unauthorized if no valid authentication token is provided.
      500:
        description: Internal server error due to database issues.
    """
    user_id: int = g.user_id
    data: Optional[Dict[str, Any]] = request.get_json()

    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400
    if not data.get('title'):
        return jsonify({"message": "Title is required"}), 400

    title: str = data['title']
    description: Optional[str] = data.get('description')
    due_date: Optional[str] = data.get('due_date')

    if due_date:
        try:
            due_date = _validate_iso_date(due_date)
        except ValueError as e:
            return jsonify({"message": str(e)}), 400

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO tasks (title, description, due_date, user_id) VALUES (?, ?, ?, ?)',
            (title, description, due_date, user_id)
        )
        conn.commit()
        new_task_id: int = cursor.lastrowid

        new_task = _get_task_by_id_and_user(conn, new_task_id, user_id)
        
        if new_task is None:
            print(f"Warning: Newly created task with ID {new_task_id} not found for user {user_id}.")
            return jsonify({"message": "Failed to retrieve newly created task."}), 500

        return jsonify(dict_from_row(new_task)), 201
    except sqlite3.Error as e:
        print(f"Database error in create_task: {e}")
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@tasks_bp.route('/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id: int):
    """
    Retrieves a specific task by its ID for the authenticated user.
    Ensures that a user can only retrieve their own tasks.
    ---
    GET /tasks/{task_id}
    Parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: The ID of the task to retrieve.
    Responses:
      200:
        description: The requested task.
        schema:
          type: object
          properties:
            id: {type: integer}
            title: {type: string}
            description: {type: string, nullable: true}
            due_date: {type: string, format: date-time, nullable: true}
            completed: {type: boolean}
            user_id: {type: integer}
            created_at: {type: string, format: date-time}
      401:
        description: Unauthorized if no valid authentication token is provided.
      404:
        description: Task not found or does not belong to the authenticated user.
      500:
        description: Internal server error due to database issues.
    """
    user_id: int = g.user_id
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        task = _get_task_by_id_and_user(conn, task_id, user_id)

        if task is None:
            return jsonify({"message": "Task not found"}), 404
        
        return jsonify(dict_from_row(task)), 200
    except sqlite3.Error as e:
        print(f"Database error in get_task: {e}")
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id: int):
    """
    Updates an existing task for the authenticated user.
    Allows partial updates (e.g., only title, or only completed status).
    Requires authentication.
    ---
    PUT /tasks/{task_id}
    Parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: The ID of the task to update.
    Request Body:
      application/json:
        schema:
          type: object
          properties:
            title: {type: string, description: "New title of the task"}
            description: {type: string, nullable: true, description: "New description of the task"}
            due_date: {type: string, format: date-time, nullable: true, description: "New due date (ISO 8601 format)"}
            completed: {type: boolean, description: "Whether the task is completed (true/false)"}
    Responses:
      200:
        description: Task updated successfully. Returns the updated task object.
        schema:
          type: object
          properties:
            id: {type: integer}
            title: {type: string}
            description: {type: string, nullable: true}
            due_date: {type: string, format: date-time, nullable: true}
            completed: {type: boolean}
            user_id: {type: integer}
            created_at: {type: string, format: date-time}
      400:
        description: Bad request if input data is invalid (e.g., empty title, invalid date format).
      401:
        description: Unauthorized if no valid authentication token is provided.
      404:
        description: Task not found or does not belong to the authenticated user.
      500:
        description: Internal server error due to database issues.
    """
    user_id: int = g.user_id
    data: Optional[Dict[str, Any]] = request.get_json()

    if not data:
        return jsonify({"message": "No input data provided"}), 400

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        
        task_exists = _get_task_by_id_and_user(conn, task_id, user_id)
        if task_exists is None:
            return jsonify({"message": "Task not found"}), 404

        update_fields: List[str] = []
        update_values: List[Any] = []

        if 'title' in data:
            title_val = data['title']
            if not isinstance(title_val, str) or not title_val.strip():
                return jsonify({"message": "Title cannot be empty and must be a string"}), 400
            update_fields.append('title = ?')
            update_values.append(title_val.strip())
        
        if 'description' in data:
            update_fields.append('description = ?')
            update_values.append(data['description'])
        
        if 'due_date' in data:
            due_date_val = data['due_date']
            try:
                due_date_val = _validate_iso_date(due_date_val)
            except ValueError as e:
                return jsonify({"message": str(e)}), 400
            update_fields.append('due_date = ?')
            update_values.append(due_date_val)
        
        if 'completed' in data:
            completed_val = data['completed']
            if not isinstance(completed_val, bool):
                return jsonify({"message": "Completed field must be a boolean (true/false)"}), 400
            update_fields.append('completed = ?')
            update_values.append(1 if completed_val else 0)

        if not update_fields:
            return jsonify({"message": "No valid fields to update provided"}), 400

        query: str = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
        update_values.extend([task_id, user_id])

        cursor = conn.cursor()
        cursor.execute(query, tuple(update_values))
        conn.commit()

        updated_task = _get_task_by_id_and_user(conn, task_id, user_id)
        
        if updated_task is None:
            print(f"Warning: Updated task with ID {task_id} not found for user {user_id} after update.")
            return jsonify({"message": "Failed to retrieve updated task."}), 500

        return jsonify(dict_from_row(updated_task)), 200
    except sqlite3.Error as e:
        print(f"Database error in update_task: {e}")
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id: int):
    """
    Deletes a specific task by its ID for the authenticated user.
    Ensures that a user can only delete their own tasks.
    ---
    DELETE /tasks/{task_id}
    Parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: The ID of the task to delete.
    Responses:
      204:
        description: Task deleted successfully (No Content).
      401:
        description: Unauthorized if no valid authentication token is provided.
      404:
        description: Task not found or does not belong to the authenticated user.
      500:
        description: Internal server error due to database issues.
    """
    user_id: int = g.user_id
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        task_exists = _get_task_by_id_and_user(conn, task_id, user_id)
        if task_exists is None:
            return jsonify({"message": "Task not found"}), 404

        cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
        conn.commit()

        if cursor.rowcount == 0:
            print(f"Warning: Task {task_id} for user {user_id} was found but not deleted (rowcount 0).")
            return jsonify({"message": "Task not found or not authorized to delete"}), 404
        
        return '', 204
    except sqlite3.Error as e:
        print(f"Database error in delete_task: {e}")
        return jsonify({"message": "Internal server error", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()