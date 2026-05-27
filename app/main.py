"""Document Management System — FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import documents

app = FastAPI(
    title="Document Management System",
    description=(
        "RESTful API for uploading, storing, searching, and managing documents "
        "with metadata tagging."
    ),
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(documents.router)
