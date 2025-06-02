import pytest
from datetime import datetime, timedelta
from backend.app import create_app, db
from backend.models import User, Task
import sqlalchemy.exc
import time # Required for time.sleep in timestamp tests

@pytest.fixture(scope='module')
def app():
    """
    Fixture to create and configure a Flask application for testing.
    Uses an in-memory SQLite database for isolation.
    """
    app = create_app(config_name='testing')
    with app.app_context():
        db.create_all()  # Create database tables
        yield app
        db.session.remove()
        db.drop_all()  # Drop tables after tests are done

@pytest.fixture(scope='function')
def client(app):
    """
    Fixture to provide a test client for making requests to the Flask app.
    """
    return app.test_client()

@pytest.fixture(scope='function')
def session(app):
    """
    Fixture to provide a database session for each test function.
    Each test runs within its own transaction, which is rolled back
    at the end of the test to ensure a clean state.
    """
    with app.app_context():
        # Establish a connection to the database
        connection = db.engine.connect()
        # Begin a transaction on this connection
        transaction = connection.begin()
        
        # Bind the session to this connection and transaction
        # This ensures all operations within the session use this specific transaction
        db.session.configure(bind=connection, expire_on_commit=False)
        
        yield db.session # Provide the session to the test
        
        # After the test, rollback the transaction to undo all changes
        transaction.rollback()
        # Remove the session
        db.session.remove()
        # Close the connection
        connection.close()

def test_user_model_creation(session):
    """
    Test that a User object can be created and saved correctly.
    Verifies basic field assignments and password hashing.
    """
    email = "test@example.com"
    password = "securepassword123"
    user = User(email=email)
    user.set_password(password)
    
    session.add(user)
    session.commit()
    
    retrieved_user = session.query(User).filter_by(email=email).first()
    
    assert retrieved_user is not None
    assert retrieved_user.email == email
    assert retrieved_user.check_password(password)
    assert retrieved_user.id is not None
    assert isinstance(retrieved_user.created_at, datetime)
    assert isinstance(retrieved_user.updated_at, datetime)
    assert retrieved_user.created_at <= datetime.utcnow()
    assert retrieved_user.updated_at <= datetime.utcnow()

def test_user_model_password_hashing(session):
    """
    Test that the password hashing mechanism works as expected.
    Ensures that the hashed password is not the plain text password
    and that check_password correctly validates.
    """
    email = "hash_test@example.com"
    password = "anothersecurepassword"
    user = User(email=email)
    user.set_password(password)
    
    session.add(user)
    session.commit()
    
    retrieved_user = session.query(User).filter_by(email=email).first()
    
    assert retrieved_user.password_hash is not None
    assert retrieved_user.password_hash != password  # Hashed password should not be plain text
    assert retrieved_user.check_password(password)
    assert not retrieved_user.check_password("wrongpassword")

def test_user_model_email_uniqueness(session):
    """
    Test that the email field is unique, preventing duplicate user registrations.
    """
    email = "unique@example.com"
    user1 = User(email=email)
    user1.set_password("pass1")
    
    session.add(user1)
    session.commit() # First user should commit successfully
    
    user2 = User(email=email)
    user2.set_password("pass2")
    
    with pytest.raises(sqlalchemy.exc.IntegrityError) as excinfo: # Expect a specific integrity error
        session.add(user2)
        session.commit()
    
    # Check for specific error message related to unique constraint violation (common for SQLite)
    assert "UNIQUE constraint failed" in str(excinfo.value)
    session.rollback() # Rollback the failed transaction within the session to clear its state

