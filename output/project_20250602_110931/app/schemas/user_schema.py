from marshmallow import Schema, fields, validate, ValidationError, validates_schema

class UserRegistrationSchema(Schema):
    """
    Schema for validating user registration requests.
    Requires email, password, and a password confirmation.
    """
    email = fields.Email(
        required=True,
        error_messages={"required": "Email is required.", "invalid": "Invalid email address."}
    )
    password = fields.String(
        required=True,
        load_only=True,  # Ensures password is not serialized back to the client
        validate=validate.Length(min=8, error="Password must be at least 8 characters long."),
        error_messages={"required": "Password is required."}
    )
    confirm_password = fields.String(
        required=True,
        load_only=True,  # Ensures password confirmation is not serialized back to the client
        error_messages={"required": "Password confirmation is required."}
    )

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        """
        Schema-level validation to ensure password and confirm_password match.
        This method is called automatically by Marshmallow after field-level validation.
        """
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError("Passwords do not match.", "confirm_password")


class UserLoginSchema(Schema):
    """
    Schema for validating user login requests.
    Requires email and password.
    """
    email = fields.Email(
        required=True,
        error_messages={"required": "Email is required.", "invalid": "Invalid email address."}
    )
    password = fields.String(
        required=True,
        load_only=True,  # Ensures password is not serialized back to the client
        error_messages={"required": "Password is required."}
    )


class UserProfileSchema(Schema):
    """
    Schema for serializing user profile data.
    Used when returning user information (e.g., after login or for a profile view).
    """
    id = fields.Integer(
        dump_only=True,  # Ensures ID is only serialized (dumped), not loaded from input
        required=True, # Ensures the ID must be present in the object being dumped
        error_messages={"required": "User ID is missing."}
    )
    email = fields.Email(
        dump_only=True,  # Ensures email is only serialized, not loaded from input
        required=True, # Ensures the email must be present in the object being dumped
        error_messages={"required": "Email is missing."}
    )
    created_at = fields.DateTime(
        dump_only=True,  # Ensures creation timestamp is only serialized
        format="%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 format for UTC
        error_messages={"invalid": "Invalid creation date format."}
    )

# Example usage (for testing/demonstration purposes, not part of the module's primary function)
if __name__ == '__main__':
    # Test UserRegistrationSchema
    print("--- Testing UserRegistrationSchema ---")
    reg_schema = UserRegistrationSchema()

    # Valid registration data
    valid_reg_data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    }
    try:
        loaded_data = reg_schema.load(valid_reg_data)
        print(f"Valid registration loaded: {loaded_data}")
    except ValidationError as err:
        print(f"Validation error for valid data (should not happen): {err.messages}")

    # Invalid registration data - passwords mismatch
    mismatch_reg_data = {
        "email": "test2@example.com",
        "password": "securepassword123",
        "confirm_password": "wrongpassword"
    }
    try:
        reg_schema.load(mismatch_reg_data)
    except ValidationError as err:
        print(f"Validation error for mismatch passwords: {err.messages}")

    # Invalid registration data - password too short
    short_pass_data = {
        "email": "test3@example.com",
        "password": "short",
        "confirm_password": "short"
    }
    try:
        reg_schema.load(short_pass_data)
    except ValidationError as err:
        print(f"Validation error for short password: {err.messages}")

    # Invalid registration data - missing email
    missing_email_data = {
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    }
    try:
        reg_schema.load(missing_email_data)
    except ValidationError as err:
        print(f"Validation error for missing email: {err.messages}")

    print("\n--- Testing UserLoginSchema ---")
    login_schema = UserLoginSchema()

    # Valid login data
    valid_login_data = {
        "email": "login@example.com",
        "password": "loginpassword"
    }
    try:
        loaded_data = login_schema.load(valid_login_data)
        print(f"Valid login loaded: {loaded_data}")
    except ValidationError as err:
        print(f"Validation error for valid login data (should not happen): {err.messages}")

    # Invalid login data - missing password
    missing_pass_login_data = {
        "email": "login2@example.com"
    }
    try:
        login_schema.load(missing_pass_login_data)
    except ValidationError as err:
        print(f"Validation error for missing login password: {err.messages}")

    print("\n--- Testing UserProfileSchema ---")
    profile_schema = UserProfileSchema()

    # Example user object (as it might come from a database)
    import datetime
    user_obj = {
        "id": 1,
        "email": "user@profile.com",
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }

    # Serialize user object to a dictionary
    try:
        serialized_data = profile_schema.dump(user_obj)
        print(f"Serialized user profile: {serialized_data}")
    except ValidationError as err:
        print(f"Serialization error (should not happen): {err.messages}")

    # Attempt to load data into profile schema (should fail for dump_only fields)
    try:
        profile_schema.load({"id": 2, "email": "new@profile.com"})
    except ValidationError as err:
        print(f"Attempt to load into profile schema (expected error for dump_only fields): {err.messages}")