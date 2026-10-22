"""Головний файл для демонстрації лабораторної роботи №1."""

from labs.lab01 import task1, task2, task3
from shared.student import (
    DATA_VARIANT,
    GROUP_NAME,
    STUDENT_NAME,
    VARIANT_NUMBER,
)


def header(title):
    """Вивести заголовок розділу."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    """Запустити всі три завдання по черзі."""
    print(
        f"Лабораторна робота №1. {STUDENT_NAME}, {GROUP_NAME}, "
        f"варіант {VARIANT_NUMBER} (дані варіанта {DATA_VARIANT})"
    )
    header("Завдання 1: аналізатор надійності паролів")
    task1.run()
    header("Завдання 2: багаторівневий контроль доступу")
    task2.run()
    header("Завдання 3: хешування, CSV та JSON-логування")
    task3.run()


if __name__ == "__main__":
    main()
