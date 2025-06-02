from marshmallow import Schema, fields, validate

class TaskRequestSchema(Schema):
    """
    Base schema for fields that can be sent in task creation or update requests.
    It defines common validation rules for title, description, and due_date.
    """
    title = fields.Str(
        validate=validate.Length(min=1, max=100),
        metadata={"description": "Title of the task. Must be between 1 and 100 characters."}
    )
    description = fields.Str(
        allow_none=True,  # Allows null values for description
        validate=validate.Length(max=500),
        metadata={"description": "Detailed description of the task. Max 500 characters. Can be null."}
    )
    due_date = fields.DateTime(
        format='iso',  # Expects and outputs ISO 8601 formatted datetime strings (e.g., "2023-10-27T10:00:00")
        allow_none=True,  # Allows null values for due_date
        metadata={"description": "Optional due date for the task (ISO 8601 format). Can be null."}
    )

class TaskCreateSchema(TaskRequestSchema):
    """
    Schema for validating new task creation requests.
    Inherits common fields from TaskRequestSchema and makes 'title' required.
    The 'completed' status is not part of the creation request; it defaults to False in the model/database.
    """
    title = fields.Str(
        required=True,  # Title is mandatory when creating a new task
        validate=validate.Length(min=1, max=100),
        metadata={"description": "Title of the task (required for creation). Must be between 1 and 100 characters."}
    )

class TaskUpdateSchema(TaskRequestSchema):
    """
    Schema for validating task update requests.
    All fields inherited from TaskRequestSchema (title, description, due_date) are optional,
    allowing for partial updates.
    Includes 'completed' field for marking tasks as complete or incomplete.
    """
    completed = fields.Bool(
        required=False,  # 'completed' field is optional for updates
        metadata={"description": "New status of the task (True if completed, False otherwise)."}
    )

class TaskSchema(TaskRequestSchema):
    """
    Full schema for serializing Task objects for API responses.
    Includes all task attributes, including read-only system-generated fields like ID and timestamps.
    This schema is used for dumping (serializing) data from the database to JSON.
    """
    id = fields.Int(
        dump_only=True,  # This field is only for output, not for input
        metadata={"description": "Unique identifier of the task."}
    )
    # Override title to make it required for output, as it will always be present
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
        metadata={"description": "Title of the task."}
    )
    # description and due_date are inherited from TaskRequestSchema as-is
    completed = fields.Bool(
        required=True,  # 'completed' status is always present in the output
        metadata={"description": "Status of the task (True if completed, False otherwise)."}
    )
    user_id = fields.Int(
        dump_only=True,  # This field is only for output, linking to the owning user
        metadata={"description": "ID of the user who owns this task."}
    )
    created_at = fields.DateTime(
        dump_only=True,
        format='iso',
        metadata={"description": "Timestamp when the task was created (ISO 8601 format)."}
    )
    updated_at = fields.DateTime(
        dump_only=True,
        format='iso',
        metadata={"description": "Timestamp when the task was last updated (ISO 8601 format)."}
    )