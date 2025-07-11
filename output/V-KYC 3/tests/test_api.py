import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
from models import User, Role, Permission
from auth_utils import get_password_hash
from config import settings
import datetime

# Use a separate SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sql_app.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for testing
@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Provides a clean database session for each test.
    Creates tables before tests, drops them after.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def client_fixture(db_session):
    """
    Provides a TestClient instance with the overridden database dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- Helper functions for test data setup ---
def create_test_user(db_session, email, password, is_active=True, roles=None):
    hashed_password = get_password_hash(password)
    user = User(email=email, hashed_password=hashed_password, is_active=is_active)
    if roles:
        for role_name in roles:
            role = db_session.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(name=role_name)
                db_session.add(role)
                db_session.commit()
                db_session.refresh(role)
            user.roles.append(role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def create_test_role(db_session, name, description=None, permissions=None):
    role = Role(name=name, description=description)
    if permissions:
        for perm_name in permissions:
            permission = db_session.query(Permission).filter(Permission.name == perm_name).first()
            if not permission:
                permission = Permission(name=perm_name)
                db_session.add(permission)
                db_session.commit()
                db_session.refresh(permission)
            role.permissions.append(permission)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role

def create_test_permission(db_session, name, description=None):
    permission = Permission(name=name, description=description)
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission

def get_auth_token(client, email, password):
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

# --- Tests ---

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"message": "API is healthy!"}

def test_register_user(client, db_session):
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123", "is_active": True}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "roles" in data
    assert data["is_active"] is True

    # Test duplicate registration
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 409
    assert response.json()["message"] == "User with email 'test@example.com' already exists."

def test_login_user(client, db_session):
    create_test_user(db_session, "login@example.com", "password123")
    response = client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test invalid credentials
    response = client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Incorrect email or password"

    # Test inactive user
    create_test_user(db_session, "inactive@example.com", "password123", is_active=False)
    response = client.post(
        "/auth/login",
        data={"username": "inactive@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert response.json()["message"] == "User account is inactive"

def test_read_users_me(client, db_session):
    user = create_test_user(db_session, "me@example.com", "password123")
    token = get_auth_token(client, "me@example.com", "password123")

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["id"] == user.id

    # Test unauthenticated access
    response = client.get("/users/me")
    assert response.status_code == 401

def test_update_users_me(client, db_session):
    user = create_test_user(db_session, "update_me@example.com", "oldpassword")
    token = get_auth_token(client, "update_me@example.com", "oldpassword")

    response = client.put(
        "/users/me",
        json={"email": "new_email@example.com", "password": "newpassword"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "new_email@example.com"

    # Verify new password works
    new_token = get_auth_token(client, "new_email@example.com", "newpassword")
    assert new_token is not None

    # Test attempt to change roles via /me
    response = client.put(
        "/users/me",
        json={"role_ids": [999]}, # Non-existent role ID
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["message"] == "You cannot modify your own roles via this endpoint."


def test_rbac_get_user_by_id(client, db_session):
    admin_role = create_test_role(db_session, "admin")
    user_read_perm = create_test_permission(db_session, "user:read")
    admin_role.permissions.append(user_read_perm)
    db_session.add(admin_role)
    db_session.commit()

    admin_user = create_test_user(db_session, "admin@example.com", "password123", roles=["admin"])
    regular_user = create_test_user(db_session, "regular@example.com", "password123")
    target_user = create_test_user(db_session, "target@example.com", "password123")

    admin_token = get_auth_token(client, "admin@example.com", "password123")
    regular_token = get_auth_token(client, "regular@example.com", "password123")

    # Admin can get any user
    response = client.get(
        f"/users/{target_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "target@example.com"

    # Regular user cannot get another user
    response = client.get(
        f"/users/{target_user.id}",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Not enough permissions to perform this action."

    # Regular user can get their own profile (tested in test_read_users_me, but re-confirm with /users/{id})
    response = client.get(
        f"/users/{regular_user.id}",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "regular@example.com"

def test_rbac_get_all_users(client, db_session):
    admin_role = create_test_role(db_session, "admin")
    user_read_perm = create_test_permission(db_session, "user:read")
    admin_role.permissions.append(user_read_perm)
    db_session.add(admin_role)
    db_session.commit()

    admin_user = create_test_user(db_session, "admin_all@example.com", "password123", roles=["admin"])
    regular_user = create_test_user(db_session, "regular_all@example.com", "password123")

    admin_token = get_auth_token(client, "admin_all@example.com", "password123")
    regular_token = get_auth_token(client, "regular_all@example.com", "password123")

    # Admin can get all users
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2 # At least admin_user and regular_user

    # Regular user cannot get all users
    response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Not enough permissions to perform this action."

def test_rbac_create_role_permission(client, db_session):
    admin_role = create_test_role(db_session, "admin")
    role_create_perm = create_test_permission(db_session, "role:create")
    perm_create_perm = create_test_permission(db_session, "permission:create")
    admin_role.permissions.extend([role_create_perm, perm_create_perm])
    db_session.add(admin_role)
    db_session.commit()

    admin_user = create_test_user(db_session, "admin_rbac@example.com", "password123", roles=["admin"])
    regular_user = create_test_user(db_session, "regular_rbac@example.com", "password123")

    admin_token = get_auth_token(client, "admin_rbac@example.com", "password123")
    regular_token = get_auth_token(client, "regular_rbac@example.com", "password123")

    # Admin can create role
    response = client.post(
        "/admin/roles",
        json={"name": "editor", "description": "Editor role"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "editor"

    # Regular user cannot create role
    response = client.post(
        "/admin/roles",
        json={"name": "viewer", "description": "Viewer role"},
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403

    # Admin can create permission
    response = client.post(
        "/admin/permissions",
        json={"name": "content:edit", "description": "Edit content"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "content:edit"

    # Regular user cannot create permission
    response = client.post(
        "/admin/permissions",
        json={"name": "content:view", "description": "View content"},
        headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403

def test_rbac_assign_remove_role(client, db_session):
    admin_role = create_test_role(db_session, "admin")
    assign_role_perm = create_test_permission(db_session, "user:assign_role")
    remove_role_perm = create_test_permission(db_session, "user:remove_role")
    admin_role.permissions.extend([assign_role_perm, remove_role_perm])
    db_session.add(admin_role)
    db_session.commit()

    admin_user = create_test_user(db_session, "admin_assign@example.com", "password123", roles=["admin"])
    target_user = create_test_user(db_session, "target_assign@example.com", "password123")
    new_role = create_test_role(db_session, "new_role")

    admin_token = get_auth_token(client, "admin_assign@example.com", "password123")

    # Assign role
    response = client.post(
        f"/admin/users/{target_user.id}/roles/{new_role.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert any(role["name"] == "new_role" for role in response.json()["roles"])

    # Verify role is assigned by fetching user
    response = client.get(
        f"/users/{target_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert any(role["name"] == "new_role" for role in response.json()["roles"])

    # Remove role
    response = client.delete(
        f"/admin/users/{target_user.id}/roles/{new_role.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert not any(role["name"] == "new_role" for role in response.json()["roles"])

    # Test non-existent user/role
    response = client.post(
        f"/admin/users/9999/roles/{new_role.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["message"] == "User with ID 9999 not found."

    response = client.post(
        f"/admin/users/{target_user.id}/roles/9999",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Role with ID 9999 not found."

def test_rate_limiting(client, db_session):
    # Temporarily set a very low rate limit for testing
    original_rate_limit = settings.RATE_LIMIT_PER_MINUTE
    settings.RATE_LIMIT_PER_MINUTE = 5

    # Make requests exceeding the limit
    for i in range(settings.RATE_LIMIT_PER_MINUTE):
        response = client.get("/health")
        assert response.status_code == 200

    response = client.get("/health")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["message"]

    # Restore original rate limit
    settings.RATE_LIMIT_PER_MINUTE = original_rate_limit