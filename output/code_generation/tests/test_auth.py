import pytest
from httpx import AsyncClient
from models import User, UserRole
from services import UserService
from schemas import UserCreate
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session):
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "NewUserPass123!",
        "full_name": "New User",
        "role": "tester"
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "tester"
    assert "id" in data

    # Verify user in DB
    user_service = UserService(db_session)
    user_in_db = await user_service.get_user_by_username("newuser")
    assert user_in_db is not None
    assert user_in_db.email == "newuser@example.com"

@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: AsyncClient, test_user: User):
    user_data = {
        "username": test_user.username, # Duplicate username
        "email": "another@example.com",
        "password": "NewUserPass123!",
        "full_name": "Another User"
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 409
    assert "Username" in response.json()["detail"]

@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient, test_user: User):
    user_data = {
        "username": "anotheruser",
        "email": test_user.email, # Duplicate email
        "password": "NewUserPass123!",
        "full_name": "Another User"
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 409
    assert "Email" in response.json()["detail"]

@pytest.mark.asyncio
async def test_register_user_invalid_password(client: AsyncClient):
    user_data = {
        "username": "weakpassuser",
        "email": "weak@example.com",
        "password": "weak", # Too short, no special char, no digit, no uppercase
        "full_name": "Weak Pass User"
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 422 # Unprocessable Entity due to Pydantic validation
    assert "password" in response.json()["errors"][0]["loc"]
    assert "at least one digit" in response.json()["errors"][0]["msg"]

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, test_user: User):
    response = await client.post(
        "/auth/token",
        data={"username": test_user.username, "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_for_access_token_invalid_credentials(client: AsyncClient, test_user: User):
    response = await client.post(
        "/auth/token",
        data={"username": test_user.username, "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

    response = await client.post(
        "/auth/token",
        data={"username": "nonexistent", "password": "anypassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, test_user: User, test_user_token: str):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id
    assert data["role"] == test_user.role.value

@pytest.mark.asyncio
async def test_read_users_me_unauthorized(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

    response = await client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"

@pytest.mark.asyncio
async def test_inactive_user_login(client: AsyncClient, db_session):
    # Create an inactive user
    inactive_user_data = UserCreate(
        username="inactiveuser",
        email="inactive@example.com",
        password="InactivePassword123!",
        full_name="Inactive User",
        role=UserRole.TESTER
    )
    user_service = UserService(db_session)
    inactive_user = await user_service.create_user(inactive_user_data)
    inactive_user.is_active = False
    db_session.add(inactive_user)
    await db_session.commit()
    await db_session.refresh(inactive_user)

    response = await client.post(
        "/auth/token",
        data={"username": inactive_user.username, "password": "InactivePassword123!"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"