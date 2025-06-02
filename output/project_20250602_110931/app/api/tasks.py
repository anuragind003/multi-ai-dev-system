from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.extensions import db
from app.models import Task

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

def task_to_dict(task):
    """
    Converts a Task model instance into a dictionary suitable for JSON serialization.
    Handles datetime objects by converting them to ISO format strings.
    """
    return {
        'id': task.id,
        'user_id': task.user_id,
        'title': task.title,
        'description': task.description,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'completed': task.completed,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat()
    }

def parse_due_date(due_date_str):
    """
    Helper function to parse a due_date string into a datetime object.
    Returns datetime object or None if string is empty/None.
    Raises ValueError if format is invalid.
    """
    if not due_date_str:
        return None
    try:
        # datetime.fromisoformat handles various ISO 8601 formats.
        return datetime.fromisoformat(due_date_str)
    except ValueError:
        raise ValueError("Invalid due_date format. Use ISO 8601 (e.g., YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).")

@tasks_bp.route('/', methods=['POST'])
@login_required
def create_task():
    """
    API endpoint to create a new task for the authenticated user.
    Requires 'title' in the request body. 'description' and 'due_date' are optional.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title')
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    description = data.get('description')
    due_date = None
    if 'due_date' in data:
        try:
            due_date = parse_due_date(data['due_date'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    try:
        new_task = Task(
            user_id=current_user.id,
            title=title,
            description=description,
            due_date=due_date
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify(task_to_dict(new_task)), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating task for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not create task', 'details': 'An unexpected error occurred.'}), 500

@tasks_bp.route('/', methods=['GET'])
@login_required
def get_tasks():
    """
    API endpoint to retrieve all tasks for the authenticated user.
    Supports optional query parameters for filtering (e.g., 'completed').
    """
    try:
        tasks_query = Task.query.filter_by(user_id=current_user.id)

        completed_param = request.args.get('completed')
        if completed_param is not None:
            if completed_param.lower() == 'true':
                tasks_query = tasks_query.filter_by(completed=True)
            elif completed_param.lower() == 'false':
                tasks_query = tasks_query.filter_by(completed=False)
            else:
                return jsonify({'error': 'Invalid value for "completed" parameter. Use "true" or "false".'}), 400

        tasks = tasks_query.order_by(Task.created_at.desc()).all()

        return jsonify([task_to_dict(task) for task in tasks]), 200
    except Exception as e:
        current_app.logger.error(f"Error retrieving tasks for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not retrieve tasks', 'details': 'An unexpected error occurred.'}), 500

@tasks_bp.route('/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    """
    API endpoint to retrieve a single task by its ID for the authenticated user.
    """
    try:
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()

        if not task:
            return jsonify({'error': 'Task not found or not authorized'}), 404

        return jsonify(task_to_dict(task)), 200
    except Exception as e:
        current_app.logger.error(f"Error retrieving task {task_id} for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not retrieve task', 'details': 'An unexpected error occurred.'}), 500

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """
    API endpoint to update an existing task for the authenticated user.
    Allows updating 'title', 'description', 'due_date', and 'completed' status.
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()

    if not task:
        return jsonify({'error': 'Task not found or not authorized'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided for update'}), 400

    try:
        if 'title' in data:
            if not data['title']:
                return jsonify({'error': 'Title cannot be empty'}), 400
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'due_date' in data:
            try:
                task.due_date = parse_due_date(data['due_date'])
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
        if 'completed' in data:
            if not isinstance(data['completed'], bool):
                return jsonify({'error': 'Completed status must be a boolean (true/false)'}), 400
            task.completed = data['completed']

        task.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify(task_to_dict(task)), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating task {task_id} for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not update task', 'details': 'An unexpected error occurred.'}), 500

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """
    API endpoint to delete a task by its ID for the authenticated user.
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()

    if not task:
        return jsonify({'error': 'Task not found or not authorized'}), 404

    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({'message': 'Task deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting task {task_id} for user {current_user.id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not delete task', 'details': 'An unexpected error occurred.'}), 500