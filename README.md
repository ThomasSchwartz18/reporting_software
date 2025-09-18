# Reporting Software

A minimal Flask application that demonstrates a secure login flow backed by a SQLite database. The structure is designed to scale as the application grows, making it easy to expand the codebase with additional blueprints, models and services.

## Features

- Flask application factory with blueprints for modular growth
- SQLite database via SQLAlchemy with automatic schema creation
- Default user credentials (`2276` / `2278!`) stored with a hashed password
- Simple login, logout and protected dashboard views

## Getting Started

1. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:

   ```bash
   flask --app wsgi run --host 0.0.0.0 --port 5000
   ```

   Alternatively, run `python wsgi.py`.

4. Visit [http://localhost:5000](http://localhost:5000) and log in with the default credentials.

## Future Enhancements

- Replace the default credentials with user registration and role management
- Add reporting data models and upload endpoints
- Integrate form validation and CSRF protection via Flask-WTF
- Introduce automated testing and linting workflows
