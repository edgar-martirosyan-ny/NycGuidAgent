from contextlib import asynccontextmanager
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import engine
from app.routers import health, types, discovery, detail, save

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-add city column to destination table if it doesn't exist
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = :db "
                "AND TABLE_NAME = 'destination' "
                "AND COLUMN_NAME = 'city'"
            ),
            {"db": settings.DB_NAME},
        )
        if result.scalar() == 0:
            conn.execute(text("ALTER TABLE destination ADD COLUMN city VARCHAR(100)"))
            conn.commit()
            print("✓ Added 'city' column to destination table")
    yield


app = FastAPI(title="NycGuidAgent", lifespan=lifespan)


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=503,
        content={"detail": f"Database error: {str(exc)}"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected server error occurred: {str(exc)}"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(types.router, prefix="/api")
app.include_router(discovery.router, prefix="/api")
app.include_router(detail.router, prefix="/api")
app.include_router(save.router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
