"""Відтворювані перевірки API (завдання 3) через HTTP-запити.

Перед запуском: ``python -m labs.lab03.seed`` (нова база) і запущений
сервер ``uvicorn labs.lab03.main:app --host 127.0.0.1 --port 8000``.

    python -m labs.lab03.check_api            # сценарії 2-13 і створення 14
    python -m labs.lab03.check_api --restart  # сценарій 14 після перезапуску
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = "http://127.0.0.1:8000"
PERSIST_CODE = "V08-PERSIST"


def call(
    method: str, path: str, body: Any = None, *, show: bool = True
) -> tuple[int, Any]:
    """Виконати HTTP-запит і повернути (код, JSON-відповідь або None)."""
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        BASE_URL + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            code, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        code, raw = error.code, error.read()
    payload = json.loads(raw) if raw else None
    if show:
        print(f"  {method} {urllib.parse.unquote(path)}")
        if body is not None:
            print(f"    body: {short(body, 110)}")
        print(f"    -> {code} {short(payload)}")
    return code, payload


def short(payload: Any, limit: int = 110) -> str:
    """Скоротити JSON для виведення в консоль."""
    if payload is None:
        return "(без тіла)"
    if isinstance(payload, dict) and isinstance(payload.get("detail"), list):
        fields = [
            "/".join(str(p) for p in item.get("loc", []))
            for item in payload["detail"]
        ]
        return f"validation error: {', '.join(fields)}"
    text = json.dumps(payload, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def all_codes() -> list[str]:
    """Отримати code усіх записів, проходячи сторінки через offset."""
    codes: list[str] = []
    offset = 0
    while True:
        _, page = call(
            "GET", f"/records?limit=100&offset={offset}", show=False
        )
        codes.extend(item["code"] for item in page)
        if len(page) < 100:
            return codes
        offset += 100


def title(text: str) -> None:
    """Вивести заголовок сценарію."""
    print(f"\n=== {text} ===")


def expect(ok: bool, results: list[bool]) -> None:
    """Зафіксувати результат перевірки."""
    results.append(ok)
    print("    OK" if ok else "    FAIL")


def new_record(code: str, **changes: Any) -> dict[str, Any]:
    """Сформувати тіло запису з типовими значеннями."""
    record = {
        "code": code,
        "title": "Навчальне вимірювання",
        "category_id": 1,
        "value": 42.5,
        "status": "new",
    }
    record.update(changes)
    return record


def run_checks() -> list[bool]:
    """Виконати сценарії 2-13 і створити запис для сценарію 14."""
    r: list[bool] = []

    title("2. GET /ping, /student, /categories")
    expect(call("GET", "/ping")[0] == 200, r)
    expect(call("GET", "/student")[0] == 200, r)
    code, cats = call("GET", "/categories")
    expect(code == 200 and [c["id"] for c in cats] == [1, 2, 3], r)

    title("3. CRUD окремого запису")
    code, rec = call("POST", "/records", new_record("V08-TEST"))
    expect(code == 201 and rec["category_name"] == "database", r)
    rid = rec["id"]
    expect(call("GET", f"/records/{rid}")[0] == 200, r)
    code, rec = call(
        "PUT",
        f"/records/{rid}",
        new_record(
            "V08-TEST",
            title="Оновлене вимірювання",
            category_id=2,
            value=61.0,
            status="done",
        ),
    )
    expect(code == 200 and rec["id"] == rid and rec["exceeds_threshold"], r)
    expect(call("DELETE", f"/records/{rid}")[0] == 204, r)
    expect(call("GET", f"/records/{rid}")[0] == 404, r)

    title("4. Фільтри, два фільтри, limit і offset")
    code, items = call("GET", "/records?category_id=1")
    expect(code == 200 and all(i["category_id"] == 1 for i in items), r)
    code, items = call("GET", "/records?status=done&min_value=40")
    expect(all(i["status"] == "done" and i["value"] >= 40 for i in items), r)
    _, page1 = call("GET", "/records?limit=3&offset=0")
    _, page2 = call("GET", "/records?limit=3&offset=3")
    ids = [i["id"] for i in page1 + page2]
    expect(ids == sorted(ids) and len(set(ids)) == 6, r)
    code, items = call("GET", "/records?q=" + urllib.parse.quote("05"))
    expect(code == 200 and [i["code"] for i in items] == ["V08-05"], r)
    expect(call("GET", "/records?category_id=99")[1] == [], r)

    title("5. Від'ємне value, порожній title, статус, limit=0 -> 422")
    before = len(all_codes())
    for body in (
        new_record("V08-BAD1", value=-5),
        new_record("V08-BAD2", title="   "),
        new_record("V08-BAD3", status="closed"),
    ):
        expect(call("POST", "/records", body)[0] == 422, r)
    expect(call("GET", "/records?limit=0")[0] == 422, r)
    expect(len(all_codes()) == before, r)

    title("6. Неправильний тип value і нескінченність -> 422")
    expect(
        call("POST", "/records", new_record("V08-BAD4", value="сорок"))[0]
        == 422,
        r,
    )
    expect(call("GET", "/records?min_value=inf")[0] == 422, r)
    expect(
        call("POST", "/records", {**new_record("V08-BAD5"), "id": 7})[0]
        == 422,
        r,
    )

    title("7. Неіснуючий record_id і category_id -> 404")
    expect(call("GET", "/records/9999")[0] == 404, r)
    expect(
        call("POST", "/records", new_record("V08-NOCAT", category_id=99))[0]
        == 404,
        r,
    )
    expect(call("GET", "/records/0")[0] == 422, r)

    title("8. Повторний code і назва категорії -> 409")
    expect(call("POST", "/records", new_record("V08-01"))[0] == 409, r)
    expect(call("POST", "/categories", {"name": "database"})[0] == 409, r)
    expect(call("GET", "/records/1")[1]["code"] == "V08-01", r)

    title("9. Видалення непорожньої та порожньої категорії")
    expect(call("DELETE", "/categories/1")[0] == 409, r)
    code, cat = call("POST", "/categories", {"name": "temp_category"})
    expect(code == 201, r)
    expect(call("DELETE", f"/categories/{cat['id']}")[0] == 204, r)
    expect(len(call("GET", "/categories", show=False)[1]) == 3, r)

    title("10. Коректний пакет із двох записів -> 201")
    bulk = [
        new_record("V08-B01", title="Пакетне вимірювання 1", value=15.0),
        new_record(
            "V08-B02",
            title="Пакетне вимірювання 2",
            category_id=3,
            value=70.0,
            status="in_progress",
        ),
    ]
    code, created = call("POST", "/records/bulk", bulk)
    expect(code == 201 and len(created) == 2, r)

    title("11. Пакет: новий + дублікат code з бази -> 409, відкат")
    before = all_codes()
    print(f"    записів до: {len(before)}")
    code, _ = call(
        "POST",
        "/records/bulk",
        [new_record("V08-ROLLBACK"), new_record("V08-01", category_id=2)],
    )
    after = all_codes()
    print(
        f"    записів після: {len(after)}; "
        f"V08-ROLLBACK у базі: {'V08-ROLLBACK' in after}"
    )
    expect(code == 409 and after == before, r)

    title("12. Пакет: новий + неіснуюча категорія -> 404, відкат")
    before = all_codes()
    print(f"    записів до: {len(before)}")
    code, _ = call(
        "POST",
        "/records/bulk",
        [
            new_record("V08-ROLLBACK2"),
            new_record("V08-NOCAT2", category_id=99),
        ],
    )
    after = all_codes()
    print(
        f"    записів після: {len(after)}; "
        f"V08-ROLLBACK2 у базі: {'V08-ROLLBACK2' in after}"
    )
    expect(code == 404 and after == before, r)

    title("13. Спроба SQL-ін'єкції: q=' OR 1=1 --")
    before = all_codes()
    code, items = call(
        "GET", "/records?q=" + urllib.parse.quote("' OR 1=1 --")
    )
    expect(code == 200 and items == [] and all_codes() == before, r)

    title("14. Створення запису перед перезапуском сервера")
    code, _ = call(
        "POST",
        "/records",
        new_record(PERSIST_CODE, title="Запис для перевірки перезапуску"),
    )
    expect(code == 201, r)
    return r


def check_after_restart() -> list[bool]:
    """Сценарій 14: запис доступний після перезапуску сервера."""
    r: list[bool] = []
    title("14. Після перезапуску сервера")
    code, items = call(
        "GET", "/records?q=" + urllib.parse.quote("перезапуску")
    )
    expect(code == 200 and [i["code"] for i in items] == [PERSIST_CODE], r)
    return r


def main() -> int:
    """Запустити перевірки та вивести підсумок."""
    parser = argparse.ArgumentParser(description="Перевірки API ЛР №3")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="перевірити запис після перезапуску сервера (сценарій 14)",
    )
    args = parser.parse_args()
    try:
        results = check_after_restart() if args.restart else run_checks()
    except urllib.error.URLError as error:
        print(f"Сервер недоступний ({BASE_URL}): {error.reason}")
        return 2
    passed = sum(results)
    print(f"\nПідсумок: {passed}/{len(results)} перевірок пройдено")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
