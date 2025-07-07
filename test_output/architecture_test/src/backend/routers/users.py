from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal

router = APIRouter(prefix="/users", tags=["users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
async def read_users(db: Session = Depends(get_db)):
    # Add your user retrieval logic here
    return {"message": "Users endpoint"}