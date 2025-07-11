from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, database

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI Operational Infrastructure Demo",
    description="A demo FastAPI application with comprehensive operational setup.",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Dependency to get the database session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    # Create database tables if they don't exist
    # In a real production scenario, use Alembic for migrations
    models.Base.metadata.create_all(bind=database.engine)
    print("Database tables checked/created.")

@app.get("/health", status_code=status.HTTP_200_OK, summary="Health Check")
async def health_check():
    """
    Performs a simple health check to ensure the application is running.
    """
    return {"status": "ok", "message": "Application is healthy"}

@app.post("/items/", response_model=schemas.Item, status_code=status.HTTP_201_CREATED, summary="Create a new item")
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """
    Creates a new item in the database.
    """
    db_item = models.Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items/", response_model=List[schemas.Item], summary="Retrieve all items")
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieves a list of all items from the database.
    """
    items = db.query(models.Item).offset(skip).limit(limit).all()
    return items

@app.get("/items/{item_id}", response_model=schemas.Item, summary="Retrieve a single item by ID")
def read_item(item_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single item by its ID.
    """
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=schemas.Item, summary="Update an existing item")
def update_item(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """
    Updates an existing item in the database.
    """
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    db_item.name = item.name
    db_item.description = item.description
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an item")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    Deletes an item from the database.
    """
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    return