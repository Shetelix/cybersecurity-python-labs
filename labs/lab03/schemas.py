"""Pydantic-моделі запитів і відповідей."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from labs.lab03.config import MAX_BULK, VALUE_MIN

Status = Literal["new", "in_progress", "done"]


class StrictModel(BaseModel):
    """Базова модель: обрізання пробілів і заборона невідомих полів."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryCreate(StrictModel):
    """Дані для створення категорії (id створює база)."""

    name: str = Field(min_length=2, max_length=40, examples=["backup_service"])


class CategoryRead(BaseModel):
    """Категорія у відповіді."""

    id: int
    name: str


class RecordCreate(StrictModel):
    """Змінювані поля запису; id задає база, а не клієнт."""

    code: str = Field(min_length=3, max_length=40, examples=["V08-TEST"])
    title: str = Field(
        min_length=3,
        max_length=120,
        examples=["Навчальне вимірювання відновлення"],
    )
    category_id: int = Field(gt=0, examples=[1])
    value: float = Field(
        ge=VALUE_MIN,
        allow_inf_nan=False,
        description="Час відновлення у хвилинах (скінченне число >= 0)",
        examples=[42.5],
    )
    status: Status = Field(examples=["new"])


class RecordReplace(RecordCreate):
    """Повна заміна: усі змінювані поля обов'язкові."""


class RecordRead(BaseModel):
    """Запис у відповіді разом із назвою категорії."""

    id: int
    code: str
    title: str
    category_id: int
    category_name: str
    value: float
    status: Status
    exceeds_threshold: bool = Field(
        description="Чи перевищує час відновлення поріг 60 хвилин"
    )


RecordBulk = Annotated[
    list[RecordCreate], Field(min_length=1, max_length=MAX_BULK)
]


class StudentRead(BaseModel):
    """Дані студента з shared/student.py."""

    student_name: str
    group_name: str
    variant_number: int
    data_variant: int


class ErrorMessage(BaseModel):
    """Тіло відповіді з описом помилки."""

    detail: str
