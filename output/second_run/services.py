from sqlalchemy.orm import Session
from .models import Task, User
from .schemas import TaskCreate, TaskUpdate
from fastapi import HTTPException, status

class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, task: TaskCreate, owner_id: int):
        db_task = Task(**task.dict(), owner_id=owner_id)
        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def get_task(self, task_id: int, owner_id: int):
        task = self.db.query(Task).filter(Task.id == task_id, Task.owner_id == owner_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def update_task(self, task_id: int, task_update: TaskUpdate, owner_id: int):
        db_task = self.get_task(task_id, owner_id)
        for key, value in task_update.dict(exclude_unset=True).items():
            setattr(db_task, key, value)
        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def delete_task(self, task_id: int, owner_id: int):
        task = self.get_task(task_id, owner_id)
        self.db.delete(task)
        self.db.commit()
        return {"message": "Task deleted"}

    def get_all_tasks(self, owner_id: int):
        return self.db.query(Task).filter(Task.owner_id == owner_id).all()

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, user_create):
        db_user = User(username=user_create.username, is_active=True)
        db_user.set_password(user_create.password)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user