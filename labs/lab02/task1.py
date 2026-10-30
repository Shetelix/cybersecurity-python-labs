"""Завдання 1. Модель користувача, адміністратора, сеансу та аудиту.

Модуль містить лише класи; демонстрація запускається з main.py командою
``python -m labs.lab02.main demo`` і не виконується під час імпорту.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# Кількість ітерацій PBKDF2-HMAC-SHA256 (рекомендація OWASP для SHA-256).
PBKDF2_ITERATIONS = 600_000
# Довжина випадкової солі в байтах.
SALT_SIZE = 16
# Час дії сеансу без активності, секунди (15 хвилин).
SESSION_TIMEOUT_SEC = 900

# Локальна частина: латинська літера, далі ще 2–63 символи [A-Za-z0-9_]
# (разом 3–64), потім @ і доменне ім'я, що містить принаймні одну крапку.
EMAIL_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9_]{2,63}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
)


def utc_now() -> datetime:
    """Повернути поточний час UTC з часовим поясом."""
    return datetime.now(timezone.utc)


class User:
    """Звичайний користувач системи."""

    def __init__(
        self,
        username: str,
        email: str,
        role: str = "user",
        active: bool = True,
    ) -> None:
        """Створити користувача; пароль задається окремо set_password()."""
        if not username:
            raise ValueError("Ім'я користувача не може бути порожнім")
        self.username = username
        self.email = email  # перевірка формату виконується у сеттері
        self.role = role
        self.active = active
        # Подвійне підкреслення вмикає name mangling: _User__password_hash.
        self.__password_hash: bytes | None = None
        self.__password_salt: bytes | None = None

    @property
    def email(self) -> str:
        """Електронна адреса користувача."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if not isinstance(value, str) or not EMAIL_RE.fullmatch(value):
            raise ValueError(f"Некоректний формат email: {value!r}")
        self._email = value

    @staticmethod
    def _derive(password: str, salt: bytes) -> bytes:
        """Обчислити ключ PBKDF2-HMAC-SHA256 для пароля та солі."""
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )

    def set_password(self, password: str) -> None:
        """Зберегти хеш пароля з новою випадковою сіллю."""
        if not isinstance(password, str) or not password:
            raise ValueError("Пароль не може бути порожнім")
        salt = os.urandom(SALT_SIZE)
        self.__password_salt = salt
        self.__password_hash = self._derive(password, salt)

    def check_password(self, password: str) -> bool:
        """Перевірити пароль, порівнюючи хеші за сталий час."""
        if self.__password_hash is None or self.__password_salt is None:
            return False
        candidate = self._derive(password, self.__password_salt)
        return hmac.compare_digest(candidate, self.__password_hash)

    def deactivate(self) -> None:
        """Заблокувати обліковий запис."""
        self.active = False

    def __str__(self) -> str:
        """Повернути короткий опис без жодних даних про пароль."""
        status = "active" if self.active else "inactive"
        return f"{self.username} <{self.email}> [{self.role}, {status}]"


class Admin(User):
    """Адміністратор: користувач із набором дозволів (наслідування)."""

    def __init__(
        self,
        username: str,
        email: str,
        permissions: Iterable[str] | None = None,
        active: bool = True,
    ) -> None:
        """Створити адміністратора; None замість змінюваного типового []."""
        super().__init__(username, email, role="admin", active=active)
        self.permissions: set[str] = set(permissions or ())

    def grant_permission(self, permission: str) -> None:
        """Надати дозвіл."""
        self.permissions.add(permission)

    def revoke_permission(self, permission: str) -> None:
        """Відкликати дозвіл (без помилки, якщо його не було)."""
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        """Перевірити наявність дозволу."""
        return permission in self.permissions

    def __str__(self) -> str:
        """Додати до опису користувача список прав."""
        perms = ", ".join(sorted(self.permissions)) or "немає"
        return f"{super().__str__()} permissions: {perms}"


