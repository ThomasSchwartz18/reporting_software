# Reporting Software

A minimal Flask application that demonstrates a secure login flow backed by a SQLite database. The structure is designed to scale as the application grows, making it easy to expand the codebase with additional blueprints, models and services.

## Features

- Flask application factory with blueprints for modular growth
- SQLite database via SQLAlchemy with automatic schema creation
- AOI problem codes synchronised from a Supabase ``defects`` table
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

3. Provide the required environment variables:

   ```bash
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_KEY="service-role-or-other-secure-key"
   ```

   The AOI module uses these values to query the Supabase ``defects`` table and
   keep the local lookup data in sync.

4. Run the application:

   ```bash
   flask --app wsgi run --host 0.0.0.0 --port 5000
   ```

   Alternatively, run `python wsgi.py`.

5. Visit [http://localhost:5000](http://localhost:5000) and log in with the default credentials.

## Environment Variables

| Name | Required | Description |
| ---- | -------- | ----------- |
| `SUPABASE_URL` | Yes | Supabase project URL (e.g. `https://xyzcompany.supabase.co`). |
| `SUPABASE_KEY` | Yes | Supabase service role or anon key with access to the `defects` table. |
| `SUPABASE_TIMEOUT` | No | Request timeout (seconds) for Supabase HTTP calls. Defaults to `10`. |

The application will start and serve pages without Supabase, but AOI problem
codes will not be available until the environment variables are provided.

## Future Enhancements

- Replace the default credentials with user registration and role management
- Add reporting data models and upload endpoints
- Integrate form validation and CSRF protection via Flask-WTF
- Introduce automated testing and linting workflows
