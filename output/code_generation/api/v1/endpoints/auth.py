from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import Token, UserLogin
from services import VKYCService, get_vkyc_service
from crud import VKYCCrud
from utils.logger import get_logger
from utils.exceptions import UnauthorizedException

logger = get_logger(__name__)

router = APIRouter()

# Dependency to get VKYCCrud instance
def get_vkyc_crud(db: AsyncSession = Depends(get_db)) -> VKYCCrud:
    return VKYCCrud(db)

# Dependency to get VKYCService instance
def get_vkyc_service_with_crud(
    crud: VKYCCrud = Depends(get_vkyc_crud)
) -> VKYCService:
    return get_vkyc_service(crud)

@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate User and Get JWT Token",
    description="Authenticates a user with username and password, returning a JWT access token.",
    responses={
        status.HTTP_200_OK: {"description": "Successfully authenticated and received token."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Incorrect username or password."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error for input."}
    }
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    vkyc_service: VKYCService = Depends(get_vkyc_service_with_crud)
):
    """
    Authenticates a user using OAuth2 password flow.
    - **username**: User's username.
    - **password**: User's password.
    """
    user_login = UserLogin(username=form_data.username, password=form_data.password)
    logger.info(f"Attempting to authenticate user: {user_login.username}")
    
    token = await vkyc_service.authenticate_user(user_login)
    if not token:
        logger.warning(f"Authentication failed for user: {user_login.username}")
        raise UnauthorizedException("Incorrect username or password.")
    
    logger.info(f"User '{user_login.username}' authenticated successfully.")
    return token