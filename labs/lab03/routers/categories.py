"""Маршрути для категорій."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status

from labs.lab03 import repository
from labs.lab03.schemas import CategoryCreate, CategoryRead, ErrorMessage

router = APIRouter(prefix="/categories", tags=["categories"])

CategoryId = Annotated[
    int, Path(gt=0, description="Ідентифікатор категорії (ціле > 0)")
]


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Список категорій за зростанням id",
)
def list_categories() -> list[dict]:
    """Повернути всі категорії."""
    return repository.list_categories()


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити категорію",
    responses={409: {"model": ErrorMessage, "description": "Дублікат назви"}},
)
def create_category(payload: CategoryCreate) -> dict:
    """Створити категорію з унікальною назвою."""
    try:
        return repository.create_category(payload.name)
    except repository.ConflictError as error:
        raise HTTPException(
            409, "Категорія з такою назвою вже існує"
        ) from error


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити порожню категорію",
    responses={
        404: {"model": ErrorMessage, "description": "Категорію не знайдено"},
        409: {
            "model": ErrorMessage,
            "description": "Категорія містить записи",
        },
    },
)
def delete_category(category_id: CategoryId) -> Response:
    """Видалити категорію, якщо в ній немає записів."""
    try:
        repository.delete_category(category_id)
    except repository.NotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except repository.ConflictError as error:
        raise HTTPException(409, str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
