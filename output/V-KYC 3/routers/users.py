from typing import List
from fastapi import APIRouter, Depends, status, Body
from fastapi.security import SecurityScopes

from schemas import UserRead, UserRegister, UserSeed, HTTPError, UserUpdate
from services import UserService
from dependencies import get_user_service, AdminUser, TeamLeadOrProcessManagerUser, CurrentUser
from models import User
from auth import oauth2_scheme, create_access_token, authenticate_user
from schemas import Token
from utils.logger import logger

router = APIRouter()

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Invalid credentials"},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Inactive user"}
    }
)
async def login_for_access_token(
    email: str = Body(..., embed=True, description="User's email"),
    password: str = Body(..., embed=True, description="User's password"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticates a user with email and password and returns an access token.
    """
    logger.info(f"Attempting to authenticate user: {email}")
    user = await authenticate_user(email, password, user_service)
    if not user.is_active:
        logger.warning(f"Authentication failed: User {email} is inactive.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Define scopes based on user's role
    scopes = ["me"]
    if user.role.name == "Admin":
        scopes.append("admin")
    elif user.role.name in ["Team Lead", "Process Manager"]:
        scopes.append("team_lead_pm")

    access_token = create_access_token(
        data={"sub": user.email, "scopes": scopes}
    )
    logger.info(f"User {email} authenticated successfully.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current authenticated user's details",
    dependencies=[Depends(oauth2_scheme)], # Ensure token is present
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not enough permissions"}
    }
)
async def read_users_me(current_user: CurrentUser):
    """
    Retrieves the details of the currently authenticated user.
    Requires 'me' scope (implicitly granted to all authenticated users).
    """
    logger.info(f"Fetching details for current user: {current_user.email}")
    return current_user

@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Admin only)",
    dependencies=[SecurityScopes(["admin"])], # Requires 'admin' scope
    responses={
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "User with this email already exists"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Role not found"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not enough permissions"}
    }
)
async def register_user(
    user_data: UserRegister,
    user_service: UserService = Depends(get_user_service),
    admin_user: AdminUser = Depends() # Ensures the caller is an admin
):
    """
    Registers a new user with a specified role.
    This endpoint is restricted to users with the 'Admin' role.
    """
    logger.info(f"Admin user {admin_user.email} attempting to register new user: {user_data.email} with role {user_data.role_name}")
    new_user = await user_service.register_user(user_data)
    logger.info(f"New user {new_user.email} registered by admin {admin_user.email}.")
    return new_user

@router.post(
    "/seed-initial-users",
    status_code=status.HTTP_201_CREATED,
    summary="Seed initial VKYC Team Leads and Process Managers (Admin only)",
    dependencies=[SecurityScopes(["admin"])], # Requires 'admin' scope
    responses={
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "One or more users already exist"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "One or more roles not found"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not enough permissions"}
    }
)
async def seed_users(
    user_seed_data: UserSeed,
    user_service: UserService = Depends(get_user_service),
    admin_user: AdminUser = Depends() # Ensures the caller is an admin
):
    """
    Seeds multiple users, typically VKYC Team Leads and Process Managers.
    This endpoint is restricted to users with the 'Admin' role.
    """
    logger.info(f"Admin user {admin_user.email} attempting to seed {len(user_seed_data.users)} users.")
    results = []
    errors = []
    for user_data in user_seed_data.users:
        try:
            new_user = await user_service.register_user(user_data)
            results.append(new_user.email)
        except (UserAlreadyExistsException, RoleNotFoundException) as e:
            errors.append({"email": user_data.email, "error": e.detail})
        except Exception as e:
            logger.error(f"Unexpected error seeding user {user_data.email}: {e}", exc_info=True)
            errors.append({"email": user_data.email, "error": "An unexpected error occurred."})

    if errors:
        logger.warning(f"Seeding completed with errors for some users: {errors}")
        return JSONResponse(
            status_code=status.HTTP_207_MULTI_STATUS,
            content={"message": "Some users could not be seeded.", "seeded": results, "errors": errors}
        )
    logger.info(f"Successfully seeded all {len(results)} users.")
    return {"message": "All users seeded successfully.", "seeded": results}

@router.get(
    "/",
    response_model=List[UserRead],
    summary="Get all users (Admin only)",
    dependencies=[SecurityScopes(["admin"])], # Requires 'admin' scope
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not enough permissions"}
    }
)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
    admin_user: AdminUser = Depends() # Ensures the caller is an admin
):
    """
    Retrieves a list of all registered users.
    This endpoint is restricted to users with the 'Admin' role.
    """
    logger.info(f"Admin user {admin_user.email} fetching all users.")
    users = await user_service.get_all_users(skip=skip, limit=limit)
    return users

@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get user by ID (Admin only)",
    dependencies=[SecurityScopes(["admin"])], # Requires 'admin' scope
    responses={
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "User not found"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not enough permissions"}
    }
)
async def get_user_by_id(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    admin_user: AdminUser = Depends() # Ensures the caller is an admin
):
    """
    Retrieves a single user by their ID.
    This endpoint is restricted to users with the 'Admin' role.
    """
    logger.info(f"Admin user {admin_user.email} fetching user with ID: {user_id}.")
    user = await user_service.get_user_by_id(user_id)
    return user

@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Update user details (Admin only)",
    dependencies=[SecurityScopes(["admin"])], # Requires 'admin' scope
    responses={
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "User or Role not found"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not enough permissions"}
    }
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    admin_user: AdminUser = Depends() # Ensures the caller is an admin
):
    """
    Updates an existing user's details, including email, name, password, and role.
    This endpoint is restricted to users with the 'Admin' role.
    """
    logger.info(f"Admin user {admin_user.email} updating user with ID: {user_id}.")
    updated_user = await user_service.update_user(user_id, user_update)
    return updated_user

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user (Admin only)",
    dependencies=[SecurityScopes(["admin"])], # Requires 'admin' scope
    responses={
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "User not found"},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Not enough permissions"}
    }
)
async def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    admin_user: AdminUser = Depends() # Ensures the caller is an admin
):
    """
    Deletes a user by their ID.
    This endpoint is restricted to users with the 'Admin' role.
    """
    logger.info(f"Admin user {admin_user.email} deleting user with ID: {user_id}.")
    await user_service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)