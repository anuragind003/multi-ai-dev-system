import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.schemas.security_test import UserCreate, UserResponse, Token
from app.services.user_service import UserService
from app.core.security import create_access_token
from app.api.dependencies import get_current_active_user, has_role
from app.models.security_test import User, UserRole
from app.core.exceptions import UnauthorizedException, ConflictException, ForbiddenException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a new user")
async def register_user(
    user_data: UserCreate,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN]))] = None # Only admin can register users
):
    """
    Registers a new user in the system.
    
    **Roles required:** `admin`
    
    - **username**: Unique username for the new user.
    - **password**: Password for the new user (min 8 characters).
    - **email**: Optional email address.
    - **full_name**: Optional full name.
    - **role**: Role of the user (admin, tester, viewer). Default is `viewer`.
    - **is_active**: Whether the user account is active. Default is `true`.
    """
    user_service = UserService(db_session)
    try:
        new_user = await user_service.create_user(user_data, current_user)
        return new_user
    except ConflictException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not register user")

@router.post("/token", response_model=Token, summary="Authenticate user and get JWT token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Authenticates a user with username and password, and returns an access token.
    
    - **username**: The user's username.
    - **password**: The user's password.
    """
    user_service = UserService(db_session)
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise UnauthorizedException(detail="Incorrect username or password")
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "roles": [user.role.value]}
    )
    logger.info(f"User '{user.username}' successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse, summary="Get current authenticated user's details")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Retrieves the details of the currently authenticated user.
    
    **Roles required:** Any active user.
    """
    return current_user

@router.put("/users/{user_id}", response_model=UserResponse, summary="Update user details by ID")
async def update_user_by_id(
    user_id: int,
    user_data: Annotated[UserCreate, Body(embed=False)], # Use UserCreate for update as well, but fields are optional
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Updates details for a specific user.
    
    **Roles required:** `admin` can update any user. Other users can only update their own profile.
    
    - **user_id**: The ID of the user to update.
    - **user_data**: The updated user information.
    """
    user_service = UserService(db_session)
    try:
        updated_user = await user_service.update_user(user_id, user_data, current_user)
        return updated_user
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update user")

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user by ID")
async def delete_user_by_id(
    user_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN]))]
):
    """
    Deletes a user from the system.
    
    **Roles required:** `admin`
    
    - **user_id**: The ID of the user to delete.
    """
    user_service = UserService(db_session)
    try:
        await user_service.delete_user(user_id, current_user)
        return {"message": "User deleted successfully"}
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete user")