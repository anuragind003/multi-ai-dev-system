from typing import Optional

from pydantic import BaseModel, validator

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None

    @validator("title")
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    completed: Optional[bool] = None

class TaskResponse(TaskBase):
    id: int
    completed: bool

    class Config:
        orm_mode = True