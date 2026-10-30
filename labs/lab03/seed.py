"""Початкове заповнення бази з data/seed.json.

Запуск з кореня репозиторію: ``python -m labs.lab03.seed``.
Нова порожня база отримує 3 категорії та 8 записів в одній транзакції;
непорожня база не змінюється.
"""

import json
import logging
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from labs.lab03.database import (
    BASE_DIR,
    display_path,
    get_connection,
    initialize_database,
)
from labs.lab03.schemas import RecordCreate

SEED_PATH = BASE_DIR / "data" / "seed.json"

logger = logging.getLogger("lab03.seed")


class CategorySeed(BaseModel):
    """Категорія в початкових даних (id задано явно)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=40)


class SeedData(BaseModel):
    """Структура seed.json: categories і records."""

    model_config = ConfigDict(extra="forbid")

    categories: list[CategorySeed] = Field(min_length=1)
    records: list[RecordCreate] = Field(min_length=1)


def load_seed(path: Path) -> SeedData:
    """Прочитати й перевірити JSON із початковими даними."""
    data = SeedData.model_validate(json.loads(path.read_text("utf-8")))
    codes = [record.code for record in data.records]
    if len(codes) != len(set(codes)):
        raise ValueError("у seed.json повторюються значення code")
    return data


def database_is_empty(connection: sqlite3.Connection) -> bool:
    """Перевірити, що в таблицях немає жодного рядка."""
    row = connection.execute(
        "SELECT EXISTS (SELECT 1 FROM categories) "
        "OR EXISTS (SELECT 1 FROM records)"
    ).fetchone()
    return not row[0]


def seed(path: Path = SEED_PATH) -> int:
    """Заповнити порожню базу; повернути код завершення."""
    initialize_database()
    try:
        data = load_seed(path)
    except (OSError, ValueError, ValidationError) as error:
        logger.error("Некоректні початкові дані %s: %s", path.name, error)
        return 1

    with closing(get_connection()) as connection:
        if not database_is_empty(connection):
            print("База вже містить дані: повторне заповнення не виконано.")
            return 0
        try:
            with connection:
                connection.executemany(
                    "INSERT INTO categories (id, name) VALUES (?, ?)",
                    [(c.id, c.name) for c in data.categories],
                )
                connection.executemany(
                    "INSERT INTO records "
                    "(code, title, category_id, value, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        (r.code, r.title, r.category_id, r.value, r.status)
                        for r in data.records
                    ],
                )
        except sqlite3.IntegrityError as error:
            logger.error("Заповнення скасовано, дані не змінено: %s", error)
            return 1
        categories = connection.execute(
            "SELECT COUNT(*) FROM categories"
        ).fetchone()[0]
        records = connection.execute(
            "SELECT COUNT(*) FROM records"
        ).fetchone()[0]
    print(
        f"Базу заповнено з {display_path(path)}: "
        f"категорій — {categories}, записів — {records}."
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(levelname)s] %(message)s"
    )
    sys.exit(seed())
