"""Завдання 1: комплексний аналізатор надійності паролів."""

import random
import string
from collections import Counter

from shared.student import DATA_VARIANT, GROUP_NAME, STUDENT_NAME
from shared.tables import print_table

# Вхідні дані варіанта 8
PASSWORDS = [
    "ThreatH@nt3r",
    "weak123",
    "P3n3trat10n@Test",
    "visitor",
    "Cyber@Defense2023",
    "normal",
    "Incident@R3sp0nse",
    "standard",
    "Risk@Analys1s",
    "typical",
]
CRITERIA = {
    "min_length": 10,
    "require_digits": True,
    "require_upper": True,
    "require_special": True,
}
FORBIDDEN_PASSWORDS = {
    "weak123",
    "visitor",
    "normal",
    "standard",
    "typical",
    "admin",
}

BONUS_LENGTH = 4
DUPLICATES_COUNT = 3

FORBIDDEN = "Заборонений"
WEAK = "Слабкий"
MEDIUM = "Середній"
STRONG = "Сильний"
VERY_STRONG = "Дуже сильний"


def add_random_duplicates(passwords, count=DUPLICATES_COUNT, rng=random):
    """Додати в кінець списку дублікати `count` випадкових паролів."""
    indexes = [rng.randrange(len(passwords)) for _ in range(count)]
    return passwords + [passwords[index] for index in indexes], indexes


def check_groups(password):
    """Повернути словник виконаних груп символів для пароля."""
    return {
        "digits": any(char.isdigit() for char in password),
        "upper": any(char.isupper() for char in password),
        "lower": any(char.islower() for char in password),
        "special": any(char in string.punctuation for char in password),
    }


def rate_password(
    password, counts, criteria=CRITERIA, forbidden=FORBIDDEN_PASSWORDS
):
    """Оцінити пароль і повернути (категорія, коментар)."""
    min_length = criteria["min_length"]
    if password in forbidden:
        return FORBIDDEN, "у списку заборонених"
    if len(password) < min_length:
        return FORBIDDEN, f"коротший за {min_length} символів"

    groups = check_groups(password)
    required = [
        name
        for name, key in (
            ("digits", "require_digits"),
            ("upper", "require_upper"),
            ("special", "require_special"),
        )
        if criteria[key]
    ]
    met = sum(groups[name] for name in required)

    if met == len(required):
        unique = counts[password] == 1
        if len(password) >= min_length + BONUS_LENGTH and unique:
            return VERY_STRONG, "усі критерії, довгий і унікальний"
        if not unique:
            return STRONG, "усі критерії, але пароль повторюється"
        return STRONG, f"усі критерії, довжина < {min_length + BONUS_LENGTH}"
    if met >= 2:
        return MEDIUM, "виконано частину критеріїв"
    return WEAK, "виконано мінімум критеріїв"


def run(rng=None):
    """Виконати завдання 1 і вивести таблицю результатів."""
    rng = rng or random.Random(DATA_VARIANT)
    print(
        f"Студент: {STUDENT_NAME}, група {GROUP_NAME}, "
        f"дані варіанта {DATA_VARIANT}"
    )
    passwords, indexes = add_random_duplicates(PASSWORDS, rng=rng)
    print(f"Випадкові індекси для дублювання: {indexes}")
    counts = Counter(passwords)

    rows = []
    for number, password in enumerate(passwords, start=1):
        category, note = rate_password(password, counts)
        rows.append((number, password, len(password), category, note))
    print_table(("№", "Пароль", "Довжина", "Категорія", "Коментар"), rows)

    summary = Counter(row[3] for row in rows)
    print("Підсумок:", ", ".join(f"{k}: {v}" for k, v in summary.items()))
    return rows


if __name__ == "__main__":
    run()
