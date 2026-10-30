"""Параметри варіанта: предметна область, одиниця вимірювання, поріг."""

from shared.student import DATA_VARIANT, VARIANT_NUMBER

# Номер варіанта студента 23; вхідні дані беруться циклічно -> варіант 8.
VARIANT = DATA_VARIANT

APP_TITLE = "Облік часу відновлення сервісів"
APP_DESCRIPTION = (
    f"ЛР №3, варіант {VARIANT_NUMBER} (дані варіанта {VARIANT}). "
    "Сервіс обліку навчальних вимірювань відновлення сервісів: "
    "категорія визначає сервіс, `value` — час відновлення у хвилинах "
    "(невід'ємне скінченне число), `status` — стан перевірки "
    "вимірювання. Поріг реагування — 60 хвилин."
)

VALUE_UNIT = "minutes"
VALUE_MIN = 0.0
# Прикладного верхнього порога немає; SQL відхиляє лише нескінченність.
THRESHOLD = 60.0

STATUSES = ("new", "in_progress", "done")
CATEGORY_NAMES = ("database", "web_service", "file_storage")
RECORD_TITLE = "Вимірювання відновлення"
SEED_VALUES = (75.0, 20.0, 40.0, 90.0, 35.0, 65.0, 55.0, 60.0)

# Обмеження списку та пакета.
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_BULK = 100
