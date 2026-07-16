"""Gunicorn/WSGI entrypoint.

Run in production with e.g.:
    venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
