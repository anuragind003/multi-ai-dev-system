from app import create_app

# Create the Flask application instance
# This 'app' object is the entry point for WSGI servers (e.g., Gunicorn, uWSGI).
app = create_app()

# This block allows you to run the application directly using `python wsgi.py`
# for local development and testing purposes.
# In a production environment, a WSGI server like Gunicorn will manage the application.
if __name__ == '__main__':
    # It's good practice to set debug=False in production.
    # For local development, debug=True is often useful.
    app.run(debug=True, host='0.0.0.0', port=5000)