"""Завдання 2: багаторівнева система контролю доступу."""

from shared.tables import print_table

# Вхідні дані варіанта 8
USERS = {
    "crypto_specialist": {
        "role": "cryptographer",
        "clearance": 4,
        "department": "Cryptography",
        "active": True,
    },
    "privacy_officer": {
        "role": "privacy_analyst",
        "clearance": 3,
        "department": "Privacy",
        "active": True,
    },
    "data_scientist": {
        "role": "data_analyst",
        "clearance": 2,
        "department": "Analytics",
        "active": True,
    },
    "field_engineer": {
        "role": "field_support",
        "clearance": 2,
        "department": "Field Ops",
        "active": True,
    },
    "test_account": {
        "role": "testing",
        "clearance": 1,
        "department": "QA",
        "active": False,
    },
}
RESOURCES = [
    ("encryption_keys", 4),
    ("privacy_policies", 3),
    ("anonymized_data", 2),
    ("crypto_algorithms", 4),
    ("consent_forms", 1),
    ("data_classification", 3),
    ("key_management", 4),
    ("statistical_models", 2),
    ("public_datasets", 1),
]
SECURITY_LEVELS = (
    "Unclassified",
    "For Official Use",
    "Confidential",
    "Secret",
)
BLOCKED_USERS = {"test_account", "gdpr_violation", "data_breach_user"}


def level_name(level, levels=SECURITY_LEVELS):
    """Повернути текстову назву рівня безпеки (рівні нумеруються з 1)."""
    return levels[level - 1]


def check_access(username, level, users=USERS, blocked=BLOCKED_USERS):
    """Перевірити доступ користувача до ресурсу з рівнем `level`."""
    user = users.get(username)
    if user is None:
        return False, "User not found"
    if username in blocked:
        return False, "User is blocked"
    if not user["active"]:
        return False, "Account inactive"
    if user["clearance"] >= level:
        return True, ""
    return False, "Insufficient clearance"


def run():
    """Вивести ресурси та результати перевірки доступу."""
    print("Ресурси системи:")
    print_table(
        ("Ресурс", "Рівень", "Назва рівня"),
        [(name, lvl, level_name(lvl)) for name, lvl in RESOURCES],
    )

    print("\nРезультати перевірки доступу:")
    allowed = denied = 0
    for username in [*USERS, "unknown_user"]:
        for resource, level in RESOURCES:
            ok, reason = check_access(username, level)
            verdict = "ALLOW" if ok else f"DENY ({reason})"
            allowed += ok
            denied += not ok
            print(f"user={username} resource={resource} -> {verdict}")
    print(f"\nУсього: ALLOW = {allowed}, DENY = {denied}")


if __name__ == "__main__":
    run()
