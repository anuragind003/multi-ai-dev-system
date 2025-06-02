import pytest
import json
import tempfile
import os
from datetime import timedelta

from backend.app import create_app
from backend.models import db, User, TokenBlocklist
from werkzeug.security import check_password_hash
from flask_jwt_extended import decode_token

@pytest.fixture(scope='session')
def app():
    """
    Fixture to create and configure a Flask app for testing.
    Uses a temporary SQLite database for isolation.
    """
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'JWT_SECRET_KEY': 'super-secret-test-key-for-auth-tests',
        'JWT_TOKEN_LOCATION': ['headers'],
        'JWT_ACCESS_TOKEN_EXPIRES': timedelta(minutes=5),
        'JWT_REFRESH_TOKEN_EXPIRES': timedelta(hours=1),
        'JWT_BLACKLIST_ENABLED': True,
        'JWT_BLACKLIST_TOKEN_CHECKS': ['access', 'refresh']
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(scope='function')
def client(app):
    """
    Fixture to provide a test client for making HTTP requests to the app.
    Ensures a clean database state before each test function.
    """
    with app.app_context():
        db.session.query(User).delete()
        if hasattr(TokenBlocklist, '__table__'):
            db.session.query(TokenBlocklist).delete()
        db.session.commit()
        
        yield app.test_client()
        
        db.session.rollback()

def register_user(client, email, password):
    """Helper to register a user via the API."""
    return client.post(
        '/auth/register',
        data=json.dumps({'email': email, 'password': password}),
        content_type='application/json'
    )

def login_user(client, email, password):
    """Helper to log in a user via the API."""
    return client.post(
        '/auth/login',
        data=json.dumps({'email': email, 'password': password}),
        content_type='application/json'
    )

@pytest.fixture(scope='function')
def logged_in_client(client):
    """
    Fixture to provide a test client with a pre-registered and logged-in user.
    Returns a tuple: (client, access_token, refresh_token, user_email, user_password)
    """
    email = 'logged_in_user@example.com'
    password = 'securepassword'

    register_user(client, email, password)
    login_response = login_user(client, email, password)
    login_data = json.loads(login_response.data)
    access_token = login_data['access_token']
    refresh_token = login_data['refresh_token']

    yield client, access_token, refresh_token, email, password

def test_register_success(client):
    """Test successful user registration."""
    email = 'test@example.com'
    password = 'password123'
    
    response = register_user(client, email, password)
    data = json.loads(response.data)

    assert response.status_code == 201
    assert data['message'] == 'User registered successfully'
    
    with client.application.app_context():
        user = db.session.query(User).filter_by(email=email).first()
        assert user is not None
        assert check_password_hash(user.password_hash, password)

def test_register_existing_email(client):
    """Test registration with an email that already exists."""
    email = 'existing@example.com'
    password = 'password123'
    
    register_user(client, email, password)
    
    response = register_user(client, email, password)
    data = json.loads(response.data)

    assert response.status_code == 409
    assert 'message' in data
    assert 'User with that email already exists' in data['message']

@pytest.mark.parametrize("payload, expected_message", [
    ({'password': 'password123'}, 'Email and password are required'),
    ({'email': 'no_pass@example.com'}, 'Email and password are required'),
    ({}, 'Email and password are required')
])
def test_register_missing_fields(client, payload, expected_message):
    """Test registration with missing email or password using parametrization."""
    response = client.post(
        '/auth/register',
        data=json.dumps(payload),
        content_type='application/json'
    )
    data = json.loads(response.data)
    assert response.status_code == 400
    assert 'message' in data
    assert expected_message in data['message']

def test_login_success(client):
    """Test successful user login."""
    email = 'login_test@example.com'
    password = 'loginpass'
    
    register_user(client, email, password)
    
    response = login_user(client, email, password)
    data = json.loads(response.data)

    assert response.status_code == 200
    assert 'access_token' in data
    assert 'refresh_token' in data

def test_login_invalid_credentials(client):
    """Test login with incorrect password."""
    email = 'invalid_cred@example.com'
    password = 'correct_password'
    
    register_user(client, email, password)
    
    response = login_user(client, email, 'wrong_password')
    data = json.loads(response.data)

    assert response.status_code == 401
    assert 'message' in data
    assert 'Invalid credentials' in data['message']

def test_login_non_existent_user(client):
    """Test login with an email that does not exist."""
    response = login_user(client, 'nonexistent@example.com', 'some_password')
    data = json.loads(response.data)

    assert response.status_code == 401
    assert 'message' in data
    assert 'Invalid credentials' in data['message']

def test_logout_success(logged_in_client):
    """Test successful user logout and token blacklisting."""
    client, access_token, _, _, _ = logged_in_client

    response = client.post(
        '/auth/logout',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    data = json.loads(response.data)

    assert response.status_code == 200
    assert 'message' in data
    assert 'Successfully logged out' in data['message']
    
    with client.application.app_context():
        decoded_token = decode_token(access_token)
        jti = decoded_token['jti']
        blocked_token = db.session.query(TokenBlocklist).filter_by(jti=jti).first()
        assert blocked_token is not None

def test_logout_no_token(client):
    """Test logout attempt without an access token."""
    response = client.post('/auth/logout')
    data = json.loads(response.data)
    
    assert response.status_code == 401
    assert 'msg' in data
    assert 'Missing Authorization Header' in data['msg']

def test_access_protected_route_after_logout(logged_in_client):
    """
    Test that a blacklisted token cannot access protected routes.
    This test assumes a protected endpoint like '/auth/protected' exists in your Flask app
    and is decorated with `@jwt_required()`.
    """
    client, access_token, _, _, _ = logged_in_client

    logout_response = client.post(
        '/auth/logout',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    assert logout_response.status_code == 200

    protected_response = client.get(
        '/auth/protected',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    data = json.loads(protected_response.data)

    assert protected_response.status_code == 401
    assert 'msg' in data
    assert 'Token has been revoked' in data['msg']

def test_refresh_token_success(logged_in_client):
    """Test successful token refresh."""
    client, _, refresh_token, _, _ = logged_in_client

    response = client.post(
        '/auth/refresh',
        headers={'Authorization': f'Bearer {refresh_token}'}
    )
    data = json.loads(response.data)

    assert response.status_code == 200
    assert 'access_token' in data
    assert 'refresh_token' not in data

def test_refresh_token_invalid(client):
    """Test token refresh with an invalid or missing refresh token."""
    response = client.post('/auth/refresh')
    data = json.loads(response.data)
    assert response.status_code == 401
    assert 'msg' in data
    assert 'Missing Authorization Header' in data['msg']

    response = client.post(
        '/auth/refresh',
        headers={'Authorization': 'Bearer invalid_token_string'}
    )
    data = json.loads(response.data)
    assert response.status_code == 401
    assert 'msg' in data
    assert 'Signature verification failed' in data['msg']

    email = 'access_as_refresh@example.com'
    password = 'accesspass'
    register_user(client, email, password)
    login_response = login_user(client, email, password)
    login_data = json.loads(login_response.data)
    access_token = login_data['access_token']

    response = client.post(
        '/auth/refresh',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    data = json.loads(response.data)
    assert response.status_code == 401
    assert 'msg' in data
    assert 'Only refresh tokens are allowed' in data['msg']