def test_task_model_creation(session):
    """
    Test that a Task object can be created and saved correctly.
    Verifies basic field assignments and relationships.
    """
    user = User(email="task_owner@example.com")
    user.set_password("taskpass")
    session.add(user)
    session.commit() # Commit user first to get an ID

    title = "Buy groceries"
    description = "Milk, eggs, bread, cheese"
    due_date = datetime.utcnow() + timedelta(days=7)
    
    task = Task(title=title, description=description, due_date=due_date, user_id=user.id)
    
    session.add(task)
    session.commit()
    
    retrieved_task = session.query(Task).filter_by(title=title).first()
    
    assert retrieved_task is not None
    assert retrieved_task.title == title
    assert retrieved_task.description == description
    assert retrieved_task.due_date.date() == due_date.date() # Compare dates only due to potential microsecond differences
    assert retrieved_task.user_id == user.id
    assert retrieved_task.is_completed is False
    assert isinstance(retrieved_task.created_at, datetime)
    assert isinstance(retrieved_task.updated_at, datetime)
    assert retrieved_task.created_at <= datetime.utcnow()
    assert retrieved_task.updated_at <= datetime.utcnow()
    assert retrieved_task.id is not None

def test_task_model_relationships(session):
    """
    Test the relationship between User and Task models.
    Ensures that a Task is correctly associated with a User
    and that the 'user' attribute on Task works.
    """
    user = User(email="rel_user@example.com")
    user.set_password("relpass")
    session.add(user)
    session.commit()

    task1 = Task(title="Task 1 for rel_user", user_id=user.id)
    task2 = Task(title="Task 2 for rel_user", user_id=user.id)
    
    session.add_all([task1, task2])
    session.commit()
    
    retrieved_user = session.query(User).filter_by(email="rel_user@example.com").first()
    assert retrieved_user is not None
    assert len(retrieved_user.tasks) == 2
    assert task1 in retrieved_user.tasks
    assert task2 in retrieved_user.tasks

    retrieved_task1 = session.query(Task).filter_by(title="Task 1 for rel_user").first()
    assert retrieved_task1.user == retrieved_user

def test_task_model_default_values(session):
    """
    Test that default values for Task fields (e.g., is_completed) are applied correctly.
    """
    user = User(email="default_user@example.com")
    user.set_password("defaultpass")
    session.add(user)
    session.commit()

    task = Task(title="Task with defaults", user_id=user.id)
    session.add(task)
    session.commit()

    retrieved_task = session.query(Task).filter_by(title="Task with defaults").first()
    assert retrieved_task.is_completed is False
    assert retrieved_task.description is None # Optional field
    assert retrieved_task.due_date is None # Optional field

def test_task_model_update_timestamps(session):
    """
    Test that `updated_at` timestamp is updated when a Task is modified.
    """
    user = User(email="update_user@example.com")
    user.set_password("updatepass")
    session.add(user)
    session.commit()

    task = Task(title="Original Title", user_id=user.id)
    session.add(task)
    session.commit()

    original_updated_at = task.updated_at
    
    # Simulate a small delay to ensure timestamp difference
    time.sleep(0.01) 

    task.title = "Updated Title"
    # No need to session.add(task) again if it's already tracked by the session
    session.commit()

    retrieved_task = session.query(Task).filter_by(id=task.id).first()
    assert retrieved_task.title == "Updated Title"
    assert retrieved_task.updated_at > original_updated_at
    assert retrieved_task.created_at == original_updated_at # created_at should not change

def test_user_model_update_timestamps(session):
    """
    Test that `updated_at` timestamp is updated when a User is modified.
    """
    user = User(email="user_update_ts@example.com")
    user.set_password("originalpass")
    session.add(user)
    session.commit()

    original_updated_at = user.updated_at
    
    # Simulate a small delay to ensure timestamp difference
    time.sleep(0.01) 

    user.email = "user_updated_ts@example.com"
    user.set_password("newpass") # This also triggers an update
    # No need to session.add(user) again if it's already tracked by the session
    session.commit()

    retrieved_user = session.query(User).filter_by(id=user.id).first()
    assert retrieved_user.email == "user_updated_ts@example.com"
    assert retrieved_user.updated_at > original_updated_at
    assert retrieved_user.created_at == original_updated_at # created_at should not change