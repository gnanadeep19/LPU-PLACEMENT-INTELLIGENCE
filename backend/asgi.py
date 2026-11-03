"""Optional FastAPI ASGI entry point for the existing authenticated Flask API.

All routes remain owned by Flask, preserving its authentication and CSRF rules.
Run from the project root: uvicorn --app-dir backend asgi:app --port 5000
"""
from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware

from app import app as flask_app

app = FastAPI(title='LPU Placement Intelligence API', docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/', WSGIMiddleware(flask_app))
