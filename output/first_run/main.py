python
### FILE: models.py
from pydantic import BaseModel, validator, constr
from datetime import date, datetime
from typing import Optional

class TaskBase(BaseModel):
    title: constr(min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None

    @validator('due_date', pre=True)
    def parse_due_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD.')
        return value

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    completed: Optional[bool] = False

class Task(TaskBase):
    id: int
    completed: bool = False

    class Config:
        orm_mode = True  # Enable ORM mode for SQLAlchemy integration