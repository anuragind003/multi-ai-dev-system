from app import create_app
from app.extensions import db

app = create_app()

@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    with app.app_context():
        db.create_all()
    print('Initialized the database.')

if __name__ == '__main__':
    app.run(debug=True)