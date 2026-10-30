# ЛР №3 — Web API на FastAPI та SQLite

Студент: Шетеля Дмитро Максимович, КБ-209, варіант 23
(дані варіанта 8, бо `(23 - 1) % 15 + 1 = 8`).

**Варіант 8 — облік часу відновлення сервісів.** Категорія визначає
сервіс (`database`, `web_service`, `file_storage`), `value` — час
відновлення у **хвилинах** (скінченне число `>= 0`, без верхньої межі),
`status` — стан перевірки вимірювання (`new`, `in_progress`, `done`).
Поріг реагування — **60 хвилин**: у відповіді поле `exceeds_threshold`
показує, чи перевищено поріг.

## Встановлення

З кореня репозиторію, в активованому середовищі з ЛР №1:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## База даних і початкові дані

```powershell
python -m labs.lab03.database   # створити таблиці за schema.sql
python -m labs.lab03.seed       # 3 категорії та 8 записів з data/seed.json
```

Повторний запуск `seed` не змінює непорожню базу. Файл
`labs/lab03/data/lab3.sqlite3` створюється програмою і не зберігається в Git;
щоб почати з чистої бази, видаліть його та повторіть команди.

## Запуск API

```powershell
uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger UI: <http://127.0.0.1:8000/docs>, OpenAPI-схема:
<http://127.0.0.1:8000/openapi.json>.

## Маршрути

| Метод і маршрут | Призначення | Успіх |
|---|---|---|
| `GET /ping` | перевірка доступності | 200 |
| `GET /student` | ПІБ, група, варіант | 200 |
| `GET /categories` | список категорій | 200 |
| `POST /categories` | створити категорію | 201 |
| `DELETE /categories/{category_id}` | видалити порожню категорію | 204 |
| `GET /records` | список із фільтрами `category_id`, `status`, `min_value`, `q`, `limit`, `offset` | 200 |
| `GET /records/{record_id}` | один запис | 200 |
| `POST /records` | створити запис | 201 |
| `PUT /records/{record_id}` | повна заміна змінюваних полів | 200 |
| `DELETE /records/{record_id}` | видалити запис | 204 |
| `POST /records/bulk` | пакет 1–100 записів в одній транзакції | 201 |

Помилки: неіснуючий запис або категорія — `404`; дублікат `code` чи назви
категорії, видалення непорожньої категорії — `409`; некоректні дані або
параметри — `422`.

## Приклади запитів (PowerShell)

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ping
Invoke-RestMethod "http://127.0.0.1:8000/records?category_id=1&status=new&limit=5"
$body = '{"code":"V08-TEST","title":"Навчальне вимірювання","category_id":1,"value":42.5,"status":"new"}'
Invoke-RestMethod -Method Post http://127.0.0.1:8000/records `
    -ContentType "application/json; charset=utf-8" -Body $body
```

Те саме через curl (Bash):

```bash
curl -i "http://127.0.0.1:8000/records?category_id=1&status=new&limit=5&offset=0"
curl -i -X POST http://127.0.0.1:8000/records -H "Content-Type: application/json" \
  -d '{"code":"V08-TEST","title":"Навчальне вимірювання","category_id":1,"value":42.5,"status":"new"}'
```

## Перевірки (завдання 3)

На новій базі після `seed` і запущеного сервера:

```powershell
python -m labs.lab03.check_api            # сценарії 2-13 і створення запису 14
# перезапустити сервер, потім:
python -m labs.lab03.check_api --restart  # сценарій 14
```

## Структура

```
labs/lab03/
├── main.py          # FastAPI, lifespan, /ping, /student
├── config.py        # предметна область, одиниця, поріг, обмеження
├── database.py      # з'єднання та виконання schema.sql
├── schema.sql       # готова схема (варіанти 7–9)
├── schemas.py       # Pydantic-моделі
├── repository.py    # параметризовані SQL-запити, транзакції
├── seed.py          # заповнення з data/seed.json
├── check_api.py     # відтворювані перевірки API
├── routers/         # categories.py, records.py
└── data/seed.json   # навчальні дані варіанта
```
