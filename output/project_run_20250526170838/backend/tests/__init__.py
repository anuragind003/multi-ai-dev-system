import os
import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()

def create_test_app():
    app = Flask(__name__)
    app.config.from_mapping(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=os.environ.get('TEST_DATABASE_URL', 'postgresql://user:password@localhost:5432/test_cdp_db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)

    # Import models to ensure they are registered with SQLAlchemy for db.create_all()
    # These imports are necessary for SQLAlchemy to discover the table definitions.
    # They are imported for their side effects of registering with the 'db' instance.
    from backend.models import Customer, Offer, Event, CampaignMetric, IngestionLog

    # Register blueprints here if your main app factory does so,
    # or if you need specific routes available for testing.
    # Example:
    # from backend.routes import api_bp
    # app.register_blueprint(api_bp)

    return app

@pytest.fixture(scope='session')
def app():
    test_app = create_test_app()

    with test_app.app_context():
        try:
            db.drop_all()
            db.create_all()
        except SQLAlchemyError as e:
            pytest.fail(f"Failed to set up test database: {e}")

    yield test_app

    with test_app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def session(app):
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)

        db.session = session

        yield session

        transaction.rollback()
        connection.close()
        session.remove()