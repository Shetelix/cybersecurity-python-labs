"""SQL-операції з параметризованими запитами (без залежності від FastAPI).

Кожна функція відкриває власне з'єднання й закриває його після операції.
Зміни виконуються в контекстному менеджері ``with connection``: за успіху
транзакція підтверджується, за винятку — скасовується.
"""

import sqlite3
from collections.abc import Iterable, Mapping
from contextlib import closing
from typing import Any

from labs.lab03.config import THRESHOLD
from labs.lab03.database import get_connection

RECORD_FIELDS = ("code", "title", "category_id", "value", "status")

# Спільна частина вибірки запису разом із назвою категорії (JOIN).
SELECT_RECORD = """
    SELECT r.id, r.code, r.title, r.category_id, c.name AS category_name,
           r.value, r.status
    FROM records AS r
    JOIN categories AS c ON c.id = r.category_id
"""


class RepositoryError(Exception):
    """Базова помилка шару доступу до даних."""


class NotFoundError(RepositoryError):
    """Запис або категорію не знайдено."""


class ConflictError(RepositoryError):
    """Порушення унікальності або спроба видалити непорожню категорію."""


class ConstraintError(RepositoryError):
    """Дані порушують інше обмеження бази (CHECK, NOT NULL)."""


def _record_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Перетворити рядок результату на словник для моделі відповіді."""
    data = dict(row)
    data["exceeds_threshold"] = data["value"] > THRESHOLD
    return data


def _translate(error: sqlite3.IntegrityError) -> RepositoryError:
    """Перетворити IntegrityError SQLite на помилку предметної області."""
    message = str(error)
    if "UNIQUE" in message:
        return ConflictError("Значення має бути унікальним")
    if "FOREIGN KEY" in message:
        return NotFoundError("Категорію не знайдено")
    return ConstraintError("Дані не відповідають обмеженням бази")


def _category_exists(connection: sqlite3.Connection, category_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return row is not None


def _fetch_record(
    connection: sqlite3.Connection, record_id: int
) -> dict[str, Any] | None:
    row = connection.execute(
        SELECT_RECORD + " WHERE r.id = ?", (record_id,)
    ).fetchone()
    return _record_to_dict(row) if row else None


# ---------------------------------------------------------------- категорії
def list_categories() -> list[dict[str, Any]]:
    """Повернути всі категорії за зростанням id."""
    with closing(get_connection()) as connection:
        rows = connection.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def create_category(name: str) -> dict[str, Any]:
    """Створити категорію; дублікат назви — ConflictError."""
    with closing(get_connection()) as connection:
        try:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)", (name,)
                )
        except sqlite3.IntegrityError as error:
            raise _translate(error) from error
        return {"id": cursor.lastrowid, "name": name}


def delete_category(category_id: int) -> None:
    """Видалити порожню категорію."""
    with closing(get_connection()) as connection:
        with connection:
            if not _category_exists(connection, category_id):
                raise NotFoundError("Категорію не знайдено")
            used = connection.execute(
                "SELECT COUNT(*) FROM records WHERE category_id = ?",
                (category_id,),
            ).fetchone()[0]
            if used:
                raise ConflictError(
                    f"Категорія містить записи ({used}), видалення заборонено"
                )
            connection.execute(
                "DELETE FROM categories WHERE id = ?", (category_id,)
            )


# ------------------------------------------------------------------ записи
def get_record(record_id: int) -> dict[str, Any]:
    """Повернути запис за id або підняти NotFoundError."""
    with closing(get_connection()) as connection:
        record = _fetch_record(connection, record_id)
    if record is None:
        raise NotFoundError("Запис не знайдено")
    return record


def list_records(
    *,
    category_id: int | None = None,
    status: str | None = None,
    min_value: float | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Повернути записи з фільтрами (AND) і поділом на сторінки.

    SQL-фрагменти беруться лише з наперед визначених рядків, а всі
    значення передаються окремим списком параметрів.
    """
    conditions: list[str] = []
    params: list[Any] = []
    if category_id is not None:
        conditions.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        conditions.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        # instr: буквальний пошук із урахуванням регістру, без шаблонів.
        conditions.append("instr(r.title, ?) > 0")
        params.append(q)
    sql = SELECT_RECORD
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with closing(get_connection()) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_record_to_dict(row) for row in rows]


def count_records() -> int:
    """Повернути загальну кількість записів."""
    with closing(get_connection()) as connection:
        return connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]


def _insert_record(
    connection: sqlite3.Connection, data: Mapping[str, Any]
) -> int:
    if not _category_exists(connection, data["category_id"]):
        raise NotFoundError(f"Категорію {data['category_id']} не знайдено")
    cursor = connection.execute(
        "INSERT INTO records (code, title, category_id, value, status) "
        "VALUES (?, ?, ?, ?, ?)",
        tuple(data[field] for field in RECORD_FIELDS),
    )
    return cursor.lastrowid


def create_record(data: Mapping[str, Any]) -> dict[str, Any]:
    """Додати запис і повернути його разом із назвою категорії."""
    with closing(get_connection()) as connection:
        try:
            with connection:
                record_id = _insert_record(connection, data)
        except sqlite3.IntegrityError as error:
            raise _translate(error) from error
        return _fetch_record(connection, record_id)


def replace_record(record_id: int, data: Mapping[str, Any]) -> dict[str, Any]:
    """Повністю замінити змінювані поля запису; id не змінюється."""
    with closing(get_connection()) as connection:
        try:
            with connection:
                if _fetch_record(connection, record_id) is None:
                    raise NotFoundError("Запис не знайдено")
                if not _category_exists(connection, data["category_id"]):
                    raise NotFoundError(
                        f"Категорію {data['category_id']} не знайдено"
                    )
                connection.execute(
                    "UPDATE records SET code = ?, title = ?, "
                    "category_id = ?, value = ?, status = ? WHERE id = ?",
                    (*(data[field] for field in RECORD_FIELDS), record_id),
                )
        except sqlite3.IntegrityError as error:
            raise _translate(error) from error
        return _fetch_record(connection, record_id)


def delete_record(record_id: int) -> None:
    """Видалити запис за id."""
    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM records WHERE id = ?", (record_id,)
            )
            if cursor.rowcount == 0:
                raise NotFoundError("Запис не знайдено")


def create_records_bulk(
    items: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Додати пакет записів атомарно: або всі, або жодного.

    Усі вставлення виконуються в одній транзакції без проміжних commit().
    Будь-яка помилка (дублікат code, неіснуюча категорія, обмеження)
    скасовує весь пакет.
    """
    with closing(get_connection()) as connection:
        try:
            with connection:
                ids = [_insert_record(connection, item) for item in items]
        except sqlite3.IntegrityError as error:
            raise _translate(error) from error
        return [_fetch_record(connection, record_id) for record_id in ids]
