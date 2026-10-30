"""Точка входу ЛР №2: команди ``demo`` (завдання 1) та ``analyze`` (2).

Запуск з кореня репозиторію:
    python -m labs.lab02.main demo
    python -m labs.lab02.main analyze [--dns-log ...] [--blacklist ...]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import timedelta

from labs.lab02 import task2
from labs.lab02.task1 import (
    SESSION_TIMEOUT_SEC,
    Admin,
    AuditLog,
    Session,
    User,
    UserAccount,
)
from shared.student import (
    DATA_VARIANT,
    GROUP_NAME,
    STUDENT_NAME,
    VARIANT_NUMBER,
)


def header(title: str) -> None:
    """Вивести заголовок кроку демонстрації."""
    print(f"\n--- {title} ---")


def run_demo() -> int:
    """Показати роботу класів завдання 1."""
    print(
        f"ЛР №2, завдання 1. {STUDENT_NAME}, {GROUP_NAME}, "
        f"варіант {VARIANT_NUMBER}"
    )
    audit = AuditLog()

    header("1. Користувач і пароль (PBKDF2-HMAC-SHA256 + сіль)")
    alice = User("alice", "alice_k@example.com")
    alice.set_password("S3cure!Pass2026")
    print(alice)
    print("Атрибут __password_hash ззовні:", hasattr(alice, "__password_hash"))
    print(
        "Після name mangling (_User__password_hash) існує:",
        hasattr(alice, "_User__password_hash"),
    )

    header("2. Невдалий і успішний вхід")
    account = UserAccount(alice, audit_log=audit)
    print(
        "Вхід з неправильним паролем:",
        account.login("alice", "wrong-pass", "10.0.0.15"),
    )
    print("Автентифікований:", account.is_authenticated())
    print(
        "Вхід з правильним паролем:",
        account.login("alice", "S3cure!Pass2026", "10.0.0.15"),
    )
    print("Автентифікований:", account.is_authenticated())
    print("Сеанс:", account["session"])

    header("3. Зміна email з валідацією")
    alice.email = "alice_new@corp.example.org"
    print("Новий email:", alice.email)
    for bad in ("1alice@example.com", "al@example.com", "alice@localhost"):
        try:
            alice.email = bad
        except ValueError as exc:
            print("Відхилено:", exc)

    header("4. Права адміністратора (наслідування Admin -> User)")
    admin = Admin(
        "root_adm", "root_adm@corp.example.org", permissions=["read_logs"]
    )
    admin.set_password("Adm1n!Strong#Key")
    admin.grant_permission("manage_users")
    admin.grant_permission("edit_firewall")
    print(admin)
    print("Може manage_users:", admin.has_permission("manage_users"))
    admin.revoke_permission("edit_firewall")
    print("Після відкликання edit_firewall:", admin)
    print("Може edit_firewall:", admin.has_permission("edit_firewall"))

    header("5. Доступ за ключем: __getitem__ / __setitem__")
    print('account["user"] ->', account["user"])
    for key, value in (("password_hash", None), ("session", "not a session")):
        try:
            if value is None:
                account[key]
            else:
                account[key] = value
        except (KeyError, TypeError) as exc:
            print(f"{type(exc).__name__}: {exc}")

    header(f"6. Завершення сеансу за таймаутом ({SESSION_TIMEOUT_SEC} с)")
    # Імітуємо бездіяльність, щоб не чекати 15 хвилин.
    account.session.last_activity -= timedelta(seconds=SESSION_TIMEOUT_SEC + 1)
    print(
        "Автентифікований після 901 с бездіяльності:",
        account.is_authenticated(),
    )
    try:
        Session("10.0.0.15").is_active(0)
    except ValueError as exc:
        print("is_active(0) ->", exc)

    header("7. Новий вхід і вихід із системи")
    print("Вхід:", account.login("alice", "S3cure!Pass2026", "10.0.0.15"))
    account.logout()
    print("Після logout автентифікований:", account.is_authenticated())

    header("8. Вхід заблокованого користувача")
    alice.deactivate()
    print(alice)
    print("Вхід:", account.login("alice", "S3cure!Pass2026", "10.0.0.15"))

    header("9. Журнал AuditLog (паролі не записуються)")
    audit.show_all()
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Створити парсер з підкомандами demo та analyze."""
    parser = argparse.ArgumentParser(
        prog="python -m labs.lab02.main",
        description="ЛР №2: ООП-демонстрація та аналізатор DNS-журналів "
        f"(варіант {VARIANT_NUMBER}, дані варіанта {DATA_VARIANT}).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="демонстрація класів завдання 1")
    analyze = sub.add_parser(
        "analyze", help="аналіз журналу DNS-запитів (завдання 2)"
    )
    task2.add_arguments(analyze)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Розібрати аргументи й виконати команду."""
    logging.basicConfig(
        level=logging.INFO, format="[%(levelname)s] %(message)s"
    )
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        return run_demo()
    return task2.run(args)


if __name__ == "__main__":
    sys.exit(main())
