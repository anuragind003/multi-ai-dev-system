from celery import Celery

# Initialize the Celery application instance.
# This instance will be configured by the main Flask application
# (e.g., in app/routes/__init__.py or app/__init__.py)
# to load settings like broker URL and result backend from Flask's app.config.
celery_app = Celery('cdp_tasks')

# This file serves as the entry point for defining the Celery application
# for background tasks and scheduled jobs within the CDP system.
# Individual task functions will be defined in separate modules
# within the 'app/tasks' package (e.g., app/tasks/data_ingestion.py,
# app/tasks/data_retention.py, etc.) and decorated with @celery_app.task.