"""FastAPI-застосунок ЛР №3 і підключення маршрутів.

Запуск з кореня репозиторію:
    uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
"""

import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from labs.lab03.config import APP_DESCRIPTION, APP_TITLE, VARIANT
from labs.lab03.database import initialize_database
from labs.lab03.routers import categories, records
from labs.lab03.schemas import StudentRead
from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

logger = logging.getLogger("lab03.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці під час запуску (без заповнення)."""
    initialize_database()
    yield


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(sqlite3.Error)
def database_error_handler(_: Request, error: sqlite3.Error) -> JSONResponse:
    """Записати технічну помилку в журнал і не показувати її клієнту."""
    logger.exception("Database error: %s", error)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутрішня помилка сервера бази даних"},
    )


@app.get("/ping", tags=["service"], summary="Перевірка доступності API")
def ping() -> dict[str, str]:
    """Повернути статус сервісу."""
    return {"status": "ok"}


@app.get(
    "/student",
    response_model=StudentRead,
    tags=["service"],
    summary="Дані студента з shared/student.py",
)
def student() -> StudentRead:
    """Повернути ПІБ, групу та номер варіанта."""
    return StudentRead(
        student_name=STUDENT_NAME,
        group_name=GROUP_NAME,
        variant_number=VARIANT_NUMBER,
        data_variant=VARIANT,
    )
