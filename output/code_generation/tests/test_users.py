import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models import UserRole
from schemas import UserResponse, Token

@pytest.mark.asyncio
async def test_register_user_as_admin(client: AsyncClient, get_admin_auth_token: str):
    """Test that an admin can register a new user."""
    admin_token = get_admin_auth_token
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "NewUserPass1!",
        "full_name": "New User",
        "role": UserRole.TEAM_LEAD.value
    }
    response = await client.post(
        "/users/register",
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    user_response = UserResponse(**response.json())
    assert user_response.username == user_data["username"]
    assert user_response.email == user_data["email"]
    assert user_response.role == UserRole.TEAM_LEAD
    assert user_response.is_active is True

@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: AsyncClient, get_admin_auth_token: str):
    """Test registering a user with a duplicate username."""
    admin_token = get_admin_auth_token
    user_data = {
        "username": "duplicateuser",
        "email": "dup1@example.com",
        "password": "Password1!",
        "full_name": "Duplicate User",
        "role": UserRole.TEAM_LEAD.value
    }
    response1 = await client.post(
        "/users/register",
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response1.status_code == 201

    response2 = await client.post(
        "/users/register",
        json=user_data, # Same username
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response2.status_code == 409 # Conflict
    assert "Username already registered" in response2.json()["detail"]

@pytest.mark.asyncio
async def test_register_user_invalid_password(client: AsyncClient, get_admin_auth_token: str):
    """Test registering a user with an invalid password."""
    admin_token = get_admin_auth_token
    user_data = {
        "username": "weakpassuser",
        "email": "weak@example.com",
        "password": "weak", # Too short, no special, no digit, no upper
        "full_name": "Weak Pass User",
        "role": UserRole.TEAM_LEAD.value
    }
    response = await client.post(
        "/users/register",
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 422 # Unprocessable Entity (Pydantic validation)
    assert "password" in response.json()["detail"][0]["loc"]
    assert "Password must contain at least one digit" in response.json()["detail"][0]["msg"]

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, create_test_user):
    """Test successful user login and token generation."""
    response = await client.post(
        "/users/token",
        data={"username": create_test_user.username, "password": "TestPassword1!"}
    )
    assert response.status_code == 200
    token = Token(**response.json())
    assert token.access_token is not None
    assert token.token_type == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with incorrect password."""
    response = await client.post(
        "/users/token",
        data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, get_auth_token: str, create_test_user):
    """Test retrieving current authenticated user's details."""
    token = get_auth_token
    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    user_response = UserResponse(**response.json())
    assert user_response.username == create_test_user.username
    assert user_response.email == create_test_user.email
    assert user_response.role == create_test_user.role

@pytest.mark.asyncio
async def test_read_users_me_unauthorized(client: AsyncClient):
    """Test retrieving current user without authentication."""
    response = await client.get("/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_logout_revokes_token(client: AsyncClient, get_auth_token: str):
    """Test that logout revokes the token and prevents further use."""
    token = get_auth_token

    # First, verify token works
    response_me = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response_me.status_code == 200

    # Then, logout
    response_logout = await client.post(
        "/users/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response_logout.status_code == 204

    # Try to use the token again, should fail
    response_after_logout = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response_after_logout.status_code == 401
    assert response_after_logout.json()["detail"] == "Token has been revoked."