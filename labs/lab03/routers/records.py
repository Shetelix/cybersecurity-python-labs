"""Маршрути для записів (вимірювань відновлення)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from labs.lab03 import repository
from labs.lab03.config import DEFAULT_LIMIT, MAX_LIMIT, VALUE_MIN
from labs.lab03.schemas import (
    ErrorMessage,
    RecordBulk,
    RecordCreate,
    RecordRead,
    RecordReplace,
    Status,
)

router = APIRouter(prefix="/records", tags=["records"])

RecordId = Annotated[
    int, Path(gt=0, description="Ідентифікатор запису (ціле > 0)")
]

NOT_FOUND = {
    "model": ErrorMessage,
    "description": "Запис або категорію не знайдено",
}
CONFLICT = {"model": ErrorMessage, "description": "Дублікат code"}


def _to_http(error: repository.RepositoryError) -> HTTPException:
    """Перетворити помилку шару даних на HTTP-відповідь."""
    if isinstance(error, repository.NotFoundError):
        return HTTPException(404, str(error))
    if isinstance(error, repository.ConflictError):
        return HTTPException(409, "Запис із таким code вже існує")
    return HTTPException(422, str(error))


@router.get(
    "",
    response_model=list[RecordRead],
    summary="Список записів із фільтрами та сторінками",
)
def list_records(
    category_id: Annotated[
        int | None, Query(gt=0, description="Лише записи категорії")
    ] = None,
    status_filter: Annotated[
        Status | None,
        Query(alias="status", description="Лише записи з цим статусом"),
    ] = None,
    min_value: Annotated[
        float | None,
        Query(
            ge=VALUE_MIN,
            allow_inf_nan=False,
            description="value >= min_value (хвилини)",
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Буквальний підрядок у title (з урахуванням регістру)",
        ),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description="Кількість записів")
    ] = DEFAULT_LIMIT,
    offset: Annotated[
        int, Query(ge=0, description="Кількість пропущених записів")
    ] = 0,
) -> list[dict]:
    """Повернути записи за фільтрами (AND), упорядковані за id."""
    return repository.list_records(
        category_id=category_id,
        status=status_filter,
        min_value=min_value,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/bulk",
    response_model=list[RecordRead],
    status_code=status.HTTP_201_CREATED,
    summary="Пакетне створення записів (атомарно)",
    responses={404: NOT_FOUND, 409: CONFLICT},
)
def create_records_bulk(payload: RecordBulk) -> list[dict]:
    """Додати від 1 до 100 записів в одній транзакції: усі або жодного."""
    try:
        return repository.create_records_bulk(
            item.model_dump() for item in payload
        )
    except repository.RepositoryError as error:
        raise _to_http(error) from error


@router.get(
    "/{record_id}",
    response_model=RecordRead,
    summary="Отримати запис за id",
    responses={404: NOT_FOUND},
)
def get_record(record_id: RecordId) -> dict:
    """Повернути один запис."""
    try:
        return repository.get_record(record_id)
    except repository.RepositoryError as error:
        raise _to_http(error) from error


@router.post(
    "",
    response_model=RecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити запис",
    responses={404: NOT_FOUND, 409: CONFLICT},
)
def create_record(payload: RecordCreate) -> dict:
    """Створити запис; id і category_name формує сервер."""
    try:
        return repository.create_record(payload.model_dump())
    except repository.RepositoryError as error:
        raise _to_http(error) from error


@router.put(
    "/{record_id}",
    response_model=RecordRead,
    summary="Повністю замінити змінювані поля запису",
    responses={404: NOT_FOUND, 409: CONFLICT},
)
def replace_record(record_id: RecordId, payload: RecordReplace) -> dict:
    """Замінити всі п'ять змінюваних полів; id не змінюється."""
    try:
        return repository.replace_record(record_id, payload.model_dump())
    except repository.RepositoryError as error:
        raise _to_http(error) from error


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити запис",
    responses={404: NOT_FOUND},
)
def delete_record(record_id: RecordId) -> Response:
    """Видалити запис за id."""
    try:
        repository.delete_record(record_id)
    except repository.RepositoryError as error:
        raise _to_http(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