class Session:
    """Сеанс користувача з часом входу та останньої активності (UTC)."""

    def __init__(self, ip: str) -> None:
        """Відкрити сеанс з указаної IP-адреси."""
        self.ip = ip
        self.login_time: datetime = utc_now()
        self.last_activity: datetime = self.login_time

    def touch(self) -> None:
        """Оновити час останньої активності."""
        self.last_activity = utc_now()

    def is_active(self, timeout_sec: int) -> bool:
        """Перевірити, чи не минув час бездіяльності timeout_sec."""
        if timeout_sec <= 0:
            raise ValueError("timeout_sec має бути додатним")
        idle = utc_now() - self.last_activity
        return idle < timedelta(seconds=timeout_sec)

    def __str__(self) -> str:
        """Повернути опис сеансу."""
        return (
            f"ip={self.ip}, login={self.login_time:%H:%M:%S} UTC, "
            f"last={self.last_activity:%H:%M:%S} UTC"
        )


@dataclass(frozen=True)
class AuditRecord:
    """Один незмінний запис журналу аудиту."""

    username: str
    action: str
    timestamp: datetime = field(default_factory=utc_now)

    def __str__(self) -> str:
        """Повернути рядок журналу."""
        return (
            f"{self.timestamp:%Y-%m-%d %H:%M:%S} UTC | "
            f"{self.username:<8} | {self.action}"
        )


class AuditLog:
    """Журнал подій безпеки (без паролів)."""

    def __init__(self) -> None:
        """Створити порожній журнал."""
        self._records: list[AuditRecord] = []

    def add_log(self, username: str, action: str) -> AuditRecord:
        """Додати запис і повернути його."""
        record = AuditRecord(username=username, action=action)
        self._records.append(record)
        return record

    def show_all(self) -> list[AuditRecord]:
        """Вивести всі записи та повернути їх копію."""
        for record in self._records:
            print(record)
        return list(self._records)

    def __len__(self) -> int:
        """Повернути кількість записів."""
        return len(self._records)


class UserAccount:
    """Обліковий запис: композиція User, Session та AuditLog."""

    # Ключі, доступні через account[key], та очікувані типи значень.
    _ITEM_TYPES: dict[str, tuple[type, ...]] = {
        "user": (User,),
        "session": (Session, type(None)),
        "audit_log": (AuditLog,),
    }

    def __init__(
        self,
        user: User,
        audit_log: AuditLog | None = None,
        session: Session | None = None,
    ) -> None:
        """Зібрати обліковий запис з готових або нових об'єктів."""
        self.user = user
        self.audit_log = audit_log if audit_log is not None else AuditLog()
        self.session = session

    def login(self, username: str, password: str, ip: str) -> bool:
        """Автентифікувати користувача й відкрити сеанс лише після успіху."""
        ok = (
            username == self.user.username
            and self.user.active
            and self.user.check_password(password)
        )
        if not ok:
            # Пароль у журнал не записується, лише факт невдачі.
            self.audit_log.add_log(username, "login_failure")
            return False
        self.session = Session(ip)
        self.session.touch()
        self.audit_log.add_log(username, "login_success")
        return True

    def is_authenticated(self) -> bool:
        """Перевірити наявність і чинність сеансу (без продовження)."""
        if self.session is None:
            return False
        return self.session.is_active(SESSION_TIMEOUT_SEC)

    def logout(self) -> None:
        """Завершити сеанс і зафіксувати подію."""
        if self.session is not None:
            self.session = None
            self.audit_log.add_log(self.user.username, "logout")

    def __getitem__(self, key: str) -> object:
        """Надати доступ до дозволених складових за ключем."""
        if key not in self._ITEM_TYPES:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value: object) -> None:
        """Замінити дозволену складову з перевіркою типу."""
        if key not in self._ITEM_TYPES:
            raise KeyError(key)
        expected = self._ITEM_TYPES[key]
        if not isinstance(value, expected):
            names = " | ".join(t.__name__ for t in expected)
            raise TypeError(
                f"{key!r} очікує {names}, отримано {type(value).__name__}"
            )
        setattr(self, key, value)
