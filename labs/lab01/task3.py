"""Завдання 3: хешування, CSV-база користувачів та JSON-логування."""

import csv
import functools
import hashlib
import json
import os
from datetime import datetime

from shared.student import DATA_VARIANT, VARIANT_NUMBER
from shared.tables import print_table

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def short_path(path):
    """Повернути шлях відносно поточної папки (для чистого виводу)."""
    return os.path.relpath(path).replace(os.sep, "/")


USERS_FILE = os.path.join(DATA_DIR, "users.csv")
LOG_FILE = os.path.join(DATA_DIR, "log.json")

# Таблиця варіантів: (алгоритм хешування, мінімальна довжина пароля)
VARIANTS_TABLE = {
    1: ("sha3_512", 12),
    2: ("sha3_224", 10),
    3: ("sha1", 8),
    4: ("sha512", 14),
    5: ("sha3_256", 16),
    6: ("blake2s", 9),
    7: ("sha384", 15),
    8: ("sha256", 11),
    9: ("sha224", 13),
    10: ("sha3_384", 10),
    11: ("blake2b", 12),
    12: ("md5", 8),
    13: ("sha3_256", 14),
    14: ("sha512", 16),
    15: ("sha1", 9),
}
HASH_ALGORITHM, MIN_LENGTH = VARIANTS_TABLE[DATA_VARIANT]

# Персональна сіль: 5 символів, номер варіанта доповнений нулями зліва
PERSONAL_SALT = str(VARIANT_NUMBER).zfill(5)

users_to_register = (
    ("admin_dmytro", "Adm1n#Secure2026"),
    ("analyst_olena", "An@lyst_Pass2026"),
    ("dev_taras", "D3v!Taras_Lviv24"),
    ("soc_ivan", "S0C#Monitor_2026"),
    ("pentester_oksana", "P3ntest@Oksana1"),
    ("auditor_petro", "Aud1t0r$Petro77"),
    ("intern_maria", "Intern@Maria2026"),
    ("devops_andriy", "DevOps#Andriy_99"),
    ("forensic_yulia", "F0rensic&Yulia88"),
    ("guest_viewer", "Gu3st-View3r_2026"),
)


class ValidationError(Exception):
    """Пароль не відповідає вимогам політики безпеки."""


def generate_hash(password: str, salt: str = "00000") -> str:
    """Повернути hex-хеш конкатенації пароля та солі."""
    if not password or not salt:
        raise ValueError("Пароль і сіль не можуть бути порожніми")
    if len(password) < MIN_LENGTH:
        raise ValidationError(f"Пароль коротший за {MIN_LENGTH} символів")
    digest = hashlib.new(HASH_ALGORITHM)
    digest.update((password + salt).encode("utf-8"))
    return digest.hexdigest()


def create_user(username, password):
    """Створити запис користувача: (логін, хеш пароля із сіллю)."""
    return username, generate_hash(password, PERSONAL_SALT)


def create_users(users_list):
    """Записати всіх користувачів у CSV-файл у форматі «логін,хеш»."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        records = [create_user(name, pwd) for name, pwd in users_list]
        with open(USERS_FILE, "w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerows(records)
    except PermissionError:
        print(f"Помилка: немає прав на запис у {USERS_FILE}")
        raise
    except (ValidationError, ValueError) as error:
        print(f"Помилка валідації: {error}")
        raise
    except OSError as error:
        print(f"Помилка введення-виведення: {error}")
        raise
    return records


def read_users():
    """Прочитати CSV-базу користувачів у список кортежів (логін, хеш)."""
    try:
        with open(USERS_FILE, newline="", encoding="utf-8") as file:
            return [tuple(row) for row in csv.reader(file) if row]
    except FileNotFoundError:
        print(f"Файл бази не знайдено: {USERS_FILE}")
        return []
    except PermissionError:
        print(f"Немає прав на читання {USERS_FILE}")
        return []
    except OSError as error:
        print(f"Помилка введення-виведення: {error}")
        return []


def write_log(entry):
    """Дописати подію до JSON-журналу (список подій)."""
    events = []
    try:
        with open(LOG_FILE, encoding="utf-8") as file:
            events = json.load(file)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        events = []
    events.append(entry)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as file:
            json.dump(events, file, ensure_ascii=False, indent=2)
    except (PermissionError, OSError) as error:
        print(f"Не вдалося записати журнал: {error}")


def log_event(func):
    """Декоратор: записує кожну спробу входу до log.json.

    Пароль і інші аргументи навмисно не зберігаються в журналі.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        username = args[0] if args else kwargs.get("username", "")
        result = "failure"
        try:
            outcome = func(*args, **kwargs)
            result = "success" if outcome else "failure"
            return outcome
        finally:
            write_log(
                {
                    "event": "login",
                    "user": username,
                    "result": result,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "args": [],
                    "kwargs": {},
                }
            )

    return wrapper


@log_event
def login(username: str, password: str) -> bool:
    """Перевірити логін і пароль за базою користувачів."""
    if not username or not password:
        raise ValueError("Логін і пароль не можуть бути порожніми")
    users_db = dict(read_users())
    stored_hash = users_db.get(username)
    if stored_hash is None:
        return False
    try:
        return generate_hash(password, PERSONAL_SALT) == stored_hash
    except ValidationError:
        return False


def run():
    """Продемонструвати реєстрацію, читання бази та автентифікацію."""
    print(
        f"Алгоритм: {HASH_ALGORITHM}, мін. довжина: {MIN_LENGTH}, "
        f"сіль: {PERSONAL_SALT}"
    )
    for path in (USERS_FILE, LOG_FILE):
        if os.path.exists(path):
            os.remove(path)

    try:
        create_users(users_to_register)
    except (ValidationError, ValueError, OSError):
        return

    users_db = read_users()
    print(f"\nБаза користувачів ({short_path(USERS_FILE)}):")
    print_table(("Логін", "Хеш пароля"), users_db)

    print("\nСпроби автентифікації:")
    attempts = (
        ("admin_dmytro", "Adm1n#Secure2026", "правильний пароль"),
        ("admin_dmytro", "Wrong#Password99", "хибний пароль"),
        ("ghost_user", "Some#Passw0rd123", "користувача немає"),
        ("soc_ivan", "short", "пароль коротший за мінімум"),
        ("", "Adm1n#Secure2026", "порожній логін"),
        ("guest_viewer", "", "порожній пароль"),
    )
    for username, password, note in attempts:
        try:
            result = login(username, password)
            print(f"login({username!r}) [{note}] -> {result}")
        except ValueError as error:
            print(f"login({username!r}) [{note}] -> ValueError: {error}")

    print(f"\nЖурнал подій збережено у {short_path(LOG_FILE)}")


if __name__ == "__main__":
    run()